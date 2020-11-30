# -*- coding: utf-8 -*-
import btcpay
import names
import pickle
import pprint
import random
import uuid

from datetime import datetime, timedelta
from dateutil.relativedelta import *
from PIL import Image, ImageDraw

from flask import Blueprint, current_app, flash, g, jsonify, redirect
from flask import render_template, request, session, url_for
from flask_security import current_user, login_required, roles_accepted
from flask_uploads import UploadSet, IMAGES

from beton.extensions import cache
from beton.logger import log
from beton.user.forms import AddBannerForm, AddBannerTextForm, AddPairingTextForm, AddWebsiteForm, AddZoneForm, ChangeOffer
from beton.user.models import Banner, Basket, Campaignes, Impressions, Log, Orders, Payments, Prices, User, Websites, Zones
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

    zonedata = Zones.query.filter_by(id=zone).first()
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


@blueprint.route('/add/zone', methods=['GET', 'POST'])
@blueprint.route('/edit/zone/<int:zoneid>', methods=['GET', 'POST'])
@roles_accepted('admin')
def add_zone(zoneid=None):
    """Add a zone."""
    all_zones = Zones.query.join(Websites).all()
    form = AddZoneForm()
    form.zone_website.choices = [(w.id, w.name) for w in
                                 Websites.query.order_by('name')]
    if request.method == 'POST':
        if form.validate_on_submit():
            if form.edited.data == "yes":
                zone = Zones.query.filter_by(id=zoneid).one()
                zone.websiteid=form.zone_website.data,
                zone.name=form.zone_name.data,
                zone.comments=form.zone_comments.data,
                zone.width=form.zone_width.data,
                zone.height=form.zone_height.data,
                zone.x0=form.zone_x0.data,
                zone.y0=form.zone_y0.data,
                zone.x1=form.zone_x1.data,
                zone.y1=form.zone_y1.data,
                zone.active=form.zone_active.data
                Zones.commit()
                msg = "Zone {} updated".format(form.zone_name.data)
                dblogger(
                    current_user.id,
                    msg
                )
                log.debug(msg)
                flash('Zone updated sucessfully.', 'success')
            else:
                Zones.create(
                    websiteid=form.zone_website.data,
                    name=form.zone_name.data,
                    comments=form.zone_comments.data,
                    width=form.zone_width.data,
                    height=form.zone_height.data,
                    x0=form.zone_x0.data,
                    y0=form.zone_y0.data,
                    x1=form.zone_x1.data,
                    y1=form.zone_y1.data,
                    active=form.zone_active.data
                )
                msg = "Zone {} added".format(form.zone_name.data)
                dblogger(
                    current_user.id,
                    msg
                )
                log.debug(msg)
                flash('Zone added sucessfully.', 'success')
            redirect(url_for('user.offer'))
        else:
            log.debug(form.errors)
    else:
        if zoneid is not None:
            zone = Zones.query.filter_by(id=zoneid).first()
            form.zone_website.data = zone.id
            form.zone_name.data = zone.name
            form.zone_comments.data = zone.comments
            form.zone_width.data = zone.width
            form.zone_height.data = zone.height
            form.zone_x0.data = zone.x0
            form.zone_y0.data = zone.y0
            form.zone_x1.data = zone.x1
            form.zone_y1.data = zone.y1
            form.zone_active.data = zone.active
    return render_template('users/add_zone.html',
                           form=form,
                           zoneid=zoneid,
                           all_zones=all_zones)


@roles_accepted('admin')
def edit_zone():
    """edit a zone."""
    form = AddZoneForm()


