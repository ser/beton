# -*- coding: utf-8 -*-
"""Various cron jobs."""

from datetime import datetime, timedelta
import xmlrpc.client

from flask import current_app

from beton.extensions import cache, db
from beton.logger import log
from beton.utils import dblogger, reviveme


def update_impressions():
    with db.app.app_context():

        # we cache login session to speed things up
        @cache.memoize(timeout=120)
        def sessionid(r):
            return reviveme(r)

        try:
            log.info("Running crontab: updating impressions.")
            from beton.user.models import Orders
            r = xmlrpc.client.ServerProxy(
                current_app.config.get('REVIVE_XML_URI'),
                verbose=False
            )
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
                    Orders.commit()
                except Exception as e:
                    # log.debug("Exception in {}".format(order.campaigno))
                    # log.exception(e)
                    #
                    # we ignore errors as they probably mean that there's no
                    # relevant data in Revive
                    pass

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
                            removed = r.ox.deleteCampaign(
                                reviveme(r),
                                campaign.campaigno
                            )
                            Orders.query.filter_by(campaigno=campaign.campaigno).delete()
                            log.debug(
                                "Campaign #%d removed from Revive?: %s" % (
                                    campaign.campaigno,
                                    str(removed)
                                )
                            )
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

