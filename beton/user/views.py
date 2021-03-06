# -*- coding: utf-8 -*-
import btcpay
import names
import pickle
import pprint
import random
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
from beton.user.forms import AddBannerForm, AddBannerTextForm, AddPairingTextForm, ChangeOffer
from beton.user.models import Banner, Basket, Impressions, Log, Orders, Payments, Prices, User
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

    zonedata = Prices.query.filter_by(zoneid=zone).first()
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
        cache.delete_memoized(all_advertisers_cached)
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
        except Exception as e:
            # # TODO: it might be required for minor used servers,
            # # as after 8 hours we are getting disconnected from mysqld
            # db.session.rollback()
            log.exception(e)
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
    # vers we need globally


@blueprint.route('/me')
@login_required
def user_me():
    """Main website for logged-in user"""
    return render_template('public/home.html')


@blueprint.route('/add/bannerz', methods=['GET', 'POST'])
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
                type="file",
                content="NULL",
                icon="NULL",
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


@blueprint.route('/add/text', methods=['GET', 'POST'])
@login_required
def add_text():
    """Add a text banner."""
    form = AddBannerTextForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            Banner.create(
                filename="NULL",
                owner=current_user.id,
                url=form.banner_url.data,
                created_at=datetime.utcnow(),
                width="NULL",
                height="NULL",
                type="text",
                content=form.banner_content.data,
                icon=form.banner_icon.data,
                comments=form.banner_comments.data
            )
            dblogger(
                current_user.id,
                "Text Banner set successfully. %s" % form.banner_content.data
            )
            flash('Your banner was set sucessfully.', 'success')  # TODO:size
            return redirect(url_for('user.bannerz'))
        else:
            flash_errors(form)
    return render_template('users/upload_text.html', form=form)


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

    # ignore the websites on our blacklist 
    for blackwebsite in current_app.config.get('REVIVE_IGNORED_WEBSITES'):
        for website in publishers:
            if website['publisherName'] == blackwebsite:
                publishers.remove(website)

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
                    zoneid=zone['zoneId'],
                    dayprice=0,
                    x0=0,
                    x1=0,
                    y0=0,
                    y1=0
                )
                Prices.commit()

            price = Prices.query.filter_by(
                        zoneid=zone['zoneId']
                    ).first()

            tmpdict = {}

            tmpdict['publisherId'] = zone['publisherId']
            tmpdict['zoneName'] = zone['zoneName']
            tmpdict['width'] = zone['width']
            tmpdict['height'] = zone['height']
            tmpdict['zoneId'] = zone['zoneId']
            tmpdict['comments'] = zone['comments']
            tmpdict['type'] = zone['type']

            tmpdict['price'] = price.dayprice
            tmpdict['x0'] = price.x0
            tmpdict['x1'] = price.x1
            tmpdict['y0'] = price.y0
            tmpdict['y1'] = price.y1

            # get stats and ignore if none
            try:
                ztatz = Impressions.query.filter_by(
                            zoneid=zone['zoneId']
                        ).first()
                tmpdict['impressions'] = ztatz.impressions
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
        allzones=all_zones,
        publishers=publishers,
        isadmin=amiadmin(),
        form=form
    )


