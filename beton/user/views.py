import ccxt
import json
import names
import pprint
import random
import requests
import uuid
# All revive XML RPC commands:
# https://github.com/revive-adserver/revive-adserver/blob/master/www/api/v2/xmlrpc/index.php
import xmlrpc.client

from datetime import datetime, timedelta
from dateutil.relativedelta import *
from PIL import Image, ImageDraw

from flask import Blueprint, current_app, flash, g, jsonify, redirect
from flask import render_template, request, session, url_for
from flask_security import current_user, login_required, roles_accepted
from flask_uploads import UploadSet, IMAGES

from beton.extensions import cache
from beton.logger import log
from beton.user.forms import AddBannerForm, ChangeOffer
from beton.user.models import Banner, Basket, Log, Orders, Payments, Prices, User
from beton.utils import dblogger, flash_errors, reviveme

blueprint = Blueprint('user', __name__, url_prefix='/me', static_folder='../static')
images = UploadSet('images', IMAGES)


def amiadmin():
    if current_user.has_role('admin'):
        isadmin = True
    else:
        isadmin = False
    return isadmin


def random_color():
    color = "%03x" % random.randint(0, 0xFFF)
    return "#"+str(color)

# it is safe to cache it for 10 minutes or even more
@cache.memoize(600)
def create_banner_overview(zone):
    destpath = (current_app.config.get('UPLOADED_IMAGES_DEST') +
        "/overview/zone-%s.png" % str(zone))
    dwg = Image.new(
        'RGB',
        (
            current_app.config.get('BANNER_OVERVIEW_WIDTH'),
            current_app.config.get('BANNER_OVERVIEW_HEIGHT')
        ),
        color='red'
    )

    zonedata = Prices.query.filter_by(id=zone).first()
    # font = ImageFont.load_default()

    b = ImageDraw.Draw(dwg)
    b.rectangle(
        [
            (
                zonedata.x0,
                zonedata.y0
            ),
            (
                zonedata.x1,
                zonedata.y1
            )
        ],
        fill='yellow'
    )
    b.text(
        (
            zonedata.x0+3,
            zonedata.y0+3
        ),
        str(zone),
        fill='black',

    )
    dwg.save(destpath, 'PNG')


@cache.memoize(50)
def getexrate(coin):
    '''Returns exchange rate from first positively responding exchange.
       It is rather safe to cache that rate for 50 seconds.'''
    exchanges = current_app.config.get('EXCHANGES')
    # TODO: add other fiat currencies than EUR
    exfiat = current_app.config.get('FIAT')
    extrade = current_app.config.get('EXCHANGES_TRADE')
    for id in exchanges:
        exchange = getattr(ccxt, id)()
        pair = coin+"/"+exfiat
        exrate = exchange.fetch_ticker(pair)[extrade]
        if exrate is not None:
            return exrate
    # if all attempts fail, we return zero rate to signal an error
    return 0


@cache.memoize(50)
def minerfee(amount, electrum_url):
    '''Ask electrum for an average miner fee.
       We assume that an average transaction is about 258 bytes long.
       We cache this for 50 seconds to avoid unnecessary traffic.'''
    log.debug("Asking Electrum for a miner fee")
    payload = {
        "id": str(uuid.uuid4()),
        "method": "getfeerate"
    }
    get_fee = requests.post(electrum_url, json=payload).json()
    log.debug("Miner fee rate per kb is in satoshi:")
    log.debug(get_fee)
    fee_kb = get_fee['result']
    return format(int(fee_kb)*0.258/100000000, '.9f')


@cache.memoize(timeout=666)
def all_advertisers_cached(r):
    '''We want to cache data which does not change frequently
       as asking revive is time costly.'''
    sessionid = session['revive']
    all_advertisers = r.ox.getAdvertiserListByAgencyId(
        sessionid,
        current_app.config.get('REVIVE_AGENCY_ID')
    )
    return all_advertisers


