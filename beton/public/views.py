"""Public section, including homepage and signup."""

import pprint
import pushover
import requests
import uuid

from datetime import datetime
from oslo_concurrency import lockutils

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_api import status
from flask_mail import Message
from flask_security import current_user, login_required, logout_user

from beton.logger import log
from beton.extensions import csrf_protect, mail
from beton.user.models import Campaignes, Orders, Payments, User, db
from beton.utils import dblogger

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
@blueprint.route('/ipn', methods=['POST'])
def ipn():
    """IPN service. BTCpayserver sends us pings when situation related to
    our payments changes. Here we are linking a campaign to a zone.
    We do not need to protect this route as each received IPN we confirm
    directly at payment processor, so it cannot get spoofed.
    """
    # FUNCTIONS
    def checkpaydb(posdata):
        pay_db = Payments.query.filter_by(posdata=posdata).join(Orders).first()
        if pay_db is None:
            log.info("There is no payment related to IPN. Aborting")
            return "NAY", status.HTTP_412_PRECONDITION_FAILED
        else:
            return pay_db

    def invoice_paidInFull(pay_db, ipn):
        # Logging to admin log
        dblogger(
            pay_db.orders.user_id,
            "RECEIVED {} for invoice {}! We are waiting now for one confirmation.".format(
                ipn['data']['btcPaid'],
                ipn['data']['id']
            )
        )
        # We record receiving payment in the Payment database
        Payments.query.filter_by(
            posdata=ipn['data']['posData']).update(
                {"received_at": datetime.utcnow()})
        Payments.commit()

    def invoice_confirmed(pay_db, ipn):
        # Logging to admin log
        dblogger(
            pay_db.orders.user_id,
            "CONFIRMED {} for invoice {}. We are boooking advert(s).".format(
                ipn['data']['btcPaid'],
                ipn['data']['id']
            )
        )

        # We record receiving payment in the Payment database
        Payments.query.filter_by(
            posdata=ipn['data']['posData']).update(
                {"confirmed_at": datetime.utcnow()})
        Payments.commit()
        # We are activating campaign and recording payment
        sql = Campaignes.query.join((Orders.campaigne)).join(Payments).filter(
            Payments.posdata==ipn['data']['posData']).all()
        log.debug(f"Payments sql: {sql}")
        for campaign in sql:
            Campaignes.query.filter_by(
                id=campaign.id).update(
                       {"active": True})
        Campaignes.commit()

        # If configuration sets pushover.net, we send it in there
        if current_app.config.get('PUSHOVER') is True:
            pushlog = (
                    "{} paid {} {} for {}".format(
                        pay_db.user_id,
                        pay_db.fiat_amount,
                        pay_db.fiat,
                        pay_db.btcpayserver_id
                    )
            )
            pushover.Client().send_message(pushlog, title="$$$")

    # TODO
    def invoice_expiredPaidPartial(pay_db, ip):
        pass

    # MAIN PART
    # We expect JSON, if it is not JSON, return http error 405
    try:
        ipn = request.get_json()
        log.debug("IPN JSON from payment processor received:")
        log.debug(pprint.pformat(ipn, depth=5))
    except Exception as e:
        log.debug("Exception as we did not get JSON request:")
        log.exception(e)
        return "NAY", status.HTTP_405_METHOD_NOT_ALLOWED

    # There are two sorts of IPNs, full and extended ones.
    # Extended has one level of JSON, full two of them.
    # If we can't do that, something is screwed so we send http error 501
    if 'posData' in ipn:
        ipnsort = 'extended'
        posdata = ipn['posData']
    elif 'data' in ipn:
        ipnsort = 'full'
        if 'posData' in ipn['data']:
            posdata = ipn['data']['posData']
    else:
        return "NAY", status.HTTP_501_NOT_IMPLEMENTED

    # Wedo not want to process the same transaction concurrently, so we lock it
    lockutils.set_defaults(current_app.config.get('CACHE_DIR'))
    with lockutils.lock(posdata):
        log.debug("We received "+ipnsort+" IPN.")
        if ipnsort == 'full':
            # We are interested in full IPNs, with codes 1003 and 1005 specifically:
            # 1003 invoice_paidInFull
            # 1005 invoice_confirmed
            # 2000 invoice_expiredPaidPartial
            #
            # loading order datails from the database
            pay_db = checkpaydb(posdata)
            if ipn['event']['code'] == 1003:
                # We received invoice_paidInFull
                invoice_paidInFull(pay_db, ipn)
            elif ipn['event']['code'] == 1005:
                # We received invoice_confirmed
                invoice_confirmed(pay_db, ipn)
            else: pass
        return "YAY", status.HTTP_200_OK