@blueprint.route('/add/website', methods=['GET', 'POST'])
@roles_accepted('admin')
def add_website():
    """Add a website."""
    all_websites = Websites.query.all()
    form = AddWebsiteForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            Websites.create(
                name=form.website_name.data,
                comments=form.website_comments.data,
                active=True,
            )
            dblogger(
                current_user.id,
                "Zone {} added".format(form.website_name.data)
            )
            flash('Website added sucessfully.', 'success')
            return redirect(url_for('user.offer'))
    return render_template('users/add_website.html',
                           form=form,
                           all_websites=all_websites)


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
    form = ChangeOffer()
    """Get and display all possible websites and zones in them."""
    all_zones = []
    websites = Websites.query.all()
    for website in websites:
        zones = Zones.query.filter_by(websiteid=website.id).all()
        for zone in zones:
            tmpdict = {}
            # First check if the zone has prices, if not, we are creating it with zero values
            howmany = Prices.query.filter_by(zoneid=zone.id).count()
            if howmany != 1:
                Prices.create(
                    zoneid=zone.id,
                    dayprice=0,
                    fiat="EUR"
                )
                Prices.commit()

            price = Prices.query.filter_by(
                        zoneid=zone.id
                    ).first()

            tmpdict['website'] = website.name
            tmpdict['id'] = zone.id
            tmpdict['name'] = zone.name
            tmpdict['price'] = price.dayprice
            tmpdict['x0'] = zone.x0
            tmpdict['x1'] = zone.x1
            tmpdict['y0'] = zone.y0
            tmpdict['y1'] = zone.y1

            # get stats and ignore if none
            try:
                ztatz = Impressions.query.filter_by(
                            zoneid=zone.id
                        ).first()
                tmpdict['impressions'] = ztatz.impressions
            except Exception as e:
                log.debug("Exception")
                log.exception(e)
                tmpdict['impressions'] = 0

            all_zones.append(tmpdict)

            # Prepare overview image
            create_banner_overview(
                zone.id
            )

    if request.method == 'POST':
        log.debug(pprint.pformat(request.form, depth=5))
        if form.validate_on_submit():
            Prices.query.filter_by(
                zoneid=form.zoneid.data).update(
                    {
                        "dayprice": form.zoneprice.data
                    }
                )
            Prices.commit()
        return redirect(url_for('user.offer'))

    # Render the page and quit
    return render_template(
        'users/offer.html',
        allzones=all_zones,
        websites=websites,
        form=form,
        isadmin=amiadmin()
    )


@blueprint.route('/campaign')
@blueprint.route('/campaign/duration/<int:no_weeks>')
@blueprint.route('/campaign/details/<int:campaign_id>')
@login_required
def campaign(no_weeks=None, campaign_id=None, invoice_uuid=None):
    """
    Details related to one campaign only.
    or
    Get and display all campaigns belonging to user.
    """
    # And now we are checking campaigns
    sql = Campaignes.query

    # We want details related to one campaign, not a list of all so we will
    # display that data and quit this function
    if campaign_id is not None:

        # we check details of the order which campaing belongs to
        campaign = sql.filter(Campaignes.id==campaign_id).join(Zones).join(Banner).add_columns(
            Banner.filename,
            Banner.height,
            Banner.width
            ).first_or_404()
        log.debug(f"CAMPAIGN: {campaign}")

        # we are getting overview of particular campaign from local database
        order = Orders.query.with_parent(campaign[0]).join(Payments).add_columns(
            Payments.received_at,
            Payments.confirmed_at,
            Payments.order_id,
            ).first_or_404()
        log.debug(f"ORDER: {order}")

        # we show details only to campaign owners or admins
        if order[0].user_id == current_user.id or amiadmin():
            # Render the page and quit
            return render_template(
                'users/campaign-single.html',
                now=datetime.utcnow(),
                datemin=datetime.min,
                campaign=campaign,
                order=order,
                url=images.url(campaign.filename)
            )
        else:
            # We politely redirecting 'hackers' to all campaigns
            return redirect(url_for("user.campaign"), code=302)

    else:
        if not no_weeks:  # we show 1 month of recent campaigns by default
            no_weeks = 4
        # admin gets all campaigns for all users limited to requested time period
        sql = sql.filter(Campaignes.stops_at > datetime.utcnow() - timedelta(weeks=no_weeks))
        if amiadmin():
            all_campaigns = sql.filter(Campaignes.o2c.any()).join(Zones).join(Banner).all()
        else:  # we want campaignes which belong to the logged in user only
            all_campaigns = sql.filter(Campaignes.o2c.any(user_id=current_user.id)).join(Zones).join(Banner).all()
        log.debug(all_campaigns)

        # Render the page and quit
        return render_template(
            'users/campaign.html',
            all_campaigns=all_campaigns,
            roles=current_user.roles,
            now=datetime.utcnow(),
            datemin=datetime.min,
            no_weeks=no_weeks
        )


