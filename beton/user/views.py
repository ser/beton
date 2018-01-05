# import logging
import json
import requests
# import uuid
import xmlrpc.client
from datetime import datetime
from dateutil import parser

import names
from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from PIL import Image

from beton.extensions import images
from beton.user.forms import AddBannerForm, ChangeOffer
from beton.user.models import Banner, Basket, Orders, Prices, Zone2Campaign
from beton.utils import flash_errors, reviveme

blueprint = Blueprint('user', __name__, url_prefix='/me', static_folder='../static')


@blueprint.url_value_preprocessor
def get_basket(endpoint, values):
    """We need basket on every view"""
    basket_sql = Basket.query.filter_by(user_id=current_user.id).all()
    if basket_sql:
        g.basket = len(basket_sql)


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

    if 'revive' in session:
        sessionid = session['revive']
        try:
            r.ox.getUserList(sessionid)
        except:
            sessionid = reviveme(r)
            session['revive'] = sessionid
    else:
        sessionid = reviveme(r)
        session['revive'] = sessionid

    # Get all publishers (websites)
    publishers = r.ox.getPublisherListByAgencyId(sessionid,
                                                 current_app.config.get('REVIVE_AGENCY_ID'))

    if current_user.has_role('admin'):
        isadmin = True
    else:
        isadmin = False
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
            except:
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
                           publishers=publishers, isadmin=isadmin,
                           form=form)


@blueprint.route('/campaign')
@login_required
def campaign():
    """Get and display all camapigns belonging to user."""
    r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                  verbose=False)
    if 'revive' in session:
        sessionid = session['revive']
        try:
            r.ox.getUserList(sessionid)
        except:
            sessionid = reviveme(r)
            session['revive'] = sessionid
    else:
        sessionid = reviveme(r)
        session['revive'] = sessionid

    all_advertisers = r.ox.getAdvertiserListByAgencyId(sessionid,
                                                       current_app.config.get('REVIVE_AGENCY_ID'))
    # Try to find out if the customer is already registered in Revive, if not,
    # register him
    try:
        next(x for x in all_advertisers if x['advertiserName'] ==
             current_user.username)
    except StopIteration:
        # logging.warning('Created user: ', current_user.username)
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
    if current_user.has_role('admin'):
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
        # check orders what do we know about that campaign
        orderinfo = Orders.query.filter_by(campaigno=campaign['campaignId']).first()
        tasks = {}
        tasks['campaignId'] = campaign['campaignId']
        tasks['campaignName'] = campaign['campaignName']
        tasks['comments'] = campaign['comments']
        starttime = datetime.strptime(campaign['startDate'].value,
                                      '%Y%m%dT%H:%M:%S')
        endtime = datetime.strptime(campaign['endDate'].value,
                                    '%Y%m%dT%H:%M:%S')
        tasks['startDate'] = starttime
        tasks['endDate'] = endtime
        present = datetime.now()
        if endtime < present:
            tasks['expired'] = True
        else:
            tasks['expired'] = False
        try:
            tasks['amount_btc'] = orderinfo.amount_btc
        except:
            tasks['amount_btc'] = 0
        try:
            tasks['ispaid'] = orderinfo.ispaid
        except:
            tasks['ispaid'] = False
        try:
            tasks['btc_address'] = orderinfo.btcaddress
        except:
            tasks['btc_address'] = "deadbeef"

        # ask for stats
        try:
            ztatz = r.ox.campaignBannerStatistics(sessionid,
                                                  campaign['campaignId'],
                                                  datetime(2011, 1, 1, 0, 0),
                                                  datetime.now()
                                                  )
            tasks['impressions'] = ztatz[0]['impressions']
        except:
            tasks['impressions'] = 0

        all_campaigns_standardized.append(tasks)

    # Render the page and quit
    return render_template('users/campaign.html',
                           all_campaigns=all_campaigns_standardized,
                           banners=banners,
                           roles=current_user.roles,
                           now=datetime.utcnow())


@blueprint.route('/api/all_campaigns_in_zone/<int:zone_id>')
@login_required
def api_all_campaigns(zone_id):
    """JSON."""
    r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                  verbose=False)
    if 'revive' in session:
        sessionid = session['revive']
        try:
            r.ox.getUserList(sessionid)
        except:
            sessionid = reviveme(r)
            session['revive'] = sessionid
    else:
        sessionid = reviveme(r)
        session['revive'] = sessionid

    all_advertisers = r.ox.getAdvertiserListByAgencyId(sessionid,
                                                       current_app.config.get('REVIVE_AGENCY_ID'))
    advertiser_id = int(next(x for x in all_advertisers if x['advertiserName'] ==
                        current_user.username)['advertiserId'])
    ac = []
    for x in all_advertisers:
        fullname = names.get_full_name()
        for y in r.ox.getCampaignListByAdvertiserId(sessionid, x['advertiserId']):
            z2c = Zone2Campaign.query.filter_by(placement_id=y['campaignId']).first()
            if z2c:
                if zone_id == int(z2c.zone_id) or zone_id == 0:
                    tasks = {}
                    tasks['id'] = y['campaignId']
                    if x['advertiserId'] == advertiser_id:
                        tasks['title'] = y['campaignName']
                        tasks['class'] = 'event-info'
                    else:
                        tasks['title'] = fullname
                    tasks['zone'] = int(z2c.zone_id)
            # calendar['url'] = ''
            # calendar['class'] = ''
                    starttime = datetime.strptime(y['startDate'].value,
                                                  '%Y%m%dT%H:%M:%S')
                    endtime = datetime.strptime(y['endDate'].value,
                                                '%Y%m%dT%H:%M:%S')
                    tasks['start'] = 1000*int(starttime.timestamp())
                    tasks['end'] = 1000*int(endtime.timestamp())
                    ac.append(tasks)

    a = {}
    a['success'] = 1
    a['result'] = ac

    return jsonify(a)


