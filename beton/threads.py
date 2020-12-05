'''
Programs which are running along the flask.

URL Parsing: https://docs.python.org/3/library/urllib.parse.html
Syslog parsing: https://gist.github.com/leandrosilva/3651640
'''
import os
import socketserver
import sys
from datetime import datetime
from lars import apache
from memory_tempfile import MemoryTempfile
from pprint import pformat as pf
from pyparsing import Word, alphas, Suppress, Combine, nums, string, Optional, Regex
from time import strftime

from beton.logger import log
from beton.user.models import Impressions

class Helper(object):
    '''
    Helping to understand the concept
    '''
    def __init__(self):
        path = None

    def getrandomurlimg(self, website):
        return "https://hyperreal.info/sites/hyperreal.info/files/grafika_artykul_skrot/62.1.jpg"

    def getcidfromreqpath(self, path):
        x, y = os.path.splitext(path)
        try:
            cid = x.split(".")[-1]
            return(int(cid))
        except:
            return 0


class DBHandler(object):
    '''
    Handling database
    '''
    def __init__(self):
        cid = 0

    def cup(self, cid):
        '''
        Updating impressions counter by 1
        '''
        c = Impressions.query.filter_by(cid=cid).first()
        before = c.impressions
        c.impressions = Impressions.impressions + 1

        return(before)


class Parser(object):
    '''
    Syslog parser
    '''
    def __init__(self):
        ints = Word(nums)

        # priority
        priority = Suppress("<") + ints + Suppress(">")

        # timestamp
        month = Word(string.ascii_uppercase , string.ascii_lowercase, exact=3)
        day   = ints
        hour  = Combine(ints + ":" + ints + ":" + ints)

        timestamp = month + day + hour

        # hostname
        hostname = Word(alphas + nums + "_" + "-" + ".")

        # appname
        appname = Word(alphas + "/" + "-" + "_" + ".") + Optional(Suppress("[") + ints + Suppress("]")) + Suppress(":")

        # message
        message = Regex(".*")

        # pattern build
        self.__pattern = priority + timestamp + hostname + appname + message

    def parse(self, line):
        parsed = self.__pattern.parseString(line)

        payload              = {}
        payload["priority"]  = parsed[0]
        payload["timestamp"] = f"{parsed[1]} {parsed[2]} {parsed[3]}"
        payload["hostname"]  = parsed[4]
        payload["appname"]   = parsed[5]
        payload["message"]   = parsed[6]

        return payload

class MyUDPHandler(socketserver.BaseRequestHandler):
    """
    Listens for syslog submissions.
    """
    def handle(self):
        parser = Parser()
        helper = Helper()
        db = DBHandler()
        data = self.request[0]
        socket = self.request[1]
        logo = data.decode('ascii')
        #print(logo)
        fields = parser.parse(logo)
        #print(fields)
        tempfile = MemoryTempfile()
        with tempfile.TemporaryFile(mode = 'w+') as ntf:
            ntf.writelines(fields['message'])
            ntf.seek(0)
            with apache.ApacheSource(ntf, log_format=apache.COMBINED) as a:
                for row in a:
                    cup = None
                    cid = helper.getcidfromreqpath(row.request.url.path_str)
                    status = row.status
                    # TODO: check if referer is from our sites
                    if cid != 0:
                        if status == 200 or status == 304:
                            cup = db.cup(cid)
                    out = f"{row.status} {row.request.url.path_str} - {cid}: {cup}"
                    log.debug(f"NGINX: {out}")
            ntf.close()
        socket.sendto(data.upper(), self.client_address)
