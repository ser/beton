import json
import names
import random
import requests
import uuid
import xmlrpc.client

from datetime import datetime
from datetime import timedelta
from dateutil import parser
from PIL import Image

from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from flask_uploads import UploadSet, IMAGES

# from beton.extensions import images
from beton.logger import log
from beton.user.forms import AddBannerForm, ChangeOffer
from beton.user.models import Banner, Basket, Orders, Payments, Prices, User  # , Zone2Campaign
from beton.utils import flash_errors, reviveme

images = UploadSet('images', IMAGES)
blueprint = Blueprint('user', __name__, url_prefix='/me', static_folder='../static')


def amiadmin():
    if current_user.has_role('admin'):
        isadmin = True
    else:
        isadmin = False
    return isadmin


def random_color():
    color = "%03x" % random.randint(0, 0xFFF)
    return "#"+str(color)


def krakenrate(coin):
    # ask kraken for rate: https://api.kraken.com/0/public/AssetPairs
    # Bitcoin to Euro:
    if coin == "BTC":
        base = "XXBTZEUR"
    # Litecoin to Euro:
    elif coin == "LTC":
        base = "XLTCZEUR"
    # Bitcoin Cash to Euro
    elif coin == "BCH":
        base = "BCHEUR"
    exuri = "https://api.kraken.com/0/public/Ticker?pair="+base
    rate = requests.get(exuri)
    json_data = rate.text
    fj = json.loads(json_data)
    try:
        exrate = fj["result"][base]["c"][0]
    except Exception as e:
        log.debug("Exception")
        log.exception(e)
        exrate = 0
    return exrate


def coinbasereate(coin):
    # ask coinbase for rate
    # Bitcoin to Euro:
    if coin == "BTC":
        exuri = "https://api.coinbase.com/v2/prices/BTC-EUR/buy"
    # Litecoin to Euro
    elif coin == "LTC":
        exuri = "https://api.coinbase.com/v2/prices/LTC-EUR/buy"
    # Bitcoin Cash to Euro
    elif coin == "BCH":
        exuri = "https://api.coinbase.com/v2/prices/BCH-EUR/buy"
    rate = requests.get(exuri)
    json_data = rate.text
    fj = json.loads(json_data)
    try:
        exrate = fj['data']['amount']
    except Exception as e:
        log.debug("Exception")
        log.exception(e)
        exrate = 0
    return exrate


def getexrate(coin):
    exrate = krakenrate(coin)
    if exrate == 0:
        exrate = coinbasereate(coin)
    return exrate


def minerfee(amount, electrum_url):
    # ask electrum for an average miner fee
    # we assume that an average transaction is about 258 bytes long
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


@blueprint.url_value_preprocessor
def get_basket(endpoint, values):
    """We need basket on every view if authenticated"""
    if current_user.is_authenticated:
        basket_sql = Basket.query.filter_by(user_id=current_user.id).all()
        if basket_sql:
            g.basket = len(basket_sql)
        else:
            g.basket = 0

    # keeping constant connection to Revive instance
    r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                  verbose=False)
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
            Banner.create(filename=filename, owner=current_user.id,
                          url=form.banner_url.data, created_at=datetime.utcnow(),
                          width=width, height=height,
                          comments=form.banner_comments.data)
            # flash(str(width)+' '+str(height), 'success')
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
    return render_template('users/bannerz.html', all_banners=all_banners,
                           all_urls=all_urls)


