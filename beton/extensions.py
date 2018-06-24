# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located in app.py."""
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_debugtoolbar import DebugToolbarExtension
from flask_mail import Mail
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
# from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required
from flask_security import Security
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
cache = Cache()
csrf_protect = CSRFProtect()
db = SQLAlchemy()
debug_toolbar = DebugToolbarExtension()
mail = Mail()
migrate = Migrate()
security = Security()
