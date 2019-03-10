"""Application assets."""
"""
    TODO:
    'libs/bootswatch/dist/' + bootswatch + '/bootstrap.css',
    bootswatch = app.config.get('BOOTSWATCH')
"""

from flask_assets import Bundle, Environment


css = Bundle(
    'libs/fullcalendar/dist/fullcalendar.css',
    'libs/bootstrap-datepicker/dist/css/bootstrap-datepicker3.css',
    'css/style.css',
    filters='cssmin',
    output='public/css/common.css'
)

js = Bundle(
    'libs/bootstrap/dist/js/bootstrap.js',
    'libs/jquery-timeago/jquery.timeago.js',
    'libs/gasparesganga-jquery-loading-overlay/src/loadingoverlay.js',
    'libs/underscore/underscore.js',
    'libs/moment/moment.js',
    'libs/moment-timezone/moment-timezone.js',
    'libs/fullcalendar/dist/fullcalendar.js',
    'libs/bootstrap-datepicker/js/bootstrap-datepicker.js',
    'libs/enquire/dist/enquire.js',
    'libs/progresspiesvg/js/jquery-progresspiesvg.js',
    'libs/progresspiesvg/js/jquery-progresspiesvg-valueDisplay.js',
    'libs/qrious/dist/qrious.js',
    'libs/holderjs/holder.js',
    'js/plugins.js',
    filters='jsmin',
    output='public/js/common.js'
)

assets = Environment()

assets.register('js_all', js)
assets.register('css_all', css)
