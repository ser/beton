import logging

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.DEBUG)
_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
_console_handler.setFormatter(_formatter)

log = logging.getLogger('beton')
log.setLevel(logging.DEBUG)
log.addHandler(_console_handler)
