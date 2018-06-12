# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located in app.py."""
# from flask_admin import Admin
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import UploadSet, IMAGES
from flask_user import UserManager, SQLAlchemyAdapter
from flask_wtf.csrf import CSRFProtect

from beton.user.models import User

bcrypt = Bcrypt()
csrf_protect = CSRFProtect()
db = SQLAlchemy()
db_adapter = SQLAlchemyAdapter(db, User)
login_manager = LoginManager()
user_manager = UserManager(db_adapter)
migrate = Migrate()
cache = Cache()
debug_toolbar = DebugToolbarExtension()
mail = Mail()
images = UploadSet('images', IMAGES)
# admin = Admin()
