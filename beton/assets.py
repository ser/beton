# -*- coding: utf-8 -*-
"""Application assets."""
from flask_assets import Bundle, Environment

css = Bundle(
    'libs/bootstrap/dist/css/bootstrap.css',
    'libs/bootstrap-calendar/css/calendar.css',
    'libs/daterangepicker/demo/css/picker.css',
    'css/style.css',
    filters='cssmin',
    output='public/css/common.css'
)

js = Bundle(
    'libs/jQuery/dist/jquery.js',
    'libs/bootstrap/dist/js/bootstrap.js',
    #   'libs/jQuery-File-Upload/js/jquery.fileupload.js',
    #   'libs/jQuery-File-Upload/js/jquery.fileupload-process.js',
    #   'libs/jQuery-File-Upload/js/jquery.fileupload-ui.js',
    #   'static/libs/salvattore/dist/salvattore.min.js',
    #   'libs/media-match/media.match.js',
    'libs/underscore/underscore.js',
    'libs/moment/moment.js',
    'libs/moment-timezone/moment-timezone.js',
    'libs/daterangepicker/lib/daterangepicker/daterangepicker.js',
    'libs/bootstrap-calendar/js/calendar.js',
    'libs/enquire/dist/enquire.js',
    'libs/savvior/dist/savvior.js',
    'js/plugins.js',
    filters='jsmin',
    output='public/js/common.js'
)

assets = Environment()

assets.register('js_all', js)
assets.register('css_all', css)