@blueprint.route('/offer', methods=['GET', 'POST'])
@login_required
def offer():
    """Get and display all possible websites and zones in them."""
    form = ChangeOffer()

    r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                  verbose=False)
    sessionid = session['revive']

    # Get all publishers (websites)
    publishers = r.ox.getPublisherListByAgencyId(sessionid,
                                                 current_app.config.get('REVIVE_AGENCY_ID'))

    all_zones = []
    for website in publishers:
        # get zones from Revive
        allzones = r.ox.getZoneListByPublisherId(sessionid,
                                                 website['publisherId'])
        for zone in allzones:
            price = Prices.query.filter_by(zoneid=zone['zoneId']).first()

            tmpdict = {}
            if price:
                tmpdict['price'] = price.dayprice
            else:
                tmpdict['price'] = 0
            tmpdict['publisherId'] = zone['publisherId']
            tmpdict['zoneName'] = zone['zoneName']
            tmpdict['width'] = zone['width']
            tmpdict['height'] = zone['height']
            tmpdict['zoneId'] = zone['zoneId']
            tmpdict['comments'] = zone['comments']

            # ask for stats
            try:
                ztatz = r.ox.getZoneDailyStatistics(sessionid,
                                                    zone['zoneId'],
                                                    datetime.now() - parser.relativedelta(months=1),
                                                    datetime.now()
                                                    )
                # tmpdict['impressions'] = ztatz[0]['impressions']
                tmpdict['impressions'] = ztatz
            except Exception as e:
                log.debug("Exception")
                log.exception(e)
                tmpdict['impressions'] = 0

            all_zones.append(tmpdict)

    if request.method == 'POST':
        if form.validate_on_submit():
            for zone in all_zones:
                if form.zoneid.data == zone['zoneId']:
                    if zone['price']:
                        Prices.query.filter_by(zoneid=form.zoneid.data).update({"dayprice": form.zoneprice.data})
                        Prices.commit()  # TODO: it should use .update
                    else:
                        Prices.create(zoneid=form.zoneid.data,
                                      dayprice=form.zoneprice.data)

        return redirect(url_for('user.offer'))

    # Render the page and quit
    return render_template('users/offer.html', allzones=all_zones,
                           publishers=publishers, isadmin=amiadmin(),
                           form=form)


