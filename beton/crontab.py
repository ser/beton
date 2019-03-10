# -*- coding: utf-8 -*-
"""Various cron jobs."""

import requests
import uuid
import xmlrpc.client

from datetime import datetime, timedelta
from dateutil.relativedelta import *

from flask import current_app

from beton.extensions import cache, db
from beton.logger import log
from beton.utils import dblogger, reviveme


# we cache login session to speed things up
@cache.memoize(timeout=120)
def sessionid(r):
    return reviveme(r)


# we cache it as we don't want to send emails more often than once an hour
@cache.memoize(timeout=60)
def sendwarning(blockchain):
    '''Notifying admins that Electrum is fcuked'''
    with db.app.app_context():
        from beton.user.models import Log, Role, User
        dbquery = Role.query.join(User).add_columns(
            User.id,
            User.username,
            User.email
        ).all()
        # log.debug(dbquery)
        for admin in dbquery:
            dblogger(admin.id, "Electrum {} is failing.".format(blockchain))


def update_impressions():
    '''This cron job gets stats from Revive and puts them into SQL database
    which is much faster to reach from Beton.'''
    with db.app.app_context():

        log.info("Running crontab: updating impressions.")
        r = xmlrpc.client.ServerProxy(
            current_app.config.get('REVIVE_XML_URI'),
            verbose=False
        )

        # Updating detailed impressions for user's campaigns
        try:
            from beton.user.models import Orders
            now = datetime.utcnow()
            # we update only currently ongoing campaigns
            ordersdata = Orders.query.filter(Orders.stops_at >= now).all()
            # for debug only:
            # ordersdata = Orders.query.all()
            for order in ordersdata:
                try:
                    ztatz = r.ox.campaignBannerStatistics(
                        sessionid(r),
                        order.campaigno,
                        datetime(2000, 1, 1, 0, 0),  # rather no chance for earlier
                        datetime.now()
                    )
                    # log.debug(ztatz)
                    value = ztatz[0]['impressions']
                    Orders.query.filter_by(
                        campaigno=order.campaigno).update(
                            {"impressions": value}
                    )
                except Exception as e:
                    # log.debug("Exception in {}".format(order.campaigno))
                    # log.exception(e)
                    #
                    # we ignore errors as they probably mean that there's no
                    # relevant data in Revive
                    pass
            Orders.commit()

        except Exception as e:
            log.debug("Exception")
            log.exception(e)

        # Get stats related to all zones aggregated across all customers
        try:
            from beton.user.models import Impressions
            now = datetime.utcnow()
            ztatz = r.ox.agencyZoneStatistics(
                sessionid(r),
                1,
                datetime.now() - relativedelta(months=1),
                datetime.now()
            )
            # try to update the table if not available, create it
            log.debug(ztatz)
            for zone in ztatz:
                howmany = Impressions.query.filter_by(
                    zoneid = zone['zoneId']
                ).count()
                if howmany is not 1:
                    Impressions.create(
                        zoneid = zone['zoneId'],
                        impressions = zone['impressions'],
                        clicks = zone['clicks']
                    )
                else:
                    Impressions.query.filter_by(
                        zoneid = zone['zoneId']
                    ).update(
                        {
                            "impressions": zone['impressions'],
                            "clicks": zone['clicks']
                        }
                    )
            Impressions.commit()

        except Exception as e:
            log.debug("Exception")
            log.exception(e)


def remove_unpaid_campaigns(timeperiod=7):
    with db.app.app_context():
        try: 
            log.info("Running crontab: removing unpaid campaigns.")
            from beton.user.models import Orders, Payments
            r = xmlrpc.client.ServerProxy(
                current_app.config.get('REVIVE_XML_URI'),
                verbose=False
            )
            all_payments = Payments.query.all()
            for payment in all_payments:
                if payment.txno == str(0):
                    if payment.created_at < datetime.now()-timedelta(days=timeperiod):
                        log.debug("Removing payment %d" % payment.id )
                        dblogger(
                            payment.user_id,
                            'Removed unpaid {chain} payment to address {adr} for {coin}.'.format(
                                chain=payment.blockchain,
                                adr=payment.address,
                                coin=payment.total_coins
                            )
                        )
                        all_campaigns = Orders.query.filter_by(paymentno=payment.id)
                        for campaign in all_campaigns:
                            try:
                                removed = r.ox.deleteCampaign(
                                    sessionid(r),
                                    campaign.campaigno
                                )
                                log.debug(
                                    "Campaign #%d removed from Revive?: %s" % (
                                        campaign.campaigno,
                                        str(removed)
                                    )
                                )
                            except:
                                log.info(
                                    "WARNING! Campaign %s was not removed from Revive - it has not existed over there. It may be an error." % (
                                        campaign.campaigno
                                    )
                                )
                            Orders.query.filter_by(campaigno=campaign.campaigno).delete()
                            dblogger(
                                campaign.user_id,
                                ("Removed campaign #%d for zone %d with banner %d, " +
                                 "created at %s, starting from %s and ending at %s.") % (
                                    campaign.campaigno,
                                    campaign.zoneid,
                                    campaign.bannerid,
                                    str(campaign.created_at),
                                    str(campaign.begins_at),
                                    str(campaign.stops_at)
                                )
                            )
                        Payments.query.filter_by(id=payment.id).delete()
            Payments.commit()
            Orders.commit()

        except Exception as e:
            log.debug("Exception")
            log.exception(e)


def ping_electrum():
    '''Checking Electrum servers health'''
    with db.app.app_context():
        try:
            log.info("Electrum health check.")
            payment_systems = current_app.config.get('PAYMENT_SYSTEMS')
            for payment_system in payment_systems:
                log.debug(payment_system)
                # We check only enabled payments
                if payment_systems[payment_system][5]:
                    payload = {
                        "id": str(uuid.uuid4()),
                        "method": "is_synchronized"
                    }
                    electrum_url = payment_systems[payment_system][3]
                    log.debug("We have sent to electrum this payload:")
                    log.debug(payload)
                    get_health = requests.post(electrum_url, json=payload).json()
                    log.debug("We got back from electrum:")
                    log.debug(get_health)
                    if not get_health['result']:
                        sendwarning(payment_system)
                else:
                    log.debug("Payment system disabled.")

        except Exception as e:
            log.debug("Exception")
            log.exception(e)
