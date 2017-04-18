# -*- coding: utf-8 -*-
"""User views."""
import logging
import xmlrpc.client

from logging.handlers import RotatingFileHandler

from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user

blueprint = Blueprint('user', __name__, url_prefix='/me', static_folder='../static')


@blueprint.route('/')
@login_required
def me():
    """Check if currently logged in user exists in Revive and if not, create
    it. Later display a current information from Revive."""
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
        logging.warning(current_user.username)
        r.ox.addAdvertiser(sessionid, { 'agencyId': current_app.config.get('REVIVE_AGENCY_ID'),
                                       'advertiserName': current_user.username,
                                       'emailAddress': current_user.email,
#                                       'contactName': current_user.first_name+" "+current_user.lastname, # TODO: check if values are set 
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
    zonestats = r.ox.advertiserZoneStatistics(sessionid, advertiser_id) # TODO

    # Logout from Revive
    r.ox.logoff(sessionid)

    # Render the page and quit
    return render_template('users/members.html', zonestats=zonestats)