@blueprint.route('/campaign')
@blueprint.route('/campaign/<int:no_weeks>')
@login_required
def campaign(no_weeks=None):
    """Get and display all campaigns belonging to user."""
    if not no_weeks:
        no_weeks = 8
    r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                  verbose=False)
    sessionid = session['revive']

    all_advertisers = r.ox.getAdvertiserListByAgencyId(sessionid,
                                                       current_app.config.get('REVIVE_AGENCY_ID'))

    # Try to find out if the customer is already registered in Revive, if not,
    # register him
    try:
        next(x for x in all_advertisers if x['advertiserName'] ==
             current_user.username)
    except StopIteration:
        # log.debug('Created user: ', current_user.username)
        r.ox.addAdvertiser(sessionid, {'agencyId': current_app.config.get('REVIVE_AGENCY_ID'),
                                       'advertiserName': current_user.username,
                                       'emailAddress': current_user.email,
                                       # 'contactName': current_user.first_name+"
                                       # "+current_user.lastname, # TODO: check if values are set
                                       'contactName': current_user.username,
                                       'comments': current_app.config.get('USER_APP_NAME')
                                       })

    all_advertisers = r.ox.getAdvertiserListByAgencyId(sessionid,
                                                       current_app.config.get('REVIVE_AGENCY_ID'))
    advertiser_id = int(next(x for x in all_advertisers if x['advertiserName'] ==
                        current_user.username)['advertiserId'])

    # dirty auth hack, TODO to be rewritten
    if amiadmin():
        all_campaigns = []
        for advertiser in all_advertisers:
            all_campaigns = all_campaigns + r.ox.getCampaignListByAdvertiserId(sessionid, advertiser['advertiserId'])
    else:
        all_campaigns = r.ox.getCampaignListByAdvertiserId(sessionid, advertiser_id)

    # find all banners related to campaigns
    banners = []
    if len(all_campaigns) > 0:
        for x in all_campaigns:
            banners.append([x['campaignId'], r.ox.getBannerListByCampaignId(sessionid,
                                                                            x['campaignId'])])
    all_campaigns_standardized = []

    for campaign in all_campaigns:
        endtime = datetime.strptime(campaign['endDate'].value,
                                    '%Y%m%dT%H:%M:%S')
        nowtime = datetime.now()
        # limit campaigns to no_weeks only
        if (nowtime - endtime) < timedelta(weeks=no_weeks):
            # log.debug((nowtime - endtime))

            # check orders what do we know about that campaign
            orderinfo = Orders.query.filter_by(campaigno=campaign['campaignId']).first()
            sql = Payments.query.filter_by(id=orderinfo.paymentno).first()
            tasks = {}
            tasks['campaignId'] = campaign['campaignId']
            tasks['campaignName'] = campaign['campaignName']
            tasks['comments'] = campaign['comments']
            starttime = datetime.strptime(campaign['startDate'].value,
                                          '%Y%m%dT%H:%M:%S')
            tasks['startDate'] = starttime
            tasks['endDate'] = endtime
            present = datetime.now()
            if endtime < present:
                tasks['expired'] = True
            else:
                tasks['expired'] = False

            try:
                tasks['address'] = sql.address
            except BaseException:
                tasks['address'] = "0"

            try:
                tasks['amount_coins'] = sql.total_coins
            except BaseException:
                tasks['amount_coins'] = 0

            try:
                tasks['chain'] = sql.blockchain
            except BaseException:
                tasks['chain'] = "0"

            try:
                if int(sql.txno) == 0:
                    tasks['ispaid'] = False
            except BaseException:
                tasks['ispaid'] = True

            # ask for stats
            try:
                ztatz = r.ox.campaignBannerStatistics(sessionid,
                                                      campaign['campaignId'],
                                                      datetime(2011, 1, 1, 0, 0),
                                                      datetime.now()
                                                      )
                tasks['impressions'] = ztatz[0]['impressions']
            except BaseException:
                tasks['impressions'] = 0

            # We ignore campaigns in the basket
            if tasks['address'] != "0":
                all_campaigns_standardized.append(tasks)

    # Render the page and quit
    return render_template('users/campaign.html',
                           all_campaigns=all_campaigns_standardized,
                           banners=banners,
                           roles=current_user.roles,
                           now=datetime.utcnow(),
                           no_weeks=no_weeks)


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
        fullname = names.get_full_name()
        tasks['id'] = order.campaigno
        tasks['title'] = fullname
        tasks['allDay'] = "true"
        tasks['color'] = random_color()
        tasks['resourceId'] = order.zoneid
        # calendar['url'] = ''
        # starttime = datetime.strptime(order.begins_at, '%Y%m%dT%H:%M:%S')
        # endtime = datetime.strptime(order.stops_at, '%Y%m%dT%H:%M:%S')
        starttime = order.begins_at
        endtime = order.stops_at
        tasks['start'] = starttime.strftime("%Y-%m-%d")
        tasks['end'] = endtime.strftime("%Y-%m-%d")
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
        publishers = r.ox.getPublisherListByAgencyId(sessionid,
                                                     current_app.config.get('REVIVE_AGENCY_ID'))

        # Get zones from Revive
        all_zones = []

        for website in publishers:
            allzones = r.ox.getZoneListByPublisherId(sessionid,
                                                     website['publisherId'])
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
        all_advertisers = r.ox.getAdvertiserListByAgencyId(sessionid,
                                                           current_app.config.get('REVIVE_AGENCY_ID'))
        advertiser_id = int(next(x for x in all_advertisers if x['advertiserName'] ==
                            current_user.username)['advertiserId'])

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

        # # ask for x rate
        # exrate = getexrate()
        # if exrate == 0:
        #    return render_template('users/electrum-problems.html')

        # totalcurrencyprice = price.dayprice/100*(totaltime.days+1)
        # totalcoinprice = totalcurrencyprice / float(exrate)

        Orders.create(campaigno=campaign,
                      zoneid=zone_id,
                      created_at=datetime.utcnow(),
                      begins_at=begin,
                      stops_at=enddate,
                      paymentno=0,
                      bannerid=banner_id
                      )

        Basket.create(campaigno=campaign,
                      user_id=current_user.id
                      )

        return render_template('users/order.html',
                               banner_id=banner_id,
                               datestart=datestart,
                               datend=datend,
                               image_url=image_url,
                               zone_id=zone_id,
                               days=totaltime.days,
                               dayprice=price.dayprice,
                               step='order')