def get_advertiser_id():
    '''Try to find out if the customer is already registered
       in Revive, if not, register him.'''
    r = xmlrpc.client.ServerProxy(
        current_app.config.get('REVIVE_XML_URI'),
        verbose=False
    )
    sessionid = session['revive']
    all_advertisers = all_advertisers_cached(r)

    try:
        next(x for x in all_advertisers if x['advertiserName'] ==
             current_user.username)
    except StopIteration:
        r.ox.addAdvertiser(
            sessionid,
            {
                'agencyId': current_app.config.get('REVIVE_AGENCY_ID'),
                'advertiserName': current_user.username,
                'emailAddress': current_user.email,
                'contactName': current_user.username,
                'comments': current_app.config.get('USER_APP_NAME')
            }
        )
        log.info("Added {} as new advertiser.".format(current_user.username))
        cache.delete_memoized('all_advertisers_cached')
        all_advertisers = all_advertisers_cached(r)

    advertiser_id = int(next(x for x in all_advertisers if x['advertiserName'] ==
                             current_user.username)['advertiserId'])
    return advertiser_id


@blueprint.url_value_preprocessor
def get_basket(endpoint, values):
    """We need basket on every view if authenticated"""
    if current_user.is_authenticated:
        try:
            basket_sql = Basket.query.filter_by(user_id=current_user.id).all()
            if basket_sql:
                g.basket = len(basket_sql)
            else:
                g.basket = 0
        except:
            ## TODO: it might be required for minor used servers,
            ## as after 8 hours we are getting disconnected from mysqld
            # db.session.rollback()
            pass

    # keeping constant connection to Revive instance
    r = xmlrpc.client.ServerProxy(
        current_app.config.get('REVIVE_XML_URI'),
        verbose=False
    )
    if 'revive' in session:
        sessionid = session['revive']
        try:
            r.ox.getUserList(sessionid)
        except xmlrpc.client.Fault:
            log.debug("XML-RPC session to Revive probably expired, getting new one.")
            sessionid = reviveme(r)
            session['revive'] = sessionid
        except Exception as e:
            log.exception(e)
    else:
        sessionid = reviveme(r)
        session['revive'] = sessionid


@blueprint.route('/me')
@login_required
def user_me():
    """Main website for logged-in user"""
    return render_template('public/home.html')


@blueprint.route('/add_bannerz', methods=['GET', 'POST'])
@login_required
def add_bannerz():
    """Add a banner."""
    form = AddBannerForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            filename = images.save(request.files['banner_image'])
            # get the width and height
            with Image.open(images.path(filename)) as img:
                width, height = img.size
            Banner.create(
                filename=filename,
                owner=current_user.id,
                url=form.banner_url.data,
                created_at=datetime.utcnow(),
                width=width,
                height=height,
                comments=form.banner_comments.data
            )
            dblogger(
                current_user.id,
                "Banner %s uploaded successfully." % filename
            )
            flash('Your banner was uploaded sucessfully.', 'success')  # TODO:size
            return redirect(url_for('user.bannerz'))
        else:
            flash_errors(form)
    return render_template('users/upload_bannerz.html', form=form)


@blueprint.route('/bannerz')
@login_required
def bannerz():
    """See the banners."""
    all_banners = Banner.query.filter_by(owner=current_user.id).all()
    all_urls = []
    for x in all_banners:
        url = images.url(x.filename)
        all_urls.append([x.id, url])
    return render_template(
        'users/bannerz.html',
        all_banners=all_banners,
        all_urls=all_urls
    )


