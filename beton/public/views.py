"""Public section, including homepage and signup."""

import requests
import uuid
import xmlrpc

from flask import Blueprint, flash, redirect, render_template, request, url_for, send_from_directory, current_app
from flask_mail import Message
from flask_security import current_user, login_required, logout_user

from beton.logger import log
from beton.extensions import csrf_protect, mail
from beton.user.models import Orders, Payments, User, db
from beton.utils import dblogger, reviveme

blueprint = Blueprint('public', __name__, static_folder='../static')


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

        if pay_db == None:
            log.info("There is no payment related to address %s - aborting." %
                      ipn['address'])
            return redirect(url_for('public.home'))

        # Verify if payment is in expected coins
        if str(pay_db.blockchain) != str(payment):
            log.info("We expected payment in %s, it came in %s" %
                      (pay_db.blockchain, payment))
            return redirect(url_for('public.home'))

        try:
            if pay_db.txno == "0":  # If our invoice is already paid, do not bother

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
                    log.debug("Balance of {} is not confirmed yet.".format(
                        unconfirmed
                    ))
                    dblogger(
                        pay_db.user_id,
                        "{} {} RECEIVED! We are waiting now for one confirmation.".format(
                            unconfirmed,
                            payment
                        )
                    )
                    return redirect(url_for('public.home'))

                # No we check if received amount is equal or larger than expected 
                weexpect = float(pay_db.total_coins)
                if confirmed >= weexpect:
                    # It is paid :-) so we activate banner(s)
                    logstr = ('IPN PAID! Confirmed balance of {} on address {} is ' +
                        '{} and we expected {}').format(
                            payment,
                            ipn['address'],
                            confirmed,
                            weexpect
                        )
                    log.debug(logstr)
                    dblogger(pay_db.user_id, logstr)

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
                    r = xmlrpc.client.ServerProxy(
                        current_app.config.get('REVIVE_XML_URI'),
                        verbose=False
                    )
                    sessionid = reviveme(r)
                    for order in all_orders:
                        # Linking the campaigna because it's paid!
                        linkme = r.ox.linkCampaign(sessionid, order.zoneid, order.campaigno)
                        log.debug("Have we linked in Revive? %s" % str(linkme))
                    # and finally mark payment as paid
                    Payments.query.filter_by(address=ipn['address']).update({"txno":
                                                                            txno})
                    Payments.commit()

                    # Logout from Revive
                    r.ox.logoff(sessionid)

                    # Getting detailed data of the customer
                    userdb = User.query.filter_by(id=pay_db.user_id).first()

                    # Mailing customer that order is paid
                    msg = Message("Payment for your campaign(s) is confirmed")
                    msg.recipients = [(userdb.email)]
                    
                    msgbody = ("Funds in {} sent to address {} are confirmed. \n\n" +
                               "Your campaign(s) are ready to be run. \n\n" +
                               "You can see all details on: \n    {}").format(
                                    payment_system[0],
                                    ipn['address'],
                                    current_app.config.get('OUR_URL')+"campaign"
                    )
                    msg.body = msgbody
                    mail.send(msg)

                else:
                    logstr = ("PROBLEM. Confirmed balance on address is " +
                              "{} but we expected {}.").format(
                                confirmed,
                                weexpect
                            )
                    log.debug(logstr)
                    dblogger(
                        pay_db.user_id,
                        logstr
                    )
            else:
                log.debug("Transaction {} is already paid.".format(pay_db.txno))

        except Exception as e:
            log.debug("Exception")
            log.exception(e)
            return redirect(url_for('public.home'))

    except Exception as e:
        log.debug("Exception")
        log.exception(e)
        return redirect(url_for('public.home'))

    # Return a redirect to main page
    return redirect(url_for('public.home'))