@blueprint.route('/basket', methods=['get'])
@login_required
def basket():
    """Present basket to customer."""

    basket = []
    price = []
    basket_sql = Basket.query.filter_by(user_id=current_user.id).all()
    # Checks to see if the user has already started a cart.
    if basket_sql:
        for item in basket_sql:
            order_sql = Orders.query.filter_by(campaigno=item.campaigno).join(Banner).join(Prices).add_columns(
                Banner.filename, Banner.url, Banner.width, Banner.height, Prices.dayprice).first()
            basket.append(order_sql)
            begin = order_sql[0].begins_at
            enddate = order_sql[0].stops_at
            totaltime = enddate - begin
            totalcurrencyprice = order_sql.dayprice/100*(totaltime.days+1)
            price.append([item.campaigno, "EUR", totalcurrencyprice])

            exchange_prices = current_app.config.get('EXCHANGE_PRICES')
            for coin in exchange_prices:
                # try to get exchange values from two sources, and give up
                exrate = getexrate(coin)
                if exrate == 0:
                    return render_template('users/electrum-problems.html')
                totalcoinprice = format(totalcurrencyprice / float(exrate), '.9f')
                price.append([item.campaigno, coin, totalcoinprice])
    else:
        basket = 0

    return render_template('users/basket.html', basket=basket,
                           price=price, present=datetime.now())


@blueprint.route('/clear/basket/<int:campaign_id>')
@login_required
def clear_basket(campaign_id):
    try:
        r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                      verbose=False)
        sessionid = session['revive']
        if campaign_id == 0:
            all_basket = Basket.query.filter_by(user_id=current_user.id).all()
            # Removing these campaigns from Revive as not useful in future
            Basket.query.filter_by(user_id=current_user.id).delete()
            for order in all_basket:
                removed = r.ox.deleteCampaign(sessionid, order.campaigno)
                log.debug("Campaign removed from Revive:")
                log.debug(order.campaigno)
                log.debug(removed)
                Orders.query.filter_by(campaigno=order.campaigno).delete()
        else:
            removed = r.ox.deleteCampaign(sessionid, campaign_id)
            log.debug("Campaign removed from Revive:")
            log.debug(campaign_id)
            log.debug(removed)
            Basket.query.filter_by(user_id=current_user.id, campaigno=campaign_id).delete()
            Orders.query.filter_by(campaigno=campaign_id).delete()
        Basket.commit()
        Orders.commit()
    except Exception as e:
        log.debug("Exception")
        log.exception(e)
    return redirect(url_for("user.basket"), code=302)


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
    basket_sql = Basket.query.filter_by(user_id=current_user.id).all()
    # Checks to see if the user has already started a cart.
    if basket_sql:
        for item in basket_sql:
            order_sql = Orders.query.filter_by(campaigno=item.campaigno).join(Banner).join(Prices).add_columns(
                Banner.filename, Banner.url, Banner.width, Banner.height, Prices.dayprice).first()
            basket.append(order_sql)
            begin = order_sql[0].begins_at
            enddate = order_sql[0].stops_at
            totaltime = enddate - begin
            totalcurrencyprice = order_sql.dayprice/100*(totaltime.days+1)
            totalcoinprice = totalcurrencyprice / float(exrate)
            total += totalcurrencyprice
            cointotal += totalcoinprice
    else:
        basket = 0
        log.error("Trying to pay for empty basket.")
        return redirect(url_for("user.basket"), code=302)

    # kindly ask miss electrum for an invoice which expires in 20 minutes
    # headers = {'content-type': 'application/json'}
    params = {
        "amount": cointotal,
        "expiration": 1212
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
    except Exception as e:
        log.debug("Exception")
        log.exception(e)
        return render_template('users/electrum-problems.html')

    fee = minerfee(cointotal, electrum_url)

    # creating database record for payment and linking it into orders
    payment_sql = Payments.create(
        blockchain=payment,
        address=addr,
        total_coins=cointotal,
        txno=0,
        created_at=datetime.utcnow()
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
    return render_template('users/pay.html',
                           total=total,
                           orders=len(basket),
                           exrate=exrate,
                           fee=fee,
                           currency=payment_system[0],
                           electrum=result)


@blueprint.route('/admin/users', methods=['get', 'post'])
@login_required
def listusers():
    if amiadmin():  # only admins get see this list
        all_users = User.query.all()
        return render_template('users/listusers.html',
                               all_users=all_users)
    else:
        flash('You need admin privileges.', 'info')
        return redirect(url_for('public.home'))
