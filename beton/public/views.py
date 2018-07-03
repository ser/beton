"""Public section, including homepage and signup."""

import requests
import uuid
import xmlrpc

from flask import Blueprint, flash, redirect, render_template, request, url_for, send_from_directory, current_app
from flask_security import current_user, login_required, logout_user

from beton.logger import log
from beton.extensions import csrf_protect
from beton.user.models import Orders, Payments, User, db

blueprint = Blueprint('public', __name__, static_folder='../static')


# @login_manager.user_loader
# def load_user(user_id):
#    """Load user by ID."""
#    return User.get_by_id(int(user_id))


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
@blueprint.route('/ipn/<string:payment>', methods=['POST'])
def ipn(payment):
    """IPN service. Electrum sends us pings when something related to
    our payments changes. Here we are linking a campaign to a zone.
    
    We do not need to protest this route as each received IPN we confirm
    directly in our electrum wallet, so it cannot get spoofed.
    """

    payment_system = current_app.config.get('PAYMENT_SYSTEMS')[payment]
    try:
        # Get the content of the IPN from Electrum
        ipn = request.get_json()
        log.debug("IPN JSON from Electrum received:")
        log.debug(ipn)
        # This is not a valid payment yet
        if not ipn['status']:
            log.debug("Electrum acknowledgement only. PR is not paid yet or is expired.")
            return redirect(url_for('public.home'))

        # loading order datails from the database
        pay_db = Payments.query.filter_by(address=ipn['address']).first()
        log.debug("Payments related to address:")
        log.debug(pay_db)

        # Verify if payment is in expected coins
        if str(pay_db.blockchain) != str(payment):
            log.debug("We expected payment in %s, it came in %s" %
                      (pay_db.blockchain, payment))
            return redirect(url_for('public.home'))

        try:
            if int(pay_db.txno) == 0:  # If our invoice is already paid, do not bother

                # Get balance on payment address from Electrum
                electrum_url = payment_system[3]
                params = {
                    "address": ipn['address']
                }
                payload = {
                    "id": str(uuid.uuid4()),
                    "method": "getaddressbalance",
                    "params": params
                }
                log.debug("We have sent to electrum this payload:")
                log.debug(payload)
                get_balance = requests.post(electrum_url, json=payload).json()
                log.debug("We got back from electrum:")
                log.debug(get_balance)

                # Electrum reports current state of transaction on this address
                confirmed = float(get_balance['result']['confirmed'])
                unconfirmed = float(get_balance['result']['unconfirmed'])

                if unconfirmed > 0:
                    # Transcation is not confirmed yet so we simply register that
                    # and wait for another ping from Electrum
                    log.debug("Balance of %s is not confirmed yet." %
                            str(unconfirmed))
                    return redirect(url_for('public.home'))

                # No we check if received amount is equal or larger than expected 
                weexpect = pay_db.total_coins
                if confirmed >= weexpect:
                    # It is paid :-) so we activate banner(s)
                    log.debug("PAID! Confirmed balance on address is %s and we expected %s." %
                            (str(confirmed), str(weexpect)))

                    # Get TX hash from Electrum
                    # params are the same so we do not declare them again
                    payload = {
                        "id": str(uuid.uuid4()),
                        "method": "getaddresshistory",
                        "params": params
                    }
                    log.debug("We have sent to electrum this payload:")
                    log.debug(payload)
                    get_tx = requests.post(electrum_url, json=payload).json()
                    log.debug("We got back from electrum:")
                    log.debug(get_tx)
                    txno = get_tx['result'][0]['tx_hash']  # we analyze only first transaction
                    # TODO: maybe in future it's worth to record fee as well?

                    # loading all orders related to payment
                    all_orders = Orders.query.filter_by(paymentno=pay_db.id).all()
                    log.debug("We are having these orders in the basket:")
                    log.debug(all_orders)
                    # Log in into Revive
                    r = xmlrpc.client.ServerProxy(current_app.config.get('REVIVE_XML_URI'),
                                                verbose=False)
                    sessionid = r.ox.logon(current_app.config.get('REVIVE_MASTER_USER'),
                                        current_app.config.get('REVIVE_MASTER_PASSWORD'))
                    for order in all_orders:
                        # Linking the campaigna because it's paid!
                        linkme = r.ox.linkCampaign(sessionid, order.zoneid, order.campaigno)
                        log.debug("Have we linked in Revive?")
                        log.debug(linkme)
                    # and finally mark payment as paid
                    Payments.query.filter_by(address=ipn['address']).update({"txno":
                                                                            txno})
                    Payments.commit()

                    # Logout from Revive and presenting an ACKNOWLEDGEMENT
                    r.ox.logoff(sessionid)

                else:
                    log.debug("Confirmed balance on address is %s but we expected %s." %
                            (str(confirmed), str(weexpect)))

        except Exception as e:
            log.debug("Transaction %s is already paid." % pay_db.txno)
            return redirect(url_for('public.home'))

    except Exception as e:
        log.debug("Exception")
        log.exception(e)
        return redirect(url_for('public.home'))

    # Return a redirect to main page
    return redirect(url_for('public.home'))
