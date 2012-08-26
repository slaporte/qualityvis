import bottle
from bottle import Bottle, run

import gevent
from gevent.threadpool import ThreadPool

# ws_pool.spawn(run, host='0.0.0.0', port=1870, server='gevent')

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


class LoupeDashboard(Bottle):

    def __init__(self, loupe_pool, results, *args, **kwargs):
        super(LoupeDashboard, self).__init__(*args, **kwargs)
        self.loupe_pool = loupe_pool
        self.results = results
        self.tpool = None
        self.route('/', callback=self.render_dashboard)

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

    def get_dict(self):
        return {'in_progress_count': len(self.loupe_pool),
                'res_count': len(self.results)}

    def render_dashboard(self):
        return self.get_dict()