@blueprint.route('/campaign')
@blueprint.route('/campaign/duration/<int:no_weeks>')
@blueprint.route('/campaign/details/<int:campaign_no>')
@blueprint.route('/campaign/uuid/<string:invoice_uuid>')
@login_required
def campaign(no_weeks=None, campaign_no=None, invoice_uuid=None):
    """
    Details related to one campaign only.
    or
    Get and display all campaigns belonging to user.
    """
    # And now we are checking campaigns
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
        Payments, Orders.paymentno == Payments.id).join(
            Banner, Orders.bannerid == Banner.id).add_columns(
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
                Payments.posdata,
                Payments.btcpayserver_id,
                Payments.received_at,
                Payments.confirmed_at,
                Payments.fiat_amount,
                Payments.fiat,
                Banner.filename,
                Banner.url,
                Banner.width,
                Banner.height,
                Banner.content,
                Banner.icon,
                Banner.type
            )

    # We are converting invoice UUID we generated for campaing_no
    # to quickly find an invoice from payment processor user interface
    # Please not there may be more campaigns related to one invoice,
    # we are just showing one of them!
    if invoice_uuid is not None:
        dbquery = dbqueryall.filter(Payments.posdata == invoice_uuid).first()
        if dbquery.campaigno:
            campaign_no = dbquery.campaigno

    # We want details related to one campaign, not a list of all so we will
    # display that data and quit this function
    if campaign_no is not None:
        # let's try to connect to the payment system to get campaign details
        btcpayclient_location = current_app.config.get('APP_DIR') + '/data/btcpayserver.client'
        try:
            with open(btcpayclient_location, 'rb') as file:
                btcpayclient = pickle.load(file)
        except Exception as e:
            log.debug("Exception")
            log.exception(e)
            log.info("Problems with accessing payment processor.")
            return render_template('users/paymentsystem-problems.html')

        # we are getting overview of particular campaign from local database
        dbquery = dbqueryall.filter(Orders.campaigno == campaign_no).first()
        # and now we check details of that payment from downstream payment processor
        log.debug(dbquery)
        if dbquery.btcpayserver_id:  # we are checking it only for historical
                                     # purposes to achieve compatibility with previous releases
            btcpayinv = btcpayclient.get_invoice(dbquery.btcpayserver_id)
            log.debug(pprint.pformat(btcpayinv, depth=5))
            cryptoInfo = btcpayinv['cryptoInfo']
            status = btcpayinv['status']
        else:
            cryptoInfo = []
            status = "unknown"

        # we show details only to campaign owners or admins
        if dbquery.user_id == current_user.id or amiadmin():
            # Render the page and quit
            return render_template(
                'users/campaign-single.html',
                now=datetime.utcnow(),
                datemin=datetime.min,
                dbquery=dbquery,
                cryptoInfo=cryptoInfo,
                status=status
            )
        else:
            # We politely redirecting 'hackers' to all campaigns
            return redirect(url_for("user.campaign"), code=302)

    # admin gets all campaigns for all users limited to requested time period
    dbqueryall = dbqueryall.filter(Orders.stops_at > datetime.utcnow() - timedelta(weeks=no_weeks))
    if amiadmin():
        all_campaigns = dbqueryall.all()
    else:
        all_campaigns = dbqueryall.filter(Orders.user_id == current_user.id).all()

    # Render the page and quit
    return render_template(
        'users/campaign.html',
        all_campaigns=all_campaigns,
        roles=current_user.roles,
        now=datetime.utcnow(),
        datemin=datetime.min,
        no_weeks=no_weeks
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

        # ignore the websites on our blacklist 
        for blackwebsite in current_app.config.get('REVIVE_IGNORED_WEBSITES'):
            for website in publishers:
                if website['publisherName'] == blackwebsite:
                    publishers.remove(website)

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
                               zone_name=zone_name, banner=banner,
                               step='chose-date')

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
            campaigno=campaign,
            zoneid=zone_id,
            created_at=datetime.utcnow(),
            begins_at=begin,
            stops_at=enddate,
            paymentno=0,
            bannerid=banner_id,
            name=randomname,
            comments=zone_name,
            impressions=0,
            user_id=current_user.id
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
            campaigno=campaign,
            user_id=current_user.id
        )

        return render_template(
            'users/order.html',
            banner_id=banner_id,
            banner=banner,
            datestart=datestart,
            datend=datend,
            image_url=image_url,
            zone_id=zone_id,
            days=totaltime.days,
            dayprice=price.dayprice,
            step='order'
        )


