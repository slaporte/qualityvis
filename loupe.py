from optparse import OptionParser

import time
import gevent
import wapiti

DEFAULT_CAT = "Featured articles that have appeared on the main page"
DEFAULT_LIMIT = 100
DEFAULT_CONC  = 100
DEFAULT_PER_CALL = 1  # TODO: make a configurable dictionary of chunk sizes
DEFAULT_TIMEOUT = 30
ALL = 20000

from inputs.backlinks import Backlinks
from inputs.feedback import FeedbackV4
from inputs.dom import DOM
from inputs.google import GoogleNews
from inputs.google import GoogleSearch
from inputs.wikitrust import Wikitrust
from inputs.grokse import PageViews
from inputs.revisions import Revisions
from inputs.assessment import Assessment

DEFAULT_INPUTS = [Backlinks, FeedbackV4, DOM, GoogleNews, GoogleSearch, Wikitrust, PageViews, Revisions, Assessment]


limits = {  # Backlinks: 100,
            # FeedbackV4: 100,
          DOM: 40,
          Revisions: 20,
          Assessment: 20}


class FancyInputPool(gevent.pool.Pool):
    def __init__(self, limits, *args, **kwargs):
        self.limits = limits if limits is not None else {}
        self.pools = {}
        super(FancyInputPool, self).__init__(*args, **kwargs)

    def add(self, grn, *args, **kwargs):
        grn_type = type(grn)
        limit = self.limits.get(grn_type)
        pool  = self.pools.get(grn_type)
        if pool is None:
            # print 'Creating pool for', grn_type
            self.pools[grn_type] = pool = gevent.pool.Pool(limit)
        super(FancyInputPool, self).add(grn)
        pool.add(grn)
        # print 'Added greenlet for', grn_type


class ArticleLoupe(object):
    def __init__(self, title, page_id, input_classes=None, input_pool=None):
        self.title = title
        self.page_id = page_id
        if input_classes is None:
            input_classes = DEFAULT_INPUTS
        self.inputs = [i(title   = self.title,
                         page_id = self.page_id) for i in input_classes]
        if input_pool is None:
            input_pool = gevent.pool.Pool()  # might as well be a set() for how we use it
        self.input_pool = input_pool
        self._int_input_pool = gevent.pool.Pool()
        self.results = {}
        self.fetch_results = {}

        self.start_time = time.time()  # need more fine-grained timing
        self._comp_inputs_count = 0

    def process_inputs(self):
        for i in self.inputs:
            i.link(self._comp_hook)
            self._int_input_pool.add(i)
            self.input_pool.start(i)
        self._int_input_pool.join()
        return self

    def _comp_hook(self, grnlt, **kwargs):
        self._comp_inputs_count += 1
        self.results.update(grnlt.results)

    @property
    def is_complete(self):
        #return len(self.results) == sum([len(i.stats) for i in self.inputs])
        return len(self.inputs) == self._comp_inputs_count

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
    results = []
    loupe_pool = gevent.pool.Pool(20)

    create_i = 0

    def loupe_on_complete(grnlt):
        loupe = grnlt.value
        results.append(loupe.results)
        kwargs = {'cr_i': loupe.create_i,
                  'co_i': len(results),
                  'count': len(cat_mems),
                  'title': loupe.title,
                  'dur': time.time() - loupe.start_time}
        log_msg = u'#{co_i}/{count} (#{cr_i}) "{title}" took {dur} seconds'.format(**kwargs)
        print log_msg
        if kwargs.get('debug'):
            loupes.append(loupe)

    fancy_pool = FancyInputPool(limits)
    for cm in cat_mems:
        al = ArticleLoupe(cm.title, cm.page_id, input_pool=fancy_pool)
        create_i += 1
        al.create_i = create_i
        loupe_pool.spawn(al.process_inputs).link(loupe_on_complete)
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

if __name__ == '__main__':
    opts, args = parse_args()
    evaluate_category(**opts.__dict__)
