# -*- coding: utf-8 -*-
"""Click commands."""
import click
import os
import random

from configparser import ConfigParser
from datetime import datetime, timedelta
from dateutil.relativedelta import *
from glob import glob
from hashlib import blake2b
from jinja2 import Template
from memory_tempfile import MemoryTempfile
from subprocess import call

from flask import current_app
from flask.helpers import get_debug_flag
from flask.cli import with_appcontext
from werkzeug.exceptions import MethodNotAllowed, NotFound

from beton.extensions import cache, kvstore
from beton.logger import log
from beton.threads import DBHandler, Helper
from beton.user.models import Banner, Campaignes, Impressions, Orders, Payments, Websites, Zones
from beton.utils import dblogger


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.join(HERE, os.pardir)
TEST_PATH = os.path.join(PROJECT_ROOT, 'tests')


@click.command()
def test():
    """Run the tests."""
    import pytest
    rv = pytest.main([TEST_PATH, '--verbose'])
    exit(rv)


@click.command()
@click.option('-f', '--fix-imports', default=False, is_flag=True,
              help='Fix imports using isort, before linting')
def lint(fix_imports):
    """Lint and check code style with flake8 and isort."""
    skip = ['requirements']
    root_files = glob('*.py')
    root_directories = [
        name for name in next(os.walk('.'))[1] if not name.startswith('.')]
    files_and_directories = [
        arg for arg in root_files + root_directories if arg not in skip]

    def execute_tool(description, *args):
        """Execute a checking tool with its arguments."""
        command_line = list(args) + files_and_directories
        click.echo('{}: {}'.format(description, ' '.join(command_line)))
        rv = call(command_line)
        if rv != 0:
            exit(rv)

    if fix_imports:
        execute_tool('Fixing import order', 'isort', '-rc')
    execute_tool('Checking code style', 'flake8')


@click.command()
def clean():
    """Remove *.pyc and *.pyo files recursively starting at current directory.

    Borrowed from Flask-Script, converted to use Click.
    """
    for dirpath, dirnames, filenames in os.walk('.'):
        for filename in filenames:
            if filename.endswith('.pyc') or filename.endswith('.pyo'):
                full_pathname = os.path.join(dirpath, filename)
                click.echo('Removing {}'.format(full_pathname))
                os.remove(full_pathname)


@click.command()
@click.option('--url', default=None,
              help='Url to test (ex. /static/image.png)')
@click.option('--order', default='rule',
              help='Property on Rule to order by (default: rule)')
@with_appcontext
def urls(url, order):
    """Display all of the url matching routes for the project.

    Borrowed from Flask-Script, converted to use Click.
    """
    rows = []
    column_length = 0
    column_headers = ('Rule', 'Endpoint', 'Arguments')

    if url:
        try:
            rule, arguments = (
                current_app.url_map
                           .bind('localhost')
                           .match(url, return_rule=True))
            rows.append((rule.rule, rule.endpoint, arguments))
            column_length = 3
        except (NotFound, MethodNotAllowed) as e:
            rows.append(('<{}>'.format(e), None, None))
            column_length = 1
    else:
        rules = sorted(
            current_app.url_map.iter_rules(),
            key=lambda rule: getattr(rule, order))
        for rule in rules:
            rows.append((rule.rule, rule.endpoint, None))
        column_length = 2

    str_template = ''
    table_width = 0

    if column_length >= 1:
        max_rule_length = max(len(r[0]) for r in rows)
        max_rule_length = max_rule_length if max_rule_length > 4 else 4
        str_template += '{:' + str(max_rule_length) + '}'
        table_width += max_rule_length

    if column_length >= 2:
        max_endpoint_length = max(len(str(r[1])) for r in rows)
        # max_endpoint_length = max(rows, key=len)
        max_endpoint_length = (
            max_endpoint_length if max_endpoint_length > 8 else 8)
        str_template += '  {:' + str(max_endpoint_length) + '}'
        table_width += 2 + max_endpoint_length

    if column_length >= 3:
        max_arguments_length = max(len(str(r[2])) for r in rows)
        max_arguments_length = (
            max_arguments_length if max_arguments_length > 9 else 9)
        str_template += '  {:' + str(max_arguments_length) + '}'
        table_width += 2 + max_arguments_length

    click.echo(str_template.format(*column_headers[:column_length]))
    click.echo('-' * table_width)

    for row in rows:
        click.echo(str_template.format(*row[:column_length]))


