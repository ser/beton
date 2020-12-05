"""The app module, containing the app factory function."""

import os
import socketserver
import threading

from flask import Flask, current_app, render_template
from flask_uploads import configure_uploads, patch_request_class, IMAGES, UploadSet
from werkzeug.middleware.proxy_fix import ProxyFix

from beton import commands
from beton.assets import assets
from beton.extensions import bcrypt, cache, csrf_protect, db, debug_toolbar, kvstore
from beton.extensions import mail, migrate, moment, scheduler, security, user_datastore
from beton.logger import log
from beton.settings import ProdConfig
from beton.threads import DBHandler, Helper, MyUDPHandler, Parser
from beton.user.forms import ExtendedConfirmRegisterForm


def create_app(config_object=ProdConfig):
    """An application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """
    app = Flask(__name__.split('.')[0])
    app.wsgi_app = ProxyFix(app.wsgi_app)
    app.config.from_object(config_object)
    # app.config.from_envvar('BETON')
    register_extensions(app)
    register_configuration(app)
    register_scheduler(app)
    register_blueprints(app)
    register_errorhandlers(app)
    register_shellcontext(app)
    #register_commands(app)  # not ready to run yet
    register_threads(app)
    return app


def register_extensions(app):
    """Register Flask extensions."""
    assets.init_app(app)
    bcrypt.init_app(app)
    cache.init_app(app)
    csrf_protect.init_app(app)
    db.app = app
    db.init_app(app)
    debug_toolbar.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    moment.init_app(app)
    kvstore.init_app(app)
    scheduler.api_enabled = True
    scheduler.init_app(app)
    security.init_app(app,
                      user_datastore,
                      confirm_register_form=ExtendedConfirmRegisterForm)
    return None


def register_configuration(app):
    images = UploadSet('images', IMAGES)
    configure_uploads(app, images)
    # max banner weight
    patch_request_class(app, size=577216)

    return None

def register_scheduler(app):
    '''
    # Setting up crontabs
    # To avoid running twice in WERKZEUG debug mode we need to make "if":
    # https://stackoverflow.com/questions/14874782/apscheduler-in-flask-executes-twice
    # If you are using uwsgi, leave it like it is.
    #
    '''
#        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    @app.before_first_request
    def load_tasks():
        scheduler.start()
        from beton import tasks
    '''
    # If you use uwsgi comment above  and commend this out:
    '''
    #scheduler.start()
    #from beton import tasks


def register_threads(app):
    '''
    Running all additional threads accompany our Flask
    '''
    @app.before_first_request
    def activate_syslogd():
        def run_syslogd():
            '''
            Syslogd server listening for nginx submissions on all interfaces,
            port 13131
            '''
            HOST, PORT = "0.0.0.0", 13131
            with socketserver.UDPServer((HOST, PORT), MyUDPHandler) as server:
                log.info("RUNNING syslogd for nginx submissions...")
                server.serve_forever()
        thread = threading.Thread(target=run_syslogd)
        thread.start()


def register_blueprints(app):
    """Register Flask blueprints."""
    from beton import public, user
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
    return None


def register_commands(app):
    """Register Click commands."""
    app.cli.add_command(commands.test)
    app.cli.add_command(commands.lint)
    app.cli.add_command(commands.clean)
    app.cli.add_command(commands.urls)
    return None