@blueprint.route('/payments')
@blueprint.route('/payments/duration/<int:no_weeks>')
@blueprint.route('/payments/details/<int:payment_no>')
@blueprint.route('/payments/uuid/<string:invoice_uuid>')
@login_required
def payments(no_weeks=None, payment_no=None, invoice_uuid=None):
    """
    Details related to one payment only.
    or
    Get and display all payments belonging to user.
    """
    sql = Payments.query.join(Orders)
    if payment_no is not None or invoice_uuid is not None:

        # let's try to connect to the payment system which stores payment details
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
        if payment_no is not None:
            dbquery = sql.filter(Payments.id == payment_no).first_or_404()
        else:
            dbquery = sql.filter(Payments.btcpayserver_id == invoice_uuid).first_or_404()
        # and now we check details of that payment from downstream payment processor
        log.debug(dbquery)
        btcpayinv = btcpayclient.get_invoice(dbquery.btcpayserver_id)
        log.debug(pprint.pformat(btcpayinv, depth=5))
        cryptoInfo = btcpayinv['cryptoInfo']
        status = btcpayinv['status']

        # we need all campaignes which are related to that payment
        campaignes = Campaignes.query.filter(Campaignes.o2c.any(id=dbquery.order_id)).join(Zones).join(Banner).all()
        log.debug(f"CAMPAIGNES: {campaignes}")

        # we show details only to campaign owners or admins
        if dbquery.orders.user_id == current_user.id or amiadmin():
            # Render the page and quit
            return render_template(
                'users/payments-single.html',
                now=datetime.utcnow(),
                datemin=datetime.min,
                dbquery=dbquery,
                cryptoInfo=cryptoInfo,
                status=status,
                campaignes=campaignes
            )
        else:
            # We politely redirecting 'hackers' to all campaigns
            return redirect(url_for("user.payments"), code=302)

    else:
        if not no_weeks:  # we show 1 month of recent payments by default
            no_weeks = 4

        # admin gets all payments for all users limited to requested time period
        sql = sql.filter(Payments.created_at > datetime.utcnow() - timedelta(weeks=no_weeks))
        if amiadmin():
            all_payments = sql.all()
        else:
            all_payments = sql.filter(Orders.user_id == current_user.id).all()
        log.debug(all_payments)

        # Render the page and quit
        return render_template(
            'users/payments.html',
            all_payments=all_payments,
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

        # active zones where banner fits
        zones = Zones.query.join(Websites).join(Prices).add_columns(
            Websites.name, Prices.dayprice, Prices.fiat).filter(
            Zones.active==True).filter(
            Zones.width >= banner.width).filter(
            Zones.height >= banner.height).all()
        log.debug(zones)
        return render_template('users/order.html', banner=banner,
                               image_url=image_url,
                               all_zones=zones, step='chose-zone')

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

        # TODO just in case, we should be checking if unlikely we don't have a campaign with this name already
        randomname = names.get_full_name()
        #log.debug(randomname)
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

        try:
            begin = datetime.strptime(datestart, "%d/%m/%Y")
            enddate = datetime.strptime(datend, "%d/%m/%Y")
        except BaseException:
            return render_template('users/date-problems.html')
        totaltime = enddate - begin
        campaign = Campaignes.create(
            name=randomname,
            zoneid=zone_id,
            ctype=0,
            bannerid=banner_id,
            created_at=datetime.utcnow(),
            begins_at=begin,
            stops_at=enddate,
            impressions=0,
            comments="",
            active=True
        )
        log.debug(campaign)
        dblogger(
            current_user.id,
            ("NEW Campaign #{} with name {} in zone #{}, starting at {}, " +
                "ending at {}, with banner {} created.").format(
                campaign.id,
                randomname,
                zone_id,
                begin,
                enddate,
                banner_id
            )
        )


        basket = Basket.create(
            campaigno=campaign.id,
            user_id=current_user.id
        )
        log.debug(basket)

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
            order_sql = Campaignes.query.filter_by(
                id=item.campaigno).join(Banner).join(Zones).join(Prices).add_columns(
                    Banner.filename, Banner.url, Banner.width, Banner.height,
                    Banner.content, Banner.icon, Banner.type, Prices.dayprice,
                    Campaignes.begins_at, Campaignes.stops_at).first()
            basket.append(order_sql)
            begin = order_sql.begins_at
            enddate = order_sql.stops_at
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
        if campaign_id == 0:
            all_basket = Basket.query.filter_by(user_id=current_user.id).all()
            # Removing these campaigns from Revive as not useful in future
            Basket.query.filter_by(user_id=current_user.id).delete()
            for order in all_basket:
                Orders.query.filter_by(campaigno=order.campaigno).delete()
                flash('Your basket was removed sucessfully.', 'success')
        else:
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
@blueprint.route('/activation/campaign/<int:campaign_no>')
@login_required
def campaign_active(campaign_no):
    try:
        # getting data about this campaign 
        # and confirming it belongs to the user
        campaign = Campaignes.query.filter(Campaignes.id==campaign_no).first_or_404()
        order = Orders.query.with_parent(campaign).first_or_404()
        if order.user_id != current_user.id or not amiadmin():
            return redirect(url_for("user.campaign"), code=302)

        currently_active = campaign.active
        if currently_active is True:
            text = "disactivated"
        else:
            text = "activated"

        # activating / disactivating
        campaign.active = not campaign.active
        Campaignes.commit()
        dblogger(
            current_user.id,
            "Campaign #{} got {} by user.".format(
                campaign_no,
                text
            )
        )
        flash(f'Your campaign was {text} sucessfully.', 'success')

    except Exception as e:
        log.debug("Exception")
        log.exception(e)

    return redirect(url_for("user.campaign", campaign_id=campaign_no), code=302)


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
            sql = Campaignes.query.filter_by(
                id=item.campaigno).join(Zones).join(Prices).join(Banner).add_columns(
                    Banner.filename, Banner.url, Banner.width, Banner.height, Prices.dayprice).one()
            log.debug(sql)
            basket.append(sql)
            begin = sql[0].begins_at
            enddate = sql[0].stops_at
            totaltime = enddate - begin
            totalcurrencyprice = sql.dayprice/100*(totaltime.days+1)
            total += totalcurrencyprice
            label = label + "[C#{} Z#{} B#{} {} ↦ {} {:.2f}{}] ※ ".format(
                item.campaigno,
                sql[0].zoneid,
                sql[0].bannerid,
                begin.strftime("%d/%m/%y"),
                enddate.strftime("%d/%m/%y"),
                totalcurrencyprice,
                current_app.config.get('FIAT')
            )
    else:
        basket = 0
        log.error("Trying to pay for empty basket.")
        return redirect(url_for("user.basket"), code=302)

    log.debug(basket)

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

    # Creating an order and linking it to campaignes via an association table
    order = Orders.create(
        comments=label,
        user_id=current_user.id
    )
    log.debug(order)
    for item in basket_sql:
        sql = Campaignes.query.filter_by(id=item.campaigno).one()
        order.campaigne.append(sql)
    Orders.commit()
    dblogger(
        current_user.id,
        ("NEW Order #{} for campaigns in the basket created.").format(
            order.id,
        )
    )

    # Creating database record for payment and linking it into orders.
    payment_sql = Payments.create(
        order_id=order.id,
        created_at=datetime.utcnow(),
        btcpayserver_id=btcpayinv['id'],
        confirmed_at=datetime.min,
        received_at=datetime.min,
        fiat=btcpayinv['currency'],
        fiat_amount=btcpayinv['price'],
        posdata=randomid,
    )

    # It looks that payment page is ready to be shown, so we remove the content of users' basket
    Basket.query.filter_by(user_id=current_user.id).delete()
    Basket.commit()

    # redirect to payment page
    return redirect(btcpayinv['url'], code=302)


@blueprint.route('/admin/pair', methods=['GET', 'POST'])
@roles_accepted('admin')
def btcpaypair():
    """Payment processor pairing."""
    btcpayclient_location = current_app.config.get('APP_DIR')+'/data/btcpayserver.client'
    log.debug(btcpayclient_location)
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