"""Various cron jobs."""


@click.command()
@with_appcontext
def cleanup_sessions():
    """Cleaning up old sessions.
    """
    try:
        kvstore.cleanup_sessions()
        log.info("Running crontab: cleaned up sessions.")
    except Exception as e:
        log.debug("Exception")
        log.exception(e)


@click.command()
@with_appcontext
def ngrotate():
    """Banner rotation for Nginx
    """

    def filename_uri(cid, filename, path):
        y, banner_suffix = os.path.splitext(filename)
        fname_uri = f"{path}.{cid}{banner_suffix}"
        return fname_uri

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
            sql = Campaignes.query.select_from(Campaignes).join((Orders.campaigne)).filter(
                Campaignes.active==True).filter(Websites.name==website.name).join(
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
                        fname_uri = filename_uri(campaign[0].id, campaign[4].filename, campaign[6].path)
                        #log.debug(f"FNAME_URI: {fname_uri}")
                        location = template.render(
                                        fname_uri=fname_uri,
                                        nginx_banner_dir=nginx_banner_dir,
                                        banner_fname=campaign[4].filename,
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
                        # we need to know which zones have no running campaign atm
                        try:
                            all_zones.remove(curzone)
                        except ValueError:
                            pass

            # processing unfilled zones with default campaignes if exist
            if len(all_zones) > 0:
                for zone in all_zones:
                    default_campaignes = Campaignes.query.filter_by(
                        zoneid=zone).filter_by(default=True).filter_by(active=True).join(
                            Zones).join(Banner).join(Impressions).with_entities(Campaignes.id,Banner.url,Banner.filename,Impressions.path).all()
                    #log.debug(default_campaignes)
                    if len(default_campaignes) > 0:
                        for default_campaign in default_campaignes:
                            fname_uri = filename_uri(default_campaign.id, default_campaign.filename, default_campaign.path)
                            location = template.render(
                                            fname_uri=fname_uri,
                                            nginx_banner_dir=nginx_banner_dir,
                                            banner_fname=default_campaign.filename,
                                            syslogd_address=syslogd_address,
                                            syslogd_port=syslogd_port,
                                )
                            nginxtmp += location

            # finally, writing results to nginx config files
            write_nginx_conf(nginxtmp, website.name, nginxconfile)


    def do_zones_ini(zones_ini, zones_current):
        '''writes zone.ini file as a portable data source for websites'''

        log.debug("Processing zone.ini...")
        # zone iteration
        for zone in Zones.query.filter_by(active=True).order_by(Zones.id).all():
            #log.debug(zone)
            entries = [i for i, d in enumerate(zones_current) if d["zone"] == zone.id]
            #log.debug(entries)
            curzone = f"ZONE_{zone.id}"
            if len(entries) > 0:
                entry = random.choice(entries)  # we want to have only one banner in each zone
                #log.debug(entry)
                zones_object[curzone] = {
                    "img": zones_current[entry]['img'],
                    "url": zones_current[entry]['url']
                }
            else:
                # we need to deploy default campaign(es) as there is no paid
                # campaignes available for this zone
                default_campaignes = Campaignes.query.filter_by(
                    zoneid=zone.id).filter_by(default=True).filter_by(active=True).join(
                        Zones).join(Banner).join(Impressions).with_entities(Campaignes.id,Banner.url,Banner.filename,Impressions.path).all()
                #log.debug(default_campaignes)
                # we want to have only one banner in each zone in case if there
                # are many default campaignes for this zone
                if len(default_campaignes) > 0:
                    default_campaign = random.choice(default_campaignes)
                    fname_uri = filename_uri(default_campaign.id, default_campaign.filename, default_campaign.path)
                    zones_object[curzone] = {
                        "img":  fname_uri,
                        "url":  default_campaign.url
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
                log.info(f"INI: Writing new banners configuration.")
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
    #log.debug(f"all_zones_before: {all_zones}")
    #
    do_nginx_conf()
    #
    do_zones_ini(zones_ini, zones_current)
    #log.debug(f"all_zones_after: {all_zones}")
