from bottle import route, run, JSONPlugin, request
import bottle
import time
import os
import oursql
from bottle_compressor import CompressorPlugin
import logging
import json
from functools import partial


compressor_plugin = CompressorPlugin(compress_level=3)
bottle.install(compressor_plugin)


#from ujson import dumps
from bottle import json_dumps as dumps
better_dumps = partial(dumps, ensure_ascii=False, separators=(',', ':'))
bottle.default_app().uninstall(JSONPlugin)
bottle.default_app().install(JSONPlugin(better_dumps))

# TODO: timestamp

ALL_PROPS = ["rev_sha1", "rev_len", "rev_text_id", "rev_timestamp", "rev_minor_edit", "rev_user_text", "rev_comment", "rev_parent_id", "rev_deleted", "rev_page", "rev_user", "rev_id"]

DESIRED_PROPS = ["rev_sha1", "rev_len", "rev_timestamp", "rev_minor_edit", "rev_user_text", "rev_comment", "rev_deleted", "rev_user", "rev_id"]


class AccessLogger(object):
    def __init__(self, logfile):
        self.logfile = logfile
        self.logger = logging.getLogger('AccessLogger')
        self.logger.setLevel(logging.INFO)
        write_handler = logging.FileHandler(logfile)
        self.logger.addHandler(write_handler)

    def log(self, action, hostname, params):
        self.logger.info(json.dumps({'time': time.asctime(), 'action': action, 'hostname': hostname, 'params': params}))

    def read(self, no):
        history = open(self.logfile, 'r')
        lines = history.readlines()
        return [json.loads(line) for line in lines[-no:]][::-1]

LOG = AccessLogger('access.log')


class ArticleHistory(object):
    '''article history object'''
    def __init__(self, title, namespace=0):
        try:
            s_time = time.time()
            db = oursql.connect(db='enwiki_p',
                host="enwiki-p.rrdb.toolserver.org",
                read_default_file=os.path.expanduser("~/.my.cnf"))
        except oursql.ProgrammingError as (error_number, error_str, donno):
            print str(error_number) + ':  ' + error_str
            self.revisions = {'error': error_str}
            self.dur = time.time() - s_time
        except:
            raise
        else:
            cursor = db.cursor(oursql.DictCursor)
            cursor.execute(u'''
                SELECT      {}
                FROM        revision
                INNER JOIN  page ON revision.rev_page = page.page_id
                WHERE       page_title = ? AND page.page_namespace = ?;
                '''.format(', '.join(DESIRED_PROPS)), (title, namespace))
            self.revisions = cursor.fetchall()
            self.dur = time.time() - s_time


class WL(object):
    '''article history object'''
    def __init__(self, title, namespace=0):
        try:
            s_time = time.time()
            db = oursql.connect(db='enwiki_p',
                host="enwiki-p.rrdb.toolserver.org",
                read_default_file=os.path.expanduser("~/.my.cnf"))
            cursor = db.cursor(oursql.DictCursor)
        except oursql.ProgrammingError as (error_number, error_str, donno):
            print str(error_number) + ':  ' + error_str
            self.revisions = {'error': error_str}
            self.dur = time.time() - s_time
        except:
            raise
        else:
            cursor.execute(u'''
                SELECT      count(ts_wl_user_touched_cropped)
                FROM        watchlist
                WHERE       wl_title = ? AND wl_namespace = ?;
                ''', (title, namespace))
            self.wers = cursor.fetchall()
            self.dur = time.time() - s_time


@route('/writelog/')
def write_log():
    action = request.query.action
    hostname = request.query.hostname
    params = request.query.params
    if action and hostname and params:
        LOG.log(action, hostname, params)
        return {'log': LOG.read(1), 'write': 'success'}
    else:
        return {'write': 'failure'}


@route('/readlog')
@route('/readlog/')
@route('/readlog/<lines:path>')
def read_log(lines=10):
    if type(lines) is not int:
        try:
            lines = int(lines)
        except ValueError:
            lines = 10
    return {'log': LOG.read(lines)}


@route('/revisions/<title:path>')
def get_revisions(title):
    article = ArticleHistory(title)
    return {'result': article.revisions}


@route('/all')
@route('/all/')
def get_everything():
    title = request.query.title
    talk = ArticleHistory(title, 1)
    article = ArticleHistory(title)
    return {'article': article.revisions, 'article_time': str(article.dur), 'talk': talk.revisions, 'talk_time': str(talk.dur)}


@route('/wl')
def get_wl():
    title = request.query.title
    w = WL(title)
    return {'watchers': w.wers[0]['count(ts_wl_user_touched_cropped)'], 'query_duration': str(w.dur)}


@route('/uptime')
@route('/uptime/')
def get_uptime():
    import subprocess
    import socket
    import os
    uptime, _, load = subprocess.check_output(['uptime']).partition(',  load average:')
    return {'uptime': uptime.strip(), 'load': load.strip(), 'hostname': socket.gethostname(), 'uname': os.uname()}

if __name__ == '__main__':
    run(host='0.0.0.0', port=8089, reloader=True, server='twisted', debug=True)