@blueprint.route('/offer', methods=['GET', 'POST'])
@login_required
def offer():
    """Get and display all possible websites and zones in them."""
    form = ChangeOffer()

    r = xmlrpc.client.ServerProxy(
        current_app.config.get('REVIVE_XML_URI'),
        verbose=False
    )
    sessionid = session['revive']
    advertiser_id = get_advertiser_id()

    # Get all publishers (websites)
    publishers = r.ox.getPublisherListByAgencyId(
        sessionid,
        current_app.config.get('REVIVE_AGENCY_ID')
    )

    all_zones = []
    for website in publishers:
        # get zones from Revive
        allzones = r.ox.getZoneListByPublisherId(
            sessionid,
            website['publisherId']
        )
        for zone in allzones:
            # First check if the zone from Revive is available in our Price
            # database, of not, we are creating it with zero values 
            howmany = Prices.query.filter_by(zoneid=zone['zoneId']).count()
            if howmany is not 1:
                Prices.create(
                    zoneid = zone['zoneId'],
                    dayprice = 0,
                    x0 = 0,
                    x1 = 0,
                    y0 = 0,
                    y1 = 0
                )
                Prices.commit()

            price = Prices.query.filter_by(zoneid=zone['zoneId']).first()

            tmpdict = {}

            tmpdict['publisherId'] = zone['publisherId']
            tmpdict['zoneName'] = zone['zoneName']
            tmpdict['width'] = zone['width']
            tmpdict['height'] = zone['height']
            tmpdict['zoneId'] = zone['zoneId']
            tmpdict['comments'] = zone['comments']

            tmpdict['price'] = price.dayprice
            tmpdict['x0'] = price.x0
            tmpdict['x1'] = price.x1
            tmpdict['y0'] = price.y0
            tmpdict['y1'] = price.y1

            # ask for stats
            try:
                ztatz = r.ox.advertiserZoneStatistics(
                    sessionid,
                    zone['zoneId'],
                    datetime.now() - relativedelta(months=1),
                    datetime.now()
                )
                tmpdict['impressions'] = ztatz[0]['impressions']
            except Exception as e:
                log.debug("Exception")
                log.exception(e)
                tmpdict['impressions'] = 0

            all_zones.append(tmpdict)

            # Prepare overview image
            create_banner_overview(
                zone['zoneId']
            )

    if request.method == 'POST':
        log.debug(pprint.pformat(request.form, depth=5))
        if form.validate_on_submit():
            for zone in all_zones:
                if form.zoneid.data == zone['zoneId']:
                    Prices.query.filter_by(
                        zoneid=form.zoneid.data).update(
                            {
                                "dayprice": form.zoneprice.data,
                                "x0": form.x0.data,
                                "x1": form.x1.data,
                                "y0": form.y0.data,
                                "y1": form.y1.data
                            }
                        )
                    Prices.commit()

        return redirect(url_for('user.offer'))

    # Render the page and quit
    return render_template(
        'users/offer.html',
        allzones = all_zones,
        publishers = publishers,
        isadmin = amiadmin(),
        form = form
    )


@blueprint.route('/campaign')
@blueprint.route('/campaign/duration/<int:no_weeks>')
@blueprint.route('/campaign/details/<int:campaign_no>')
@login_required
def campaign(no_weeks=None,campaign_no=None):
    """
    Details related to one campaign only.
    or
    Get and display all campaigns belonging to user.
    """

    if not no_weeks:  # we show 1 month of recent campaigns by default
        no_weeks = 4
    r = xmlrpc.client.ServerProxy(
        current_app.config.get('REVIVE_XML_URI'),
        verbose=False
    )
    sessionid = session['revive']

    advertiser_id = get_advertiser_id()

    # A universal JOIN across tables to get info about an order
    dbqueryall = Orders.query.join(
        Payments, Orders.paymentno==Payments.id).join(
            Banner, Orders.bannerid==Banner.id).add_columns(
                Orders.user_id,
                Orders.begins_at,
                Orders.stops_at,
                Orders.created_at,
                Orders.zoneid,
                Orders.campaigno,
                Orders.bannerid,
                Orders.name,
                Orders.comments,
                Orders.impressions,
                Payments.address,
                Payments.bip70_id,
                Payments.confirmed_at,
                Payments.received_at,
                Payments.blockchain,
                Payments.total_coins,
                Payments.txno,
                Banner.filename,
                Banner.url,
                Banner.width,
                Banner.height
            )

    # We want details related to one campaign, not a list of all so we will
    # display that data and quit this function
    if campaign_no is not None:
        dbquery = dbqueryall.filter(Orders.campaigno==campaign_no).first()

        # we show details only to campaign owners or admins
        if Orders.user_id == current_user.id or amiadmin():
            # Render the page and quit
            return render_template(
                'users/campaign-single.html',
                now = datetime.utcnow(),
                datemin = datetime.min,
                dbquery = dbquery
            )
        else:
            # We politely redirecting 'hackers' to all campaigns
            return redirect(url_for("user.campaign"), code=302)

    # admin gets all campaigns for all users
    if amiadmin():
        all_campaigns = dbqueryall.all()
    else:
        all_campaigns = dbqueryall.filter(Orders.user_id==current_user.id).all()

    # Render the page and quit
    return render_template(
        'users/campaign.html',
        all_campaigns = all_campaigns,
        roles = current_user.roles,
        now = datetime.utcnow(),
        datemin = datetime.min,
        no_weeks = no_weeks
    )


