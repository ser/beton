# -*- coding: utf-8 -*-
"""User views."""
import datetime
import logging
import xmlrpc.client

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from PIL import Image

from beton.extensions import images
from beton.user.forms import AddBannerForm
from beton.user.models import Banner
from beton.utils import flash_errors

blueprint = Blueprint('user', __name__, url_prefix='/me', static_folder='../static')


@blueprint.route('/')
@login_required
def me():
    """Check if currently logged in user exists in Revive and if not, create it.

    Later display a current information from Revive.
    """
    r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'), verbose=False)
    sessionid = r.ox.logon(current_app.config.get('REVIVE_MASTER_USER'),
                           current_app.config.get('REVIVE_MASTER_PASSWORD'))
    all_advertisers = r.ox.getAdvertiserListByAgencyId(sessionid,
                                                       current_app.config.get('REVIVE_AGENCY_ID'))
    # Try to find out if the customer is already registered in Revive, if not,
    # register him
    try:
        next(x for x in all_advertisers if x['advertiserName'] ==
             current_user.username)
    except StopIteration:
        logging.warning('Created user: ', current_user.username)
        r.ox.addAdvertiser(sessionid, {'agencyId': current_app.config.get('REVIVE_AGENCY_ID'),
                                       'advertiserName': current_user.username,
                                       'emailAddress': current_user.email,
                                       # 'contactName': current_user.first_name+"
                                       # "+current_user.lastname, # TODO: check if values are set
                                       'contactName': current_user.username,
                                       'comments': 'beton'
                                       })
    # We are now sure that we have a user in Revive, so now get his ID over there
    all_advertisers = r.ox.getAdvertiserListByAgencyId(sessionid,
                                                       current_app.config.get('REVIVE_AGENCY_ID'))
    advertiser_id = int(next(x for x in all_advertisers if x['advertiserName'] ==
                        current_user.username)['advertiserId'])

    # TODO: update email address of the user in Revice to the current flask database

    # Get all possible current data related to the user from Revive
    zonestats = r.ox.advertiserZoneStatistics(sessionid, advertiser_id)  # TODO
    campstats = r.ox.advertiserCampaignStatistics(sessionid, advertiser_id)  # TODO

    # Logout from Revive
    r.ox.logoff(sessionid)

    # Render the page and quit
    return render_template('users/members.html',
                           zonestats=zonestats,
                           campstats=campstats)


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
                          url=form.banner_url.data, created_at=datetime.datetime.utcnow(),
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


@blueprint.route('/offer')
@login_required
def offer():
    """Get and display all possible websites and zones in them."""
    r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                  verbose=False)
    sessionid = r.ox.logon(current_app.config.get('REVIVE_MASTER_USER'),
                           current_app.config.get('REVIVE_MASTER_PASSWORD'))

    # get zones from Revive
    allzones = r.ox.getZoneListByPublisherId(sessionid,
                                             current_app.config.get('REVIVE_AGENCY_ID'))

    # Logout from Revive
    r.ox.logoff(sessionid)

    # Render the page and quit
    return render_template('users/offer.html', allzones=allzones)


@blueprint.route('/campaign')
@login_required
def campaign():
    """Get and display all camapigns belonging to user."""
    r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                  verbose=False)
    sessionid = r.ox.logon(current_app.config.get('REVIVE_MASTER_USER'),
                           current_app.config.get('REVIVE_MASTER_PASSWORD'))

    all_advertisers = r.ox.getAdvertiserListByAgencyId(sessionid,
                                                       current_app.config.get('REVIVE_AGENCY_ID'))
    advertiser_id = int(next(x for x in all_advertisers if x['advertiserName'] ==
                        current_user.username)['advertiserId'])

    all_campaigns = r.ox.getCampaignListByAdvertiserId(sessionid, advertiser_id)

    # find all banners related to campaigns
    banners = []
    if len(all_campaigns) > 0:
        for x in all_campaigns:
            banners.append([x['campaignId'], r.ox.getBannerListByCampaignId(sessionid, x['campaignId'])])

    # Logout from Revive
    r.ox.logoff(sessionid)

    # Render the page and quit
    return render_template('users/campaign.html',
                           all_campaigns=all_campaigns,
                           banners=banners)
