# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""
from flask import current_app, flash


def flash_errors(form, category='warning'):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash('{0} - {1}'.format(getattr(form, field).label.text, error), category)

def reviveme(r):
    sessionid = r.ox.logon(current_app.config.get('REVIVE_MASTER_USER'),
                           current_app.config.get('REVIVE_MASTER_PASSWORD'))
    return sessionid
