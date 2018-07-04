# -*- coding: utf-8 -*-
"""Various cron jobs."""

from datetime import datetime, timedelta
import xmlrpc.client

from flask import current_app

from beton.extensions import db
from beton.logger import log
from beton.utils import dblogger, reviveme

def remove_unpaid_campaigns(timeperiod=7):
    with db.app.app_context():
        try: 
            log.info("Running crontab.")
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

