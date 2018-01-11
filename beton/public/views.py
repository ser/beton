# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
import logging
import requests
import uuid
import xmlrpc
from flask import Blueprint, flash, redirect, render_template, request, url_for, send_from_directory, current_app
from flask_login import current_user, login_required, login_user, logout_user

from beton.extensions import csrf_protect, login_manager
from beton.user.forms import RegisterForm
from beton.user.models import Orders, User
from beton.utils import flash_errors

blueprint = Blueprint('public', __name__, static_folder='../static')


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.get_by_id(int(user_id))


@blueprint.route('/', methods=['GET'])
def home():
    """Home page."""
    # redirect to personalised version for logged in users
    if current_user.is_authenticated:
        return redirect(url_for('user.user_me'))
    return render_template('public/home.html')


@blueprint.route('/logout/')
@login_required
def logout():
    """Logout."""
    logout_user()
    flash('You are logged out.', 'info')
    return redirect(url_for('public.home'))


@blueprint.route('/about/')
def about():
    """About page."""
    return render_template('public/about.html')


# TODO: this should be served directly via nginx in production
@blueprint.route('/banners/<path:filename>')
def download_file(filename):
    return send_from_directory(current_app.config.get('UPLOADED_IMAGES_DEST'), filename)


@csrf_protect.exempt
@blueprint.route('/ipn', methods=['POST'])
def ipn():
    """Quasi-IPN service. Electrum sends us pings when something related to oe
    og pur payments changes. We have an opportunity to register it and for
    example link a campaign to a zone."""
    electrum_url = current_app.config.get('ELECTRUM_RPC')

    # Log in into Revive
    r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                  verbose=False)
    sessionid = r.ox.logon(current_app.config.get('REVIVE_MASTER_USER'),
                           current_app.config.get('REVIVE_MASTER_PASSWORD'))


    # Get the content of the IPN from Electrum
    json = request.get_json()

    # loading order datails from the database
    ipndb = Orders.query.filter_by(btcaddress=json['address']).first()
    previous_status = ipndb.ispaid

    f = open("/tmp/a", 'a')
    f.write(str(json))
    f.write(str(ipndb))

    if previous_status != True: # If our invoice is already paid, do not bother

        # Let us usk Electrum back about the address
        headers = {'content-type': 'application/json'}
        params = {
            "key": json['address']
        }
        payload = {
            "id": str(uuid.uuid4()),
            "method": "getrequest",
            "params": params
        }
        e_please = requests.post(electrum_url, json=payload, headers=headers).json()
        e_results = e_please['result']
        current_status = e_results['status']
        f.write(str(e_results))

        if current_status == 'Paid':
            # Linking the campaigna because it's paid!
            linkme = r.ox.linkCampaign(sessionid, ipndb.zoneid, ipndb.campaigno)
            # Next two lines smell, TODO: make it properly
            Orders.query.filter_by(btcaddress=json['address']).update({"ispaid":
                                                                       True})
            Orders.commit()

    # Logout from Revive
    r.ox.logoff(sessionid)

    # Return a redirect to main page
    return redirect(url_for('public.home'))
