"""Public section, including homepage and signup."""

# import logging

import requests
import uuid
import xmlrpc
from flask import Blueprint, flash, redirect, render_template, request, url_for, send_from_directory, current_app
from flask_login import current_user, login_required, logout_user

from beton.extensions import csrf_protect, login_manager
# from beton.user.forms import RegisterForm
from beton.user.models import Orders, Payments, User
# from beton.utils import flash_errors

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
    """Quasi-IPN service. Electrum sends us pings when something related to
    our payments changes. Here we are linking a campaign to a zone."""

    try:
        # Get the content of the IPN from Electrum
        ipn = request.get_json()
        print("IPN JSON: ", ipn)
        # This is not a valid payment yet
        if not ipn['status']:
            print("Electrum acknowledged subscription. Not paid yet.")
            return redirect(url_for('public.home'))

        # loading order datails from the database
        pay_db = Payments.query.filter_by(btcaddress=ipn['address']).first()
        print("Payments related to address: ", pay_db)

        if int(pay_db.txno) == 0:  # If our invoice is already paid, do not bother

            # Get TX hash from Electrum
            electrum_url = current_app.config.get('ELECTRUM_RPC')
            params = {
                "address": ipn['address']
            }
            payload = {
                "id": str(uuid.uuid4()),
                "method": "getaddresshistory",
                "params": params
            }
            print("We have sent to electrum this payload: ", payload)
            get_tx = requests.post(electrum_url, json=payload).json()
            print("We got back from electrum: ", get_tx)
            txno = get_tx['result'][0]['tx_hash']

            # loading all orders related to payment
            all_orders = Orders.query.filter_by(paymentno=pay_db.id).all()
            print("We are having these orders in the basket: ", all_orders)
            # Log in into Revive
            r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                          verbose=False)
            sessionid = r.ox.logon(current_app.config.get('REVIVE_MASTER_USER'),
                                   current_app.config.get('REVIVE_MASTER_PASSWORD'))
            for order in all_orders:
                # Linking the campaigna because it's paid!
                linkme = r.ox.linkCampaign(sessionid, order.zoneid, order.campaigno)
                print("Have we linked in Revive? ", linkme)
            # and finally mark payment as paid
            Payments.query.filter_by(btcaddress=ipn['address']).update({"txno":
                                                                        txno})
            Payments.commit()

            # Logout from Revive
            r.ox.logoff(sessionid)

            return "<html>ACK</html>"

    except:
        # Return a redirect to main page
        return redirect(url_for('public.home'))
