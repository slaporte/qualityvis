from optparse import OptionParser
from itertools import chain

import time
import gevent
import realgar

DEFAULT_CAT = "Featured articles that have appeared on the main page"
DEFAULT_LIMIT = 100
DEFAULT_CONC  = 100
DEFAULT_PER_CALL = 1  # TODO: make a configurable dictionary of chunk sizes
DEFAULT_TIMEOUT = 30
ALL = 20000

from inputs.backlinks import Backlinks
from inputs.feedback import FeedbackV4
from inputs.dom import DOM
DEFAULT_INPUTS = [Backlinks, FeedbackV4, DOM]

"""
limits = {inputs.grokseStats: 5}


class FancyInputPool(object):
    def __init__(self):
        self.req_multi = {}
        pass
    def spawn(self, grn):
        if not req_multi.get(type(grn)):
            gevent.pool.Pool(limits[type(grn)])
        self.req_multi[type(grn)].start(grn)
"""


class ArticleLoupe(object):
    """
    1. Get article (text + revision id + other metadata)
    2. Run inputs, checking for loupe completeness
    3. Serialize/complete.
    """
    def __init__(self, page, inputs=None):
        self.title = page.title
        self.page_id = page.page_id
        self.rev_id = page.rev_id
        self.text = page.rev_text
        self.page = page
        if inputs is None:
            self.inputs = DEFAULT_INPUTS
        self.results = {}
        self.fetch_results = {}

        self._comp_inputs_count = 0

    def process_inputs(self):
        for i in self.inputs:
            gevent.spawn(self.process_one_input, i).link(self._comp_hook)

    def _comp_hook(self, *args, **kwargs):
        self._comp_inputs_count += 1
        if self.is_complete:
            print 'loupe created for', self.title, 'took', time.time() - self.page.fetch_date, 'seconds'

    def process_one_input(self, i):
        try:
            self.fetch_results[i] = i.fetch(title   = self.title,
                                            page_id = self.page_id,
                                            rev_id  = self.rev_id,
                                            text    = self.text)
        except Exception as e:
            # TODO: retry
            print 'Fetch failed on', self.title, 'for input', i,
            print 'with exception', repr(e)
            return
        proc_res = i.process(self.fetch_results[i])
        if isinstance(proc_res, Exception):
            print i, 'process step glubbed up on', self.title
        else:
            self.results.update(proc_res)
        return

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
    cat_mems = realgar.get_category(category, count=limit)
    cat_titles = [cm.title[5:] for cm in cat_mems if cm.title.startswith("Talk:")]
    loupes = []
    loupe_pool = gevent.pool.Pool(30)
    pages = realgar.chunked_pimap(realgar.get_articles_by_title,
                                  cat_titles,
                                  kwargs.get('concurrency', DEFAULT_CONC),
                                  kwargs.get('grouping', DEFAULT_PER_CALL))
    for p in chain.from_iterable(pages):
        al = ArticleLoupe(p)
        loupes.append(al)
        loupe_pool.spawn(al.process_inputs)
    loupe_pool.join()
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
