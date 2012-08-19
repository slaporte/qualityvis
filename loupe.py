from optparse import OptionParser
from itertools import chain

import time
import gevent
import realgar

DEFAULT_CAT = "Featured articles that have appeared on the main page"
DEFAULT_LIMIT = 100
DEFAULT_CONC  = 100
DEFAULT_PER_CALL = 1 # TODO: make a configurable dictionary of chunk sizes
DEFAULT_TIMEOUT = 30
ALL = 20000

#from inputs import dom_stats, grokse_stats

#DEFAULT_INPUTS = [dom_stats, grokse_stats]
DEFAULT_INPUTS = []
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


class Input(object):
    source = None

    @classmethod
    def fetch(cls, title, rev_id, page_id, dom):
        return cls.source(title, rev_id, page_id, dom)

    @classmethod
    def process(cls, fetch_results):
        ret = {}
        for k, func in cls.stats.items():
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


class IncomingLinks(Input):
    fetch = realgar.get_incoming_links
    fetch = staticmethod(fetch)

    stats = {
        'incoming_links': lambda f_res: len(f_res),
    }


def get_feedback_stats(title, page_id, **kwargs):
    params = {'list': 'articlefeedback',
              'afpageid': page_id
              }
    # no ratings entry in the json means there are no ratings. if any of the other keys are missing
    # that's an error.
    return realgar.api_req('query', params).results['query']['articlefeedback'][0].get('ratings', [])


class FeedbackV4(Input):
    fetch = get_feedback_stats
    fetch = staticmethod(fetch)

    stats = {
        'fb_trustworthy': lambda f: f[0]['total'] / f[0]['count'] if f[0]['count'] else 0,
        'fb_objective': lambda f: f[1]['total'] / f[1]['count'] if f[1]['count'] else 0,
        'fb_complete': lambda f: f[2]['total'] / f[2]['count'] if f[2]['count'] else 0,
        'fb_wellwritten': lambda f: f[3]['total'] / f[3]['count'] if f[3]['count'] else 0,
        'fb_count_trustworthy': lambda f: f[0]['count'],
        'fb_count_objective': lambda f: f[1]['count'],
        'fb_count_complete': lambda f: f[2]['count'],
        'fb_count_wellwritten': lambda f: f[3]['count'],
        'fb_count_total': lambda f: sum([x['count'] for x in f]),
        'fb_countall_total': lambda f: sum([x['countall'] for x in f])
    }

DEFAULT_INPUTS = [IncomingLinks, FeedbackV4]

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

    def process_inputs(self):
        for i in self.inputs:
            gevent.spawn(self.process_one_input, i).link(self._comp_hook)

    def _comp_hook(self, *args, **kwargs):
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
        return len(self.results) == sum([len(i.stats) for i in self.inputs])


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
