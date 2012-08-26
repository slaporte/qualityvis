import bottle
from bottle import Bottle, run

import gevent
from gevent.threadpool import ThreadPool

# ws_pool.spawn(run, host='0.0.0.0', port=1870, server='gevent')

DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 1870
DEFAULT_SERVER = 'gevent'


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
        kwargs['port'] = kwargs.get('port', DEFAULT_PORT)
        kwargs['server'] = kwargs.get('server', DEFAULT_SERVER)
        self.tpool.spawn(run, self, **kwargs)

    def get_dict(self):
        return {'in_progress_count': len(self.loupe_pool),
                'res_count': len(self.results)}

    def render_dashboard(self):
        return self.get_dict()
