import time
import bottle
from bottle import Bottle, JSONPlugin, run, TemplatePlugin, template
from bottle import static_file
from collections import defaultdict
import sys
from lib import wapiti

import psutil
import os

import gevent
from gevent import socket
from gevent.threadpool import ThreadPool

from functools import partial
better_dumps = partial(bottle.json_dumps, indent=2,
    sort_keys=True, default=repr)

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 1870
DEFAULT_SERVER = 'gevent'


def find_port(host=DEFAULT_HOST, start_port=DEFAULT_PORT, end_port=None):
    start_port = int(start_port)
    end_port = end_port or start_port + 100
    for p in range(start_port, end_port):
        try:
            s = socket.socket()
            s.bind((host, p))
        except socket.error:
            continue
        else:
            s.close()
            return p
    return None


class LoupeDashboard(Bottle):

    def __init__(self, louper, *args, **kwargs):
        super(LoupeDashboard, self).__init__(*args, **kwargs)
        self.loupe_pool = louper.loupe_pool
        self.total_loupes = louper.total_count
        self.results = louper.results
        self.inputs = louper.input_classes
        self.failed_stats = louper.failed_stats
        self.fetch_failures = louper.fetch_failures
        self.start_time = time.time()
        self.tpool = None

        self.start_time = kwargs.get('start_time') or time.time()
        self.start_cmd = kwargs.get('start_cmd') or ' '.join(sys.argv)
        self.host_machine = kwargs.get('hostname') or socket.gethostname()
        self.open_toolserver_queries = self.get_toolserver_openlog()
        if self.open_toolserver_queries > 0:
            print '\nNote: there are', self.open_toolserver_queries, 'open queries on toolserver\n'
        self.send_toolserver_log('start', start_time=self.start_time)
        self.toolserver_uptime = self.get_toolserver_uptime()
        self.route('/', callback=self.render_dashboard, template='dashboard')
        self.route('/summary', callback=self.get_summary_dict, template='summary')
        self.route('/all_results', callback=self.get_all_results)
        self.route('/static/<filepath:path>', callback=self.serve_static)
        self.uninstall(JSONPlugin)
        self.install(JSONPlugin(better_dumps))
        self.install(TemplatePlugin())
        self.sys_peaks = defaultdict(float)

    def run(self, **kwargs):
        if self.tpool is None:
            self.tpool = ThreadPool(2)
        kwargs['host'] = kwargs.get('host', DEFAULT_HOST)
        pref_port = kwargs.get('port', DEFAULT_PORT)
        port = find_port(kwargs['host'], pref_port)
        if port is None:
            raise Exception('Could not find suitable port to run LoupeDashboard server.')
        else:
            kwargs['port'] = port
        kwargs['server'] = kwargs.get('server', DEFAULT_SERVER)
        self.tpool.spawn(run, self, **kwargs)

    def get_summary_dict(self, with_meta=True):
        cur_time = time.time()
        success_count = len([o for o in self.results.values() if o.get('is_successful')])
        failure_count = len(self.results) - success_count
        in_prog_times = dict([(o.title, cur_time - o.times['create']) for o in self.loupe_pool])
        ret = {'in_progress_count': len(self.loupe_pool),
               'in_progress': in_prog_times,
               'complete_count': len(self.results),
               'success_count': success_count,
               'failure_count': failure_count,
               'total_articles': self.total_loupes,
               }
        if with_meta:
            ret['meta'] = self.get_meta_dict()
        return ret

    def get_meta_dict(self):
        return {'start_time': time.strftime("%d %b %Y %H:%M:%S UTC", time.gmtime(self.start_time)),
                'duration': time.time() - self.start_time,
                'start_cmd': self.start_cmd,
                'host_machine': self.host_machine
                }

    def get_sys_stats(self):
        p = psutil.Process(os.getpid())
        connection_status = defaultdict(int)
        for connection in p.get_connections():
            connection_status[connection.status] += 1
            connection_status['total'] += 1
        ret = {'mem_info': p.get_memory_info().rss,
               'mem_pct': p.get_memory_percent(),
               'num_fds': p.get_num_fds(),
               'connections': connection_status,
               'no_connections': connection_status['total'],
               'cpu_pct': p.get_cpu_percent(interval=.01)
                }
        for (key, value) in ret.iteritems():
            if key is not 'connections' and value > self.sys_peaks[key]:
                self.sys_peaks[key] = value
        return ret

    def get_dict(self):
        ret = {}
        ret['summary'] = self.get_summary_dict(with_meta=False)
        ret['sys'] = self.get_sys_stats()
        ret['sys_peaks'] = self.sys_peaks
        ret['input_classes'] = [i.__name__ for i in self.inputs]
        ret['in_progress'] = [o.get_status() for o in self.loupe_pool]
        ret['complete'] = [o.get('status') for o in self.results.values()]
        ret['toolserver'] = self.toolserver_uptime
        ret['meta'] = self.get_meta_dict()
        ret['failed_stats'] = self.failed_stats
        ret['fetch_failures'] = self.fetch_failures
        return ret

    def get_all_results(self):
        ret = {}
        ret['results'] = self.results
        return ret

    def get_report(self):
        return template('dashboard', self.render_dashboard(final=True))

    def get_toolserver_uptime(self):
        res = {}
        try:
            res = wapiti.get_json('http://toolserver.org/~slaporte/rs/uptime')
            res['open_queries'] = self.open_toolserver_queries
        except Exception as e:
            print 'Error getting toolserver stats:', e
        return res

    def get_toolserver_openlog(self):
        res = {}
        try:
            res = wapiti.get_json('http://toolserver.org/~slaporte/rs/openlog')
        except Exception as e:
            print 'Error getting toolserver stats:', e
        return res.get('openlog', 0)

    def send_toolserver_log(self, action, start_time=0):
        params = {'action': action, 'hostname': self.host_machine, 'params': self.start_cmd, 'start_time': start_time}
        try:
            wapiti.get_url('http://toolserver.org/~slaporte/rs/writelog/', params=params)
        except Exception as e:
            print 'Error logging:', e

    def render_dashboard(self, final=False):
        ret = self.get_dict()
        if final:
            ret['toolserver_final'] = self.get_toolserver_uptime()
            self.send_toolserver_log('complete', start_time=self.start_time)
        else:
            ret['toolserver_final'] = False
        return ret

    def get_report(self):
        return template('dashboard', self.render_dashboard())

    def serve_static(self, filepath):
        from os.path import dirname
        asset_dir = dirname(__file__) + '/assets'
        return static_file(filepath, root=asset_dir)