@blueprint.route('/api/all_campaigns_in_zone/<int:zone_id>')
@login_required
def api_all_campaigns(zone_id):
    """JSON:
    https://fullcalendar.io/docs/event-object
    """
    # TODO: get timescales from fullcalendar uri
    # start = request.args.get('start')
    # end = request.args.get('end')
    # Get all orders from local database
    if zone_id == 0:
        all_orders = Orders.query.all()
    else:
        all_orders = Orders.query.filter_by(zoneid=zone_id).all()
    ac = []
    for order in all_orders:
        tasks = {}
        fullname = order.name
        tasks['id'] = order.campaigno
        tasks['title'] = fullname
        tasks['allDay'] = "true"
        tasks['color'] = random_color()
        tasks['resourceId'] = order.zoneid
        starttime = order.begins_at
        endtime = order.stops_at
        tasks['start'] = starttime.strftime("%Y-%m-%d")
        if (endtime - starttime).days < 1:
            calendarend = endtime
        else:
            calendarend = endtime + timedelta(days=1)
        tasks['end'] = calendarend.strftime("%Y-%m-%d")
        ac.append(tasks)

    return jsonify(ac)


@blueprint.route('/order', methods=['get', 'post'])
@login_required
def order():
    """Order a campaign."""
    r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                  verbose=False)
    sessionid = session['revive']

    if ('step' not in request.form) or \
            ('submit' in request.form.values() and request.form['submit'] == 'cancel'):
        all_banners = Banner.query.filter_by(owner=current_user.id).all()
        all_urls = []
        for x in all_banners:
            url = images.url(x.filename)
            all_urls.append([x.id, url])
        return render_template('users/order.html', all_banners=all_banners,
                               all_urls=all_urls, step='chose-banner')

    elif request.form['step'] == 'chose-zone':
        """Get and display all possible websites and zones in them."""
        # Get banner height and width
        banner_id = int(request.form['banner_id'])
        banner = Banner.query.filter_by(id=banner_id).first()
        image_url = images.url(banner.filename)

        # Get all publishers (websites)
        publishers = r.ox.getPublisherListByAgencyId(
            sessionid,
            current_app.config.get('REVIVE_AGENCY_ID')
        )

        # Get zones from Revive
        all_zones = []

        for website in publishers:
            allzones = r.ox.getZoneListByPublisherId(
                sessionid,
                website['publisherId']
            )
            for zone in allzones:
                price = Prices.query.filter_by(zoneid=zone['zoneId']).first()
                if not price:
                    return render_template('users/order-noprice.html')
                zone_width = zone['width']
                zone_height = zone['height']
                zone['price'] = price
                if zone_width == banner.width and zone_height == banner.height:
                    all_zones.append(zone)
        return render_template('users/order.html', banner=banner,
                               image_url=image_url,
                               all_zones=all_zones, step='chose-zone')

    elif request.form['step'] == 'chose-date':
        banner_id = int(request.form['banner_id'])
        banner = Banner.query.filter_by(id=banner_id).first()
        image_url = images.url(banner.filename)
        zone_id = int(request.form['zone_id'])
        zone_name = request.form['zone_name']
        return render_template('users/order.html', banner_id=banner_id,
                               zone_id=zone_id, image_url=image_url,
                               zone_name=zone_name, step='chose-date')

    elif request.form['step'] == 'order':
        randomname = names.get_full_name()
        banner_id = int(request.form['banner_id'])
        banner = Banner.query.filter_by(id=banner_id).first()
        image_url = images.url(banner.filename)
        width = banner.width
        height = banner.height
        url = banner.url
        zone_id = int(request.form['zone_id'])
        zone_name = request.form['zone_name']
        datestart = request.form['datestart']
        datend = request.form['datend']

        price = Prices.query.filter_by(zoneid=zone_id).first()

        # We are booking the campaign in Revive, but turning off by default
        # until payment is confirmed
        advertiser_id = get_advertiser_id()

        try:
            begin = datetime.strptime(datestart, "%d/%m/%Y")
            enddate = datetime.strptime(datend, "%d/%m/%Y")
        except BaseException:
            return render_template('users/date-problems.html')
        totaltime = enddate - begin
        diki = {}
        diki['advertiserId'] = advertiser_id
        diki['campaignName'] = randomname
        diki['startDate'] = begin
        diki['endDate'] = enddate
        diki['comments'] = zone_name
        campaign = r.ox.addCampaign(sessionid, diki)

        # Now we are adding our banner to campaign
        diki = {}
        diki['campaignId'] = campaign
        diki['bannerName'] = str(banner_id)
        diki['imageURL'] = image_url
        diki['width'] = width
        diki['height'] = height
        diki['url'] = url
        diki['storageType'] = 'url'
        r.ox.addBanner(sessionid, diki)

        Orders.create(
            campaigno = campaign,
            zoneid = zone_id,
            created_at = datetime.utcnow(),
            begins_at = begin,
            stops_at = enddate,
            paymentno = 0,
            bannerid = banner_id,
            name = randomname,
            comments = zone_name,
            impressions = 0,
            user_id = current_user.id
        )

        dblogger(
            current_user.id,
            ("NEW Campaign #%s with name %s in zone %s, starting at %s, " +
                "ending at %s, with banner %s created.") % (
                str(campaign),
                randomname,
                str(zone_id),
                str(begin),
                str(enddate),
                str(banner_id)
            )
        )

        Basket.create(
            campaigno = campaign,
            user_id = current_user.id
        )

        return render_template(
            'users/order.html',
            banner_id = banner_id,
            datestart = datestart,
            datend = datend,
            image_url = image_url,
            zone_id = zone_id,
            days = totaltime.days,
            dayprice = price.dayprice,
            step = 'order'
        )


