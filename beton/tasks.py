# -*- coding: utf-8 -*-
"""Various cron jobs."""

import os
import random

from configparser import ConfigParser
from datetime import datetime, timedelta
from dateutil.relativedelta import *
from hashlib import blake2b
from jinja2 import Template
from memory_tempfile import MemoryTempfile

from flask import current_app
from flask.helpers import get_debug_flag

from beton.extensions import cache, kvstore, scheduler
from beton.logger import log
from beton.threads import DBHandler, Helper
from beton.user.models import Banner, Campaignes, Impressions, Orders, Payments, Websites, Zones
from beton.utils import dblogger


# ################
# Helper functions

# ################
# Main tasks

# In production we do it every 6 hours, but in debug mode every minute.
frequency = 1 if get_debug_flag() else 360


@scheduler.task('interval', id='cleanup_sessions', minutes=frequency)
def cleanup_sessions():
    with scheduler.app.app_context():
        try:
            kvstore.cleanup_sessions()
            log.info("Running crontab: cleaned up sessions.")
        except Exception as e:
            log.debug("Exception")
            log.exception(e)


# We want to have this data updated every minute for banner rotation
frequency = 1


@scheduler.task('interval', id='configs', minutes=frequency)
def configs():

    def write_nginx_conf(nginxdata, website, nginxconfile):
        '''writes nginx.conf for every website'''

        with open(nginxconfile, "r", encoding='utf-8') as r:
            currenthash = blake2b(r.read().encode('utf-8')).hexdigest()
            #log.debug(f"NGINX currenthash: {currenthash}")
            newhash = blake2b(nginxdata.encode('utf-8')).hexdigest()
            #log.debug(f"NGINX newhash: {newhash}")
        if currenthash != newhash:
            with open(nginxconfile, "w") as w:
                w.write(nginxdata)
                log.info(f"NGINX: Writing configuration for website {website}.")
            log.debug(f"LOCATIONs: {nginxdata}")
        else:
            log.info(f"NGINX: Keeping unchanged configuration for website {website}.")

    def do_nginx_conf():
        websites = Websites.query.filter_by(active=True).all()
        for website in websites:
            sql = Campaignes.query.join((Orders.campaigne)).filter(Campaignes.active==True).filter(Websites.name==website.name).join(
                Payments).join(Zones).join(Banner).join(Websites).join(Impressions).order_by(Campaignes.id)
            all_campaigns = sql.with_entities(Campaignes, Payments, Orders, Zones, Banner, Websites, Impressions).all()
            #log.debug(f"ALL CAMPAIGNES: {all_campaigns}")
            nginxconfile = nginxconfdir + "/" + website.name + ".conf"
            nginxtmp = f"# Nginx beton configuration for website {website.name}:"
            for campaign in all_campaigns:
                # We want actually running campaignes only
                #log.debug(f"CAMPAIGN: {campaign}")
                #is_running = campaign[0].begins_at < datetime.utcnow() and campaign[0].stops_at > datetime.utcnow()
                is_running = campaign[0].begins_at < datetime.utcnow() and campaign[0].stops_at > datetime.utcnow()
                #log.debug(f"IS RUNNING?: {is_running}")
                if is_running is True:
                    is_paid = campaign[1].confirmed_at > datetime.min
                    #log.debug(f"CAMPAIGN: {campaign} - IS PAID?: {is_paid}")
                    if is_paid is True:
                        banner_fname = campaign[4].filename
                        #log.debug(f"BANNER_FNAME: {banner_fname}")
                        # Preparing environment for jinja template
                        fname_org = dbhandler.getl(campaign[0].id).path
                        #log.debug(f"FNAME_ORG: {fname_org}")
                        y, banner_suffix = os.path.splitext(banner_fname)
                        fname_uri = f"{fname_org}.{campaign[0].id}{banner_suffix}"
                        #log.debug(f"FNAME_URI: {fname_uri}")
                        location = template.render(
                                        fname_uri=fname_uri,
                                        nginx_banner_dir=nginx_banner_dir,
                                        banner_fname=banner_fname,
                                        syslogd_address=syslogd_address,
                                        syslogd_port=syslogd_port,
                            )
                        nginxtmp += location
                        curzone = campaign[3].id
                        zones_current.append({
                            "zone": curzone,
                            "img": fname_uri,
                            "url": campaign[4].url
                        })
                        try:
                            all_zones.remove(curzone)
                        except ValueError:
                            pass
            #
            write_nginx_conf(nginxtmp, website.name, nginxconfile)

    def do_zones_ini(zones_ini, zones_current):
        '''writes zone.ini file as a portable data source for websites'''

        log.debug("Processing zone.ini...")
        for zone in Zones.query.filter(Zones.active==True).order_by(Zones.id).all():
            #log.debug(zone)
            entries = [i for i, d in enumerate(zones_current) if d["zone"] == zone.id]
            #log.debug(entries)
            if len(entries) > 0:
                entry = random.choice(entries)  # we want to have only one banner in each zone
                #log.debug(entry)
                curzone = f"ZONE_{zone.id}"
                zones_object[curzone] = {
                    "img": zones_current[entry]['img'],
                    "url": zones_current[entry]['url']
                }

        with open(zones_ini, "r", encoding='utf-8') as r:
            currenthash = blake2b(r.read().encode('utf-8')).hexdigest()
            #log.debug(f"INI currenthash: {currenthash}")
            tempfile = MemoryTempfile()
            with tempfile.TemporaryFile(mode = 'w+') as t:
                zones_object.write(t)
                t.seek(0)
                newhash = blake2b(t.read().encode('utf-8')).hexdigest()
                #log.debug(f"INI newhash: {newhash}")
        if currenthash != newhash:
            with open(zones_ini, "w", encoding='utf-8') as w:
                zones_object.write(w)
                log.info(f"INI: Writing configuration.")
        else:
            log.info(f"INI: Keeping old config.")

    log.debug("Processing configs...")
    helper = Helper()
    dbhandler = DBHandler()
    outfile = ""
    zones_current = []
    all_zones = []
    # jinja template for a single campaign entrance in nginx config
    j2temp = """
location = {{ fname_uri }} {
   alias {{ nginx_banner_dir }}/{{ banner_fname }};
   access_log syslog:server={{ syslogd_address }}:{{ syslogd_port }},facility=news,tag=beton,severity=info combined;
   # if you use mod_pagespeed, you should disallow any modifications
   pagespeed Disallow {{ fname_uri }};
}
    """
    template = Template(j2temp)
    zones_object = ConfigParser()

    with scheduler.app.app_context():
        nginxconfdir = current_app.config.get('NGINXCONFDIR')
        nginx_banner_dir = current_app.config.get('NGINXBANNERDIR')
        syslogd_address = current_app.config.get('SYSLOGD_ADDRESS')
        syslogd_port = current_app.config.get('SYSLOGD_PORT')
        zones_ini = current_app.config.get('ZONES_INI')
        # we are checking all active campaignes and creating appropriate nginx
        # configs
        # we need to have a seperate config for each domain
        for zone in Zones.query.filter(Zones.active==True).order_by(Zones.id).all():
            all_zones.append(zone.id)
        log.debug(f"all_zones_before: {all_zones}")
        #
        do_nginx_conf()
        #
        do_zones_ini(zones_ini, zones_current)
        log.debug(f"all_zones_after: {all_zones}")
