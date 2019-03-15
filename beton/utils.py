# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""

from datetime import datetime

from flask import current_app, flash

from beton.logger import log
from beton.user.models import Log


def flash_errors(form, category='warning'):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash('{0} - {1}'.format(getattr(form, field).label.text, error), category)

def reviveme(r):
    sessionid = r.ox.logon(current_app.config.get('REVIVE_MASTER_USER'),
                           current_app.config.get('REVIVE_MASTER_PASSWORD'))
    return sessionid

def dblogger(userid, logdata):
    """Logging main events to database."""
    try:
        Log.create(
            user_id=userid,
            datelog=datetime.utcnow(),
            logdata=logdata
        )
    except Exception as e:
        log.exception(e)