@blueprint.route('/basket', methods=['get'])
@login_required
def basket():
    """Present his/her basket to customer."""

    basket = []
    price = []
    basket_sql = Basket.query.filter_by(user_id=current_user.id).all()
    # Checks to see if the user has already started a cart.
    if basket_sql:
        for item in basket_sql:
            order_sql = Orders.query.filter_by(
                campaigno=item.campaigno).join(Banner).join(Prices).add_columns(
                Banner.filename, Banner.url, Banner.width, Banner.height, Prices.dayprice).first()
            basket.append(order_sql)
            begin = order_sql[0].begins_at
            enddate = order_sql[0].stops_at
            totaltime = enddate - begin
            totalcurrencyprice = order_sql.dayprice/100*(totaltime.days+1)
            price.append([item.campaigno, "EUR", totalcurrencyprice])

            excoins = current_app.config.get('EXCHANGE_COINS')
            for coin in excoins:
                # try to get exchange values from two sources, and give up
                exrate = getexrate(coin)
                if exrate == 0:
                    return render_template('users/electrum-problems.html')
                totalcoinprice = format(totalcurrencyprice / float(exrate), '.9f')
                price.append([item.campaigno, coin, totalcoinprice])
    else:
        basket = 0

    return render_template(
        'users/basket.html',
        basket = basket,
        price = price,
        present = datetime.now()-timedelta(days=1)
    )

@blueprint.route('/clear/banner/<int:banner_id>')
@login_required
def clear_banner(banner_id):
    try:
        banner_data = Banner.query.filter_by(id=banner_id).first()
        if banner_data.owner == current_user.id:
            Banner.query.filter_by(id=banner_id).delete()
            flash(
                ('Your banner was removed sucessfully. All running campaigns' +
                  'are not affected.'), 'success'
            )
            dblogger(
                current_user.id,
                "User removed banner #{}".format(banner_id)
            )
            Banner.commit()
    except Exception as e:
        log.debug("Exception")
        log.exception(e)
    return redirect(url_for("user.bannerz"), code=302)


