# -*- coding: utf-8 -*-
"""Various cron jobs."""

from datetime import datetime, timedelta
from dateutil.relativedelta import *

from flask import current_app
from flask.helpers import get_debug_flag

from beton.extensions import cache, kvstore, scheduler
from beton.logger import log
from beton.user.models import Banner, Campaignes, Orders, Zones
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


frequency = 1 if get_debug_flag() else 360


@scheduler.task('interval', id='writing nginx conf', minutes=frequency)
def nginx():
    with scheduler.app.app_context():
        # we are checking all active campaignes and creating appropriate nginx
        # config
        all_campaigns = Campaignes.query.filter(Campaignes.o2c.any()).join(Zones).join(Banner).order_by(Campaignes.id).all()
        log.debug(f"ALL CAMPAIGNES: {all_campaigns}")


