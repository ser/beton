# -*- coding: utf-8 -*-
"""Various cron jobs."""

from datetime import datetime, timedelta
from dateutil.relativedelta import *

from flask import current_app
from flask.helpers import get_debug_flag

from jinja2 import Template

from beton.extensions import cache, kvstore, scheduler
from beton.logger import log
from beton.threads import Helper
from beton.user.models import Banner, Campaignes, Orders, Websites, Zones
from beton.utils import dblogger


# ################
# Helper functions

# ################
# Main tasks

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


# In production we do it every 1 hour, but in debug mode every minute.
frequency = 1 if get_debug_flag() else 60


@scheduler.task('interval', id='nginx_conf', minutes=frequency)
def nginx_conf():

    helper = Helper()
    outfile = ""
    nginxconf = '/tmp/beton.conf'
    #nginxconf = '/beton/nginx/beton.conf'
    # jinja template for a single campaign entrance in nginx config
    j2temp = """
location = {{ fname_uri }} {
   alias {{ nginx_banner_dir }} {{ banner_fname }};
   access_log syslog:server=10.77.1.27:13131,facility=news,tag=kfasik,severity=info combined if=$log_ip;
   # if you use pagespeeda, you should disallow any modifications
   pagespeed Disallow {{ fname_uri }};
}  """
    template = Template(j2temp)

    with scheduler.app.app_context():
        # we are checking all active campaignes and creating appropriate nginx
        # config
        #sql = Campaignes.query.join((Orders.campaigne)).filter(Campaignes.o2c.any()).filter(Campaignes.active==True).join(Zones).join(Banner).join(Websites).order_by(Campaignes.id)
        #sql = Campaignes.query.join((Orders.campaigne)).filter(Campaignes.active==True).join(Zones).join(Banner).join(Websites).join(Payments).order_by(Campaignes.id)
        sql = Campaignes.query.join((Orders.campaigne)).filter(Campaignes.active==True).join(Payments).join(Zones).join(Banner).join(Websites).join(Impressions).order_by(Campaignes.id)
        #all_campaigns = sql.with_entities(Campaignes, Payments, Orders, Banner, Zones, Websites).all()
        all_campaigns = sql.with_entities(Campaignes, Payments, Orders, Zones, Banner, Websites, Impressions).all()
        log.debug(f"ALL CAMPAIGNES: {all_campaigns}")
        for campaign in all_campaigns:
            # We want actually running campaignes only
            log.debug(f"CAMPAIGN: {campaign}")
            is_running = campaign[0].begins_at < datetime.utcnow() and campaign[0].stops_at > datetime.utcnow()
            log.debug(f"IS RUNNING?: {is_running}")
            if is_running is True:
                is_paid = campaign[1].confirmed_at > datetime.min
                log.debug(f"PAID: {is_paid}")