@blueprint.route('/clear/basket/<int:campaign_id>')
@login_required
def clear_basket(campaign_id):
    try:
        r = xmlrpc.client.ServerProxy(
            current_app.config.get('REVIVE_XML_URI'),
            verbose=False
        )
        sessionid = session['revive']
        if campaign_id == 0:
            all_basket = Basket.query.filter_by(user_id=current_user.id).all()
            # Removing these campaigns from Revive as not useful in future
            Basket.query.filter_by(user_id=current_user.id).delete()
            for order in all_basket:
                removed = r.ox.deleteCampaign(sessionid, order.campaigno)
                log.debug(
                    "Campaign #%s removed from Revive?: %s" % (
                        str(order.campaigno),
                        str(removed)
                    )
                )
                Orders.query.filter_by(campaigno=order.campaigno).delete()
                flash('Your basket was removed sucessfully.', 'success')
        else:
            removed = r.ox.deleteCampaign(sessionid, campaign_id)
            log.debug(
                "Campaign #%s removed from Revive?: %s" % (
                        str(order.campaigno),
                        str(removed)
                    )
            )
            Basket.query.filter_by(user_id=current_user.id, campaigno=campaign_id).delete()
            Orders.query.filter_by(campaigno=campaign_id).delete()
            flash('Your planned campaign was removed sucessfully.', 'success')
        Basket.commit()
        Orders.commit()
    except Exception as e:
        log.debug("Exception")
        log.exception(e)
    return redirect(url_for("user.basket"), code=302)


# TODO: better ask user twice if campaign is running
@blueprint.route('/clear/campaign/<int:campaign_no>')
@login_required
def clear_campaign(campaign_no):
    try:
        r = xmlrpc.client.ServerProxy(
            current_app.config.get('REVIVE_XML_URI'),
            verbose=False
        )
        sessionid = session['revive']

        # getting data about this campaign 
        # and confirming it belongs to the user
        campaigndata = Orders.query.filter_by(campaigno=campaign_no).first()
        if campaigndata.user_id != current_user.id or not amiadmin():
            return redirect(url_for("user.campaign"), code=302)

        # removing campaign from all sources
        Orders.query.filter_by(campaigno=campaign_no).delete()
        Orders.commit()
        removed = r.ox.deleteCampaign(sessionid, campaign_no)
        logdata = (
            "Campaign #{} removed from Revive?: {}".format(
                campaign_no,
                removed
            )
        )
        log.debug(logdata)
        dblogger(
            current_user.id,
            "Campaign #{} was deleted by user.".format(
                campaign_no
            )
        )
        flash('Your campaign was deleted sucessfully.', 'success')

    except Exception as e:
        log.debug("Exception")
        log.exception(e)

    return redirect(url_for("user.campaign"), code=302)


