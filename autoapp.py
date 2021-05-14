# -*- coding: utf-8 -*-
"""Create an application instance."""

import threading
import requests
import time

from dotenv import load_dotenv
from flask.helpers import get_debug_flag

from beton.app import create_app
from beton.logger import log
from beton.settings import DevConfig, ProdConfig

load_dotenv()
CONFIG = DevConfig if get_debug_flag() else ProdConfig

# this function warms up flask when run in devel mode
def start_runner():
    def start_loop():
        not_started = True
        while not_started:
            log.info('...in start loop...')
            try:
                r = requests.get('http://127.0.0.1:5000/')
                if r.status_code == 200:
                    log.info('...Flask server started, quiting start loop thread. Amazing, now hard production time :-)')
                    not_started = False
                #print(r.status_code)
            except:
                log.info('Server not yet started')
            time.sleep(2)

    log.info('Started runner...')
    thread = threading.Thread(target=start_loop)
    thread.start()

#start_runner()
app = create_app(CONFIG)
