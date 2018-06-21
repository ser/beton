# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located in app.py."""
# from flask_admin import Admin
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_debugtoolbar import DebugToolbarExtension
# from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin, login_required
from flask_sqlalchemy import SQLAlchemy

#from beton.user.models import User, Role

bcrypt = Bcrypt()
csrf_protect = CSRFProtect()
db = SQLAlchemy()
# login_manager = LoginManager()
migrate = Migrate()
cache = Cache()
debug_toolbar = DebugToolbarExtension()
mail = Mail()
#user_datastore = SQLAlchemyUserDatastore(db, User, Role)
#security = Security(user_datastore)
security = Security()
# admin = Admin()