@blueprint.route('/pay/<string:payment>')
@login_required
def pay(payment):
    """Pay a campaign. We serve a few payment systems, so it depends on 'payment' value."""

    payment_system = current_app.config.get('PAYMENT_SYSTEMS')[payment]

    exrate = getexrate(payment_system[0])
    if exrate == 0:
        return render_template('users/electrum-problems.html')

    # first we need to get basket data
    basket = []
    total = 0
    cointotal = 0
    label = "%s ※ %s ※ " % (
        current_app.config.get('USER_APP_NAME'),
        current_user.username)
    basket_sql = Basket.query.filter_by(user_id=current_user.id).all()
    # Checks to see if the user has already started a cart.
    if basket_sql:
        for item in basket_sql:
            order_sql = Orders.query.filter_by(
                campaigno=item.campaigno).join(Banner).join(Prices).add_columns(
                Banner.filename, Banner.url, Banner.width, Banner.height, Prices.dayprice).first()
            basket.append(order_sql)
            begin = order_sql[0].begins_at
            enddate = order_sql[0].stops_at
            totaltime = enddate - begin
            totalcurrencyprice = order_sql.dayprice/100*(totaltime.days+1)
            totalcoinprice = totalcurrencyprice / float(exrate)
            total += totalcurrencyprice
            cointotal += totalcoinprice
            label = label + "[C#{} Z#{} B#{} {} ↦ {} {}] ※ ".format(
                item.campaigno,
                order_sql[0].zoneid,
                order_sql[0].bannerid,
                begin.strftime("%d/%m/%y"),
                enddate.strftime("%d/%m/%y"),
                str(totalcurrencyprice)+current_app.config.get('FIAT')
            )
    else:
        basket = 0
        log.error("Trying to pay for empty basket.")
        return redirect(url_for("user.basket"), code=302)


    # kindly ask miss electrum for an invoice which expires in ~20 minutes
    params = {
        "amount": cointotal,
        "expiration": 1212,
        "memo": label
    }
    payload = {
        "id": str(uuid.uuid4()),
        "method": "addrequest",
        "params": params
    }
    log.debug("Payload to send to Electrum:")
    log.debug(payload)

    # contact electrum server - if it is not possible, signal problems to
    # customer
    electrum_url = payment_system[3]
    log.debug("Electrum RPC URI:")
    log.debug(electrum_url)
    try:
        electrum = requests.post(electrum_url, json=payload).json()
        log.debug("Data received back from Electrum:")
        log.debug(electrum)
    except Exception as e:
        log.debug("Exception")
        log.exception(e)
        return render_template('users/electrum-problems.html')
    result = electrum['result']
    if result is False:
        return render_template('users/electrum-problems.html')
    try:
        addr = result['address']
        pramount = result['amount']  # amount in satoshi
        bip70_id = result['id']
    except Exception as e:
        log.debug("Exception")
        log.exception(e)
        return render_template('users/electrum-problems.html')

    # We use amount taken from BIP70 Payment Request to avoid any distortions
    # from rounding - plus satoshi to crypturrency convertion.
    total_coins = (pramount/100000000.000000000)
    fee = minerfee(total_coins, electrum_url)

    # Creating database record for payment and linking it into orders.
    payment_sql = Payments.create(
        blockchain = payment,
        address = addr,
        total_coins = total_coins,
        txno = 0,
        created_at = datetime.utcnow(),
        user_id = current_user.id,
        bip70_id = bip70_id,
        confirmed_at = datetime.min,
        received_at = datetime.min
    )
    paymentno = payment_sql.id
    for item in basket:
        Orders.query.filter_by(campaigno=item[0].campaigno).update({"paymentno": paymentno})
        Orders.commit()

    #  kindly ask miss electrum for a ping when our address changes
    params = {
        "address": addr,
        "URL": current_app.config.get('OUR_URL')+'ipn/'+payment
    }
    payload = {
        "id": str(uuid.uuid4()),
        "method": "notify",
        "params": params
    }
    log.debug("Payload sent to Electrum:")
    log.debug(payload)
    ipn_please = requests.post(electrum_url, json=payload).json()
    log.debug("Response received from Electrum:")
    log.debug(ipn_please)
    # If electrum refuses notify request, signal an error and give up payment
    if ipn_please['result'] is not True:
        return render_template('users/electrum-problems.html')

    # It looks that payment page is ready to be shown, so we remove the content of basket
    Basket.query.filter_by(user_id=current_user.id).delete()
    Basket.commit()

    # and display payment page
    return render_template(
        'users/pay.html',
        total = total,
        orders = len(basket),
        exrate = exrate,
        fee = fee,
        currency = payment_system[0],
        electrum = result
    )


@blueprint.route('/admin/users')
@roles_accepted('admin')
def listusers():
    all_users = User.query.all()
    return render_template(
        'users/listusers.html',
        all_users=all_users
    )


# TODO: paging of data
@blueprint.route('/admin/log/<int:user_id>')
@roles_accepted('admin')
def logaboutuser(user_id):
    userlog = Log.query.filter_by(user_id=user_id).all()
    return render_template(
        'users/logaboutuser.html',
        userlog = userlog
    )
