# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located in app.py."""

import os.path

from simplekv.fs import FilesystemStore

from flask_apscheduler import APScheduler
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_debugtoolbar import DebugToolbarExtension
from flask_kvsession import KVSessionExtension
from flask_mail import Mail
from flask_migrate import Migrate
from flask_moment import Moment
from flask_wtf.csrf import CSRFProtect
from flask_security import Security, SQLAlchemyUserDatastore
from flask_sqlalchemy import SQLAlchemy

app_dir = os.path.abspath(os.path.dirname(__file__))

bcrypt = Bcrypt()
cache = Cache()
csrf_protect = CSRFProtect()
db = SQLAlchemy()
debug_toolbar = DebugToolbarExtension()
mail = Mail()
migrate = Migrate()
moment = Moment()
scheduler = APScheduler()
sesstore = FilesystemStore(app_dir + '/data')
kvstore = KVSessionExtension(sesstore)

# Security
from beton.user.models import User, Role
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security()
