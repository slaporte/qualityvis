import time
import bottle
from bottle import Bottle, JSONPlugin, run

import gevent
from gevent.threadpool import ThreadPool

from functools import partial
better_dumps = partial(bottle.json_dumps, indent=2,
    sort_keys=True, default=repr)

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 1870
DEFAULT_SERVER = 'gevent'


def find_port(host=DEFAULT_HOST, start_port=DEFAULT_PORT, end_port=None):
    import socket
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

# TODO: add ortellius load to meta
import sys
import socket
class LoupeDashboard(Bottle):

    def __init__(self, loupe_pool, results, *args, **kwargs):
        super(LoupeDashboard, self).__init__(*args, **kwargs)
        self.loupe_pool = loupe_pool
        self.results = results
        self.tpool = None
        self.start_time = kwargs.get('start_time') or time.time()
        self.start_cmd = kwargs.get('start_cmd') or ' '.join(sys.argv)
        self.host_machine = kwargs.get('hostname') or socket.gethostname()

        self.route('/', callback=self.render_dashboard)
        self.route('/summary', callback=self.get_summary_dict)
        self.route('/all_results', callback=self.get_all_results)
        self.uninstall(JSONPlugin)
        self.install(JSONPlugin(better_dumps))


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
        in_prog_times = dict([ (o.title, cur_time - o.times['create']) for o in self.loupe_pool ])
        ret =  {'in_progress_count': len(self.loupe_pool),
                'in_progress': in_prog_times,
                'complete_count': len(self.results),
                'success_count': success_count,
                'failure_count': failure_count }
        if with_meta:
            ret['meta'] = self.get_meta_dict()
        return ret

    def get_meta_dict(self):
        return { 'start_time': self.start_time,
                 'start_cmd': self.start_cmd,
                 'host_machine': self.host_machine }

    def get_dict(self):
        ret = {}
        ret['summary'] = self.get_summary_dict(with_meta=False)
        ret['in_progress'] = [o.get_status() for o in self.loupe_pool]
        ret['complete'] = [o.get('status') for o in self.results.values()]
        ret['meta'] = self.get_meta_dict()
        return ret

    def get_all_results(self):
        ret = {}
        ret['results'] = self.results
        return ret

    def render_dashboard(self):
        return self.get_dict()
