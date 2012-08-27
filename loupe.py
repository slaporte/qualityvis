from optparse import OptionParser
import logging
import time
from collections import OrderedDict

import gevent
from gevent.greenlet import Greenlet

import wapiti

DEFAULT_CAT = "Featured articles that have appeared on the main page"
DEFAULT_LIMIT = 100
DEFAULT_CONC  = 20
DEFAULT_PER_CALL = 1  # TODO: make a configurable dictionary of chunk sizes
DEFAULT_TIMEOUT = 30
ALL = 20000

from inputs import DEFAULT_INPUTS, DOM, Revisions, Assessment
from dashboard import LoupeDashboard

limits = {  # Backlinks: 100,
            # FeedbackV4: 100,
          DOM: 40,
          Revisions: 20,
          Assessment: 20}


class FancyInputPool(gevent.pool.Pool):
    def __init__(self, limits, *args, **kwargs):
        self.limits = limits if limits is not None else {}
        self.pools = {}  # will be lazily initialized in add()
        super(FancyInputPool, self).__init__(*args, **kwargs)

    def add(self, grn, *args, **kwargs):
        super(FancyInputPool, self).add(grn)
        for in_type, limit in self.limits.iteritems():
            if isinstance(grn, in_type):
                pool = self.pools.get(in_type)
                if pool is None:
                    self.pools[in_type] = pool = gevent.pool.Pool(limit)
                pool.add(grn)
        return


class ArticleLoupe(Greenlet):
    def __init__(self, title, page_id, input_classes=None, input_pool=None, *args, **kwargs):
        self.title = title
        self.page_id = page_id
        if input_classes is None:
            input_classes = DEFAULT_INPUTS
        self.inputs = [i(title   = self.title,
                         page_id = self.page_id) for i in input_classes]
        if input_pool is None:
            input_pool = gevent.pool.Pool()
        self.input_pool = input_pool
        self._int_input_pool = gevent.pool.Pool()
        self.results = {}
        self.fetch_results = {}

        self.times = {'create': time.time()}
        self._comp_inputs_count = 0

        super(ArticleLoupe, self).__init__(*args, **kwargs)

    def process_inputs(self):
        for i in self.inputs:
            i.link(self._comp_hook)
            self._int_input_pool.add(i)
            self.input_pool.start(i)
        self._int_input_pool.join()
        return self

    def _run(self):
        return self.process_inputs()

    #_run = process_inputs  # pretty much all you need to make a Greenlet

    def _comp_hook(self, grnlt, **kwargs):
        self._comp_inputs_count += 1
        self.results.update(grnlt.results)
        if self.is_complete:
            self.times['complete'] = time.time()

    @property
    def durations(self):
        ret = dict([(i.class_name, i.durations) for i in self.inputs])
        try:
            ret['total'] = self.times['complete'] - self.times['create']
        except KeyError:
            pass
        return ret

    @property
    def is_complete(self):
        #return len(self.results) == sum([len(i.stats) for i in self.inputs])
        return len(self.inputs) == self._comp_inputs_count

    def to_dict(self):
        ret = {}
        ret.update(self.results)
        ret['status'] = self.get_status()
        return ret

    def get_status(self):
        input_statuses = dict([ (i.class_name, i.status) for i in self.inputs ])
        is_complete = all([ i['is_complete'] for i in input_statuses.itervalues() ])
        is_successful = all([ i['is_successful'] for i in input_statuses.itervalues() ])
        ret = {
            'durations': self.durations,
            'page_id': self.page_id,
            'title': self.title,
            'create_time': self.times['create'],
            'inputs': input_statuses,
            'is_complete': is_complete,
            'is_successful': is_successful,
        }
        return ret


    def get_flat_results(self):
        return flatten_dict(self.results)


def flatten_dict(root, prefix_keys=True):
    dicts = [([], root)]
    ret = {}
    seen = set()
    for path, d in dicts:
        if id(d) in seen:
            continue
        seen.add(id(d))
        for k, v in d.items():
            new_path = path + [k]
            prefix = '_'.join(new_path) if prefix_keys else k
            if hasattr(v, 'items'):
                dicts.append((new_path, v))
            else:
                ret[prefix] = v
    return ret

def evaluate_category(category, limit, **kwargs):
    print 'Fetching members of category', str(category) + '...'
    cat_mems = wapiti.get_category(category, count=limit, to_zero_ns=True)
    print 'Creating Loupes for', len(cat_mems), 'articles in', str(category) + '...'
    loupes = []  # NOTE: only used in debug mode, uses a lot more ram
    results = OrderedDict()
    loupe_pool = gevent.pool.Pool(kwargs.get('concurrency', DEFAULT_CONC))

    create_i = 0

    dash = LoupeDashboard(loupe_pool, results)
    dash.run()

    def loupe_on_complete(grnlt):
        loupe = grnlt

        results[loupe.title] = loupe.to_dict()

        msg_params = {'cr_i': loupe.create_i,
                      'co_i': len(results),
                      'count': len(cat_mems),
                      'title': loupe.title,
                      'dur': time.time() - loupe.times['create']}
        log_msg = u'#{co_i}/{count} (#{cr_i}) "{title}" took {dur:.4f} seconds'.format(**msg_params)
        print log_msg
        if kwargs.get('debug'):
            loupes.append(loupe)

    fancy_pool = FancyInputPool(limits)
    for cm in cat_mems:
        al = ArticleLoupe(cm.title, cm.page_id, input_pool=fancy_pool)
        create_i += 1
        al.create_i = create_i
        al.link(loupe_on_complete)
        loupe_pool.start(al)
    loupe_pool.join()

    if kwargs.get('debug'):
        import pdb;pdb.set_trace()

# check for errors:
# [al.title for al in loupes if any([isinstance(r, Exception) for r in al.results.values()])]

def parse_args():
    parser = OptionParser()
    parser.add_option("-l", "--limit", dest="limit",
                      type="int", default=DEFAULT_LIMIT,
                      help="max number of articles to evaluate")

    parser.add_option("-C", "--category", dest="category",
                      type="string", default=DEFAULT_CAT,
                      help="category to search for ArticleHistory templates")

    parser.add_option("-c", "--concurrency", dest="concurrency",
                      type="int", default=DEFAULT_CONC,
                      help="concurrency factor to use when querying the"
                      "Wikipedia API (simultaneous requests)")

    parser.add_option("-g", "--grouping", dest="grouping",
                      type="int", default=DEFAULT_PER_CALL,
                      help="how many sub-responses to request per API call")

    parser.add_option('-D', "--debug", dest="debug",
                      action="store_true", default=False,
                      help="enable debugging (and pop up pdb at the end of successful run")

    parser.add_option("-q", "--quiet", dest="verbose", action="store_false",
                      help="suppress output (TODO)")
    return parser.parse_args()

from dashboard import LoupeDashboard

if __name__ == '__main__':
    opts, args = parse_args()
    evaluate_category(**opts.__dict__)