@blueprint.route('/order', methods=['get', 'post'])
@login_required
def order():
    """Order a campaign."""
    r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                  verbose=False)
    if 'revive' in session:
        sessionid = session['revive']
        try:
            r.ox.getUserList(sessionid)
        except:
            sessionid = reviveme(r)
            session['revive'] = sessionid
    else:
        sessionid = reviveme(r)
        session['revive'] = sessionid

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

        begin = datetime.strptime(datestart, "%d/%m/%Y")
        enddate = datetime.strptime(datend, "%d/%m/%Y")
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

        # ask kraken for rate
        krkuri = "https://api.kraken.com/0/public/Ticker?pair=XXBTZEUR"
        krkr = requests.get(krkuri)
        json_data = krkr.text
        fj = json.loads(json_data)
        exrate = fj["result"]['XXBTZEUR']["c"][0]
        totalcurrencyprice = price.dayprice/100*(totaltime.days+1)
        totalbtcprice = totalcurrencyprice / float(exrate)

        Orders.create(campaigno=campaign,
                      zoneid=zone_id,
                      created_at=datetime.utcnow(),
                      amount_days=totaltime.days+1,
                      paymentno=0,
                      bannerid=banner_id
                      )

        Basket.create(campaigno=campaign,
                      user_id=current_user.id
                      )

        return render_template('users/order.html', banner_id=banner_id,
                               datestart=datestart, datend=datend, image_url=image_url,
                               zone_id=zone_id, days=totaltime.days,
                               exrate=exrate, dayprice=price.dayprice,
                               btctotal=totalbtcprice, step='order')


@blueprint.route('/basket', methods=['get'])
@login_required
def basket():
    """Present basket to customer.
    r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                  verbose=False)
    if 'revive' in session:
        sessionid = session['revive']
        try:
            r.ox.getUserList(sessionid)
        except:
            sessionid = reviveme(r)
            session['revive'] = sessionid
    else:
        sessionid = reviveme(r)
        session['revive'] = sessionid
    """

    # Checks to see if the user has already started a cart.
    basket_sql = Basket.query.filter_by(user_id=current_user.id).all()
    basket = []
    banners = []
    if basket_sql:
        for item in basket_sql:
            order_sql = Orders.query.filter_by(campaigno=item.campaigno).first()
            basket.append(order_sql)
            banner_sql = Banner.query.filter_by(id=order_sql.bannerid).first()
            banners.append(banner_sql)
    else:
        basket = 0

    return render_template('users/basket.html', basket=basket,
                           banners=banners)


@blueprint.route('/clear/basket/<int:campaign_id>')
@login_required
def clear_basket(campaign_id):
    if campaign_id == "0":
        basket_sql = Basket.query.filter_by(user_id=current_user.id).all()
        basket_sql.delete()
    else:
        basket_sql = Basket.query.filter_by(user_id=current_user.id, campaigno=campaign_id).first()
        basket_sql.delete()
    return redirect(url_for("user.basket"), code=302)


@blueprint.route('/pay', methods=['get', 'post'])
@login_required
def pay():
    """Pay a campaign."""

    pass
    """
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

        begin = datetime.strptime(datestart, "%d/%m/%Y")
        enddate = datetime.strptime(datend, "%d/%m/%Y")
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
        # banno = r.ox.addBanner(sessionid, diki)

        # ask kraken for rate
        krkuri = "https://api.kraken.com/0/public/Ticker?pair=XXBTZEUR"
        krkr = requests.get(krkuri)
        json_data = krkr.text
        fj = json.loads(json_data)
        exrate = fj["result"]['XXBTZEUR']["c"][0]
        totalcurrencyprice = price.dayprice/100*(totaltime.days+1)
        totalbtcprice = totalcurrencyprice / float(exrate)

        # kindly ask miss electrum for an invoice which expires in 20 minutes
        # headers = {'content-type': 'application/json'}
        params = {
            "amount": totalbtcprice,
            "expiration": 1212
        }
        payload = {
            "id": str(uuid.uuid4()),
            "method": "addrequest",
            "params": params
        }

        electrum_url = current_app.config.get('ELECTRUM_RPC')
        electrum = requests.post(electrum_url, json=payload).json()
        result = electrum['result']
        # more debug if needed
        # print(electrum_url)
        # print(result)
        # print(params)
        # print(payload)
        btcaddr = result['address']

        Orders.create(campaigno=campaign,
                      amount_btc=totalbtcprice,
                      zoneid=zone_id,
                      created_at=datetime.utcnow(),
                      ispaid=False,
                      btcaddress=btcaddr)

        #  kindly ask miss electrum for a ping when our address changes
        params = {
            "address": btcaddr,
            "URL": current_app.config.get('OUR_URL')+'ipn'
        }
        payload = {
            "id": str(uuid.uuid4()),
            "method": "notify",
            "params": params
        }
        # ipn_please = requests.post(electrum_url, json=payload).json()

        return render_template('users/order.html', banner_id=banner_id,
                               datestart=datestart, datend=datend, image_url=image_url,
                               zone_id=zone_id, days=totaltime.days,
                               exrate=exrate, dayprice=price.dayprice,
                               btctotal=totalbtcprice, electrum=result,
                               step='pay')
"""