@blueprint.route('/basket', methods=['get'])
@login_required
def basket():
    """Present his/her basket to customer."""

    basket = []
    price = []
    totalprice = 0
    basket_sql = Basket.query.filter_by(user_id=current_user.id).all()
    # Checks to see if the user has already started a cart.
    if basket_sql:
        for item in basket_sql:
            order_sql = Orders.query.filter_by(
                campaigno=item.campaigno).join(Banner).join(Prices).add_columns(
                Banner.filename, Banner.url, Banner.width, Banner.height,
                    Banner.content, Banner.icon, Banner.type, Prices.dayprice).first()
            basket.append(order_sql)
            begin = order_sql[0].begins_at
            enddate = order_sql[0].stops_at
            campaign_time = enddate - begin
            currencyprice = order_sql.dayprice/100*(campaign_time.days+1)
            price.append([item.campaigno, currencyprice])
            totalprice += currencyprice
    else:
        basket = 0
        price = 0

    return render_template(
        'users/basket.html',
        basket=basket,
        price=price,
        totalprice=totalprice,
        present=datetime.now()-timedelta(days=1)
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
                try:
                    removed = r.ox.deleteCampaign(sessionid, order.campaigno)
                    log.debug(
                        "Campaign #%s removed from Revive?: %s" % (
                            str(order.campaigno),
                            str(removed)
                            )
                    )
                except:
                    log.info(
                        "Campaign %s was not removed from Revive because it was not found in there. It can be an error or you removed it manually before in Revive interface." % (
                            str(order.campaigno)
                            )
                    )
                Orders.query.filter_by(campaigno=order.campaigno).delete()
                flash('Your basket was removed sucessfully.', 'success')
        else:
            try:
                removed = r.ox.deleteCampaign(sessionid, campaign_id)
                log.debug(
                    "Campaign #%s removed from Revive?: %s" % (
                            str(campaign_id),
                            str(removed)
                        )
                )
            except:
                log.info(
                    "Campaign %s was not removed from Revive because it was not found in there. It can be an error or you removed it manually before in Revive interface." % (
                        str(campaign_id)
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
        flash('There was an error in processing your request. If situation repeats, please contact us.', 'error')
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


@blueprint.route('/pay')
@login_required
def pay():
    """Pay a campaign."""
    # let's try to connect to the payment system
    btcpayclient_location = current_app.config.get('APP_DIR')+'/data/btcpayserver.client'
    try:
        with open(btcpayclient_location, 'rb') as file:
            btcpayclient = pickle.load(file)
    except Exception as e:
        log.debug("Exception")
        log.exception(e)
        log.info("Problems with accessing payment processor.")
        return render_template('users/paymentsystem-problems.html')

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
            total += totalcurrencyprice
            label = label + "[C#{} Z#{} B#{} {} ↦ {} {:.2f}{}] ※ ".format(
                item.campaigno,
                order_sql[0].zoneid,
                order_sql[0].bannerid,
                begin.strftime("%d/%m/%y"),
                enddate.strftime("%d/%m/%y"),
                totalcurrencyprice,
                current_app.config.get('FIAT')
            )
    else:
        basket = 0
        log.error("Trying to pay for empty basket.")
        return redirect(url_for("user.basket"), code=302)

    randomid = str(uuid.uuid4())
    buyer = {
        "email": current_user.email,
        "name": current_user.username,
        "notify": "true",
    }

    # prepare invoice request
    btcpayinvreq = {
        "price": total,
        "currency": current_app.config.get('FIAT'),
        # "transactionSpeed": "high",
        "itemDesc": label,
        "posData": randomid,
        "orderId": randomid,
        "buyer": buyer,
        "extendedNotifications": "true",
        "notificationURL": current_app.config.get('OUR_URL') + 'ipn',
        "redirectURL": current_app.config.get('OUR_URL') + 'campaign/uuid/' + randomid,
    }
    # contact payment processor and ask for invoice
    btcpayinv = btcpayclient.create_invoice(btcpayinvreq)
    log.debug(pprint.pformat(btcpayinv, depth=5))

    # Creating database record for payment and linking it into orders.
    payment_sql = Payments.create(
        created_at=datetime.utcnow(),
        user_id=current_user.id,
        btcpayserver_id=btcpayinv['id'],
        confirmed_at=datetime.min,
        received_at=datetime.min,
        fiat=btcpayinv['currency'],
        fiat_amount=btcpayinv['price'],
        posdata=randomid,
    )
    # we need payment numer id to properly relate tables
    paymentno = payment_sql.id

    for item in basket:
        Orders.query.filter_by(campaigno=item[0].campaigno).update({"paymentno": paymentno})
        Orders.commit()

    # It looks that payment page is ready to be shown, so we remove the content of basket
    Basket.query.filter_by(user_id=current_user.id).delete()
    Basket.commit()

    # redirect to payment page
    return redirect(btcpayinv['url'], code=302)


@blueprint.route('/admin/pair', methods=['GET', 'POST'])
@roles_accepted('admin')
def btcpaypair():
    """Payment processor pairing."""
    btcpayclient_location = current_app.config.get('APP_DIR')+'/data/btcpayserver.client'
    print(btcpayclient_location)
    fiat = current_app.config.get('FIAT')
    # Recognise if pairing is done and valid
    try:

        with open(btcpayclient_location, 'rb') as file:
            btcpayclient = pickle.load(file)

        # try if it works
        rates = btcpayclient.get_rates()
        log.debug(pprint.pformat(rates, depth=5))
        state = True
        log.debug("We found a working processor.")
    except Exception as e:
        log.debug(e)
        log.debug("We are unable to bind to the processor.")
        state = False

    # Form to update/pair
    form = AddPairingTextForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                btcpayuri = current_app.config.get('BTCPAY_URI')
                btcpayclient = btcpay.BTCPayClient.create_client(
                    host=btcpayuri,
                    code=form.pairing_code.data
                )
                fo = open(btcpayclient_location, "wb")
                pickle.dump(btcpayclient, fo)
                fo.close()
                flash('Your payment processor was paired successfully.', 'success')
                state = True
            except Exception as e:
                log.debug("Exception")
                log.exception(e)
                flash('The pairing process failed. Check logs or repeat.', 'error')
                state = False
        else:
            flash_errors(form)

    return render_template(
        'users/pair.html',
        state=state,
        form=form
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
        userlog=userlog
    )
