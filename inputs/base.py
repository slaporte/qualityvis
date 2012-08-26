import time
from gevent.greenlet import Greenlet

class Input(Greenlet):

    retries = 3

    def __init__(self, title, page_id, *args, **kwargs):
        self.page_title = title
        self.page_id    = page_id

        self.attempts = 0
        self.fetch_results = None
        self.results = None
        self.times = {'create': time.time()}
        super(Input, self).__init__(*args, **kwargs)

    @property
    def class_name(self):
        return str(self.__class__.__name__)

    @property
    def import_name(self):
        return '.'.join((str(self.__module__), str(self.__class__.__name__)))

    @property
    def durations(self):
        ret = {}
        try:
            ret['total'] = self.times['complete'] - self.times['create']
        except:
            ret['total'] = None
        try:
            ret['fetch'] = self.times['fetch_end'] - self.times['fetch_start']
        except:
            ret['fetch'] = None
        try:
            ret['process'] = self.times['process_end'] - self.times['process_start']
        except:
            ret['process'] = None
        return ret

    def fetch(self):
        raise NotImplemented  # TODO: convert to abstract class?

    def process(self, fetch_results):
        ret = {}
        for k, func in self.stats.iteritems():
            try:
                if fetch_results:
                    res = func(fetch_results)
                else:
                    res = None
            except Exception as e:
                ret[k] = e
            else:
                ret[k] = res
        return ret

    def __call__(self):
        self.times['fetch_start'] = time.time()
        for i in range(0, self.retries):
            self.attempts += 1
            try:
                self.fetch_results = self.fetch()
            except Exception as e:
                e_msg = "Fetch failed on {i_t} input for article {p_t} ({p_id}) with exception {e}"
                e_msg = e_msg.format(p_t=self.page_title, p_id=self.page_id, i_t=self.class_name, e=repr(e))
                print e_msg
            else:
                break
            finally:
                self.times['fetch_end'] = self.times['process_start'] = time.time()

        proc_res = self.process(self.fetch_results)
        self.results = proc_res
        if isinstance(proc_res, Exception):
            print type(self), 'process step glubbed up on', self.page_title
        self.times['process_end'] = self.times['complete'] = time.time()
        return proc_res

    _run = __call__


class WikipediaInput(Input):
    pass

def get_url(url, params=None, raise_exc=True):
    import requests
    if params is None:
        params = {}
    headers = {'accept-encoding': 'gzip'}
    resp = requests.Response()
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
    except Exception as e:
        if raise_exc:
            raise
        else:
            resp.error = e
    return resp


def get_json(*args, **kwargs):
    import json
    resp = get_url(*args, **kwargs)
    return json.loads(resp.text)
