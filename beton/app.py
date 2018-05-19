"""The app module, containing the app factory function."""
from flask import Flask, render_template
from flask_kvsession import KVSessionExtension
from flask_moment import Moment
from flask_user import UserManager, SQLAlchemyAdapter
from simplekv.fs import FilesystemStore
from werkzeug.contrib.fixers import ProxyFix

from beton import commands, public, user
from beton.assets import assets
from beton.extensions import bcrypt, cache, configure_uploads, csrf_protect, patch_request_class
from beton.extensions import db, debug_toolbar, images, login_manager, mail, migrate
from beton.user.models import User

moment = Moment()
sesstore = FilesystemStore('./data')


def create_app():
    """An application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """
    app = Flask(__name__.split('.')[0])
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.config.from_pyfile('./settings.py')
    app.config.from_envvar('BETON')
    register_extensions(app)
    register_blueprints(app)
    register_errorhandlers(app)
    register_shellcontext(app)
    register_commands(app)
    return app


def register_extensions(app):
    """Register Flask extensions."""
    assets.init_app(app)
    bcrypt.init_app(app)
    cache.init_app(app)
    db.init_app(app)
    csrf_protect.init_app(app)
    debug_toolbar.init_app(app)
    migrate.init_app(app, db)
    configure_uploads(app, images)
    patch_request_class(app, size=577216)
    moment.init_app(app)
    mail.init_app(app)
    db_adapter = SQLAlchemyAdapter(db, User)
    user_manager = UserManager(db_adapter, app)
    KVSessionExtension(sesstore, app)
    return None


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(public.views.blueprint,
                           url_prefix=app.config.get('SUBDIR'))
    app.register_blueprint(user.views.blueprint,
                           url_prefix=app.config.get('SUBDIR'))
    return None


def register_errorhandlers(app):
    """Register error handlers."""
    def render_error(error):
        """Render error template."""
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, 'code', 500)
        return render_template('{0}.html'.format(error_code)), error_code
    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)
    return None


def register_shellcontext(app):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {
            'db': db,
            'User': user.models.User}

    app.shell_context_processor(shell_context)


def register_commands(app):
    """Register Click commands."""
    app.cli.add_command(commands.test)
    app.cli.add_command(commands.lint)
    app.cli.add_command(commands.clean)
    app.cli.add_command(commands.urls)
