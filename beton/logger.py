import logging

from flask.helpers import get_debug_flag

FORMAT = '[%(asctime)s] [%(levelname)s] %(message)s'
logging.basicConfig(format=FORMAT)

log = logging.getLogger(__name__)

if get_debug_flag():
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)
