# -*- coding: utf-8 -*-
"""Various cron jobs."""

import xmlrpc.client

from datetime import datetime, timedelta
from dateutil.relativedelta import *

from flask import current_app
from flask.helpers import get_debug_flag

from beton.extensions import cache, kvstore, scheduler
from beton.logger import log
from beton.utils import dblogger, reviveme


# Helper functions 
#
# we cache login session to speed tasks access up
@cache.memoize(timeout=120)
def sessionid(r):
    return reviveme(r)

# ##########
# Main tasks
# 


# TODO
# We want to keep a persistant connection to Revive
# and we are constantly keeping it up. it should minimally speed up connection
# of clients when the session to Revive is disconnected.
#
# @scheduler.task('interval', id='revive_persist', seconds=111)
# def revive_persist():
#    with scheduler.app.app_context():
#        # we cache login session to speed customer access up
#        r = xmlrpc.client.ServerProxy(
#            current_app.config.get('REVIVE_XML_URI'),
#            verbose=False
#        )
#        reviveme(r)
#        log.info("Running crontab: revive keepup")


# Cleaning expired sessions in ./data
# In production we do it every 6 hours, but in debug mode every minute.
frequency = 1 if get_debug_flag() else 360
@scheduler.task('interval', id='cleanup_sessions', minutes=frequency)
def cleanup_sessions():
    with scheduler.app.app_context():
        try:
            kvstore.cleanup_sessions()
            log.info("Running crontab: cleaned up sessions.")
        except Exception as e:
            log.debug("Exception")
            log.exception(e)

# Updating detailed impressions for user's campaigns
# We do not need to do that more often than each hour
# as Revive itself does it hourly
@scheduler.task('interval', id='update_impressions', hours=1)
def update_impressions():
    '''This cron job gets stats from Revive and puts them into SQL database
    which is much faster to reach from Beton.'''
    with scheduler.app.app_context():

        log.info("Running crontab: updating impressions.")
        r = xmlrpc.client.ServerProxy(
            current_app.config.get('REVIVE_XML_URI'),
            verbose=False
        )
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
            if ztatz:
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


# Removal of unpaid campaigns after a week - we really do not need them
@scheduler.task('interval', id='remove_unpaid_campaigns', hours=24)
def remove_unpaid_campaigns(timeperiod=7):
    with scheduler.app.app_context():
        try: 
            log.info("Running crontab: removing unpaid campaigns.")
            from beton.user.models import Orders, Payments
            r = xmlrpc.client.ServerProxy(
                current_app.config.get('REVIVE_XML_URI'),
                verbose=False
            )
            all_payments = Payments.query.all()
            for payment in all_payments:
                if payment.received_at == datetime.min:
                    if payment.created_at < datetime.now()-timedelta(days=timeperiod):
                        log.debug("Removing payment %d" % payment.id )
                        dblogger(
                            payment.user_id,
                            'CRON: Removed unpaid payment ID {btcpayid}.'.format(
                                btcpayid=payment.btcpayserver_id
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
