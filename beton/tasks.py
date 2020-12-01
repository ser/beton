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
