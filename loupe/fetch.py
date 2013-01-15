import gevent
from gevent import monkey
monkey.patch_all()
from gevent.greenlet import Greenlet
import article_list
from argparse import ArgumentParser
import logging
import time
import codecs
from collections import OrderedDict, defaultdict
import json
from lib import wapiti
from dashboard import LoupeDashboard
from inputs import DEFAULT_INPUTS, DOM, Revisions
import os

DEFAULT_CAT = "Featured articles that have appeared on the main page"
DEFAULT_LIMIT = 100
DEFAULT_CONC = 20
DEFAULT_PER_CALL = 1  # TODO: make a configurable dictionary of chunk sizes
DEFAULT_TIMEOUT = 30
ALL = 20000

DEFAULT_LIMITS = {
    # Backlinks: 100,
    # FeedbackV4: 100,
    DOM: 40,
    Revisions: 20}


def get_filename(prefix=''):
    return prefix.replace(' ', '_') + '-' + str(int(time.time()))


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
    def __init__(self, title, page_id, page_ns, input_classes=None, input_pool=None, *args, **kwargs):
        self.title = title
        self.page_id = page_id
        self.page_ns = page_ns
        if input_classes is None:
            input_classes = DEFAULT_INPUTS
        self.inputs = [i(title=self.title,
                         page_id=self.page_id) for i in input_classes]
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
        if grnlt.results:
            self.results.update(grnlt.results)
        if self.is_complete:
            self.times['complete'] = time.time()

    @property
    def durations(self):
        ret = dict([(i.class_name, i.durations) for i in self.inputs])
        try:
            ret['total'] = self.times['complete'] - self.times['create']
        except KeyError:
            ret['total'] = time.time() - self.times['create']
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
        input_statuses = dict([(i.class_name, i.status) for i in self.inputs])
        is_complete = all([i['is_complete'] for i in input_statuses.itervalues()])
        is_successful = all([i['is_successful'] for i in input_statuses.itervalues()])
        ret = {
            'durations': self.durations,
            'page_id': self.page_id,
            'title': self.title,
            'create_time': self.times['create'],
            'inputs': input_statuses,
            'is_complete': is_complete,
            'is_successful': is_successful,
        }
        ret['create_i'] = getattr(self, 'create_i', 0)
        return ret

    def get_flat_results(self):
        return flatten_dict(self.results)

class Louper(object):
    # TODO: maybe have a mode where it fills in failed stats?
    # TODO: maybe accept a config object of some sort
    def __init__(self, page_ds, **kwargs):
        self.page_ds = page_ds
        self.total_count = len(page_ds)
        try:
            self.input_classes = kwargs['inputs']
            filename = kwargs['filename']
            self.concurrency = kwargs.get('concurrency', DEFAULT_CONC)
            self.limits = kwargs.get('limits', DEFAULT_LIMITS)
            self.debug = kwargs.get('debug', False)
        except KeyError as ke:
            raise ValueError('Louper expected argument '+str(ke))

        self.output_file = codecs.open(filename, 'w', 'utf-8')
        self.loupes = [] # NOTE: only used in debug mode, uses a lot more ram
        self.results = OrderedDict()
        self.failed_stats = defaultdict(list)
        self.fetch_failures = defaultdict(list)
        self.input_pool = FancyInputPool(self.limits)
        self.loupe_pool = gevent.pool.Pool(self.concurrency)

    def run(self):
        print 'Creating Loupes for', len(self.page_ds), 'articles...'
        create_i = 0
        for pd in self.page_ds:
            al = ArticleLoupe(pd.title, pd.page_id, pd.ns, input_pool=self.input_pool, input_classes=self.input_classes)
            create_i += 1
            al.create_i = create_i
            al.link(self.on_loupe_complete)
            self.loupe_pool.start(al)
        self.loupe_pool.join()

    def on_loupe_complete(self, loupe):
        self.results[loupe.title] = loupe.to_dict()
        msg_params = {'cr_i': loupe.create_i,
                      'co_i': len(self.results),
                      'count': self.total_count,
                      'title': loupe.title,
                      'dur': time.time() - loupe.times['create']}
        log_msg = u'#{co_i}/{count} (#{cr_i}) "{title}" took {dur:.4f} seconds'.format(**msg_params)
        for inpt in loupe.inputs:
            status = inpt.status
            if not status.get('fetch_succeeded'):
                self.fetch_failures[loupe.title].append(inpt.class_name)
            for stat in status.get('failed_stats'):
                stat_failure = (inpt.class_name, stat, str(loupe.results[stat]))
                self.failed_stats[stat_failure].append(loupe.title)
        print log_msg
        #import pdb;pdb.set_trace()
        output_dict = loupe.results
        output_dict['title'] = loupe.title
        output_dict['id'] = loupe.page_id
        output_dict['ns'] = loupe.page_ns
        output_dict['times'] = loupe.times

        self.output_file.write(json.dumps(output_dict, default=str))
        self.output_file.write('\n')

        if self.debug:
            self.loupes.append(loupe)

    def close(self):
        # TODO:  might want to find a better way of doin this
        self.output_file.close()

'''
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

    parser.add_option("-R", "--recursive", dest="recursive",
                      action="store_true", default=False,
                      help="search category recursively")

    parser.add_option("-g", "--grouping", dest="grouping",
                      type="int", default=DEFAULT_PER_CALL,
                      help="how many sub-responses to request per API call")

    parser.add_option('-D', "--debug", dest="debug",
                      action="store_true", default=False,
                      help="enable debugging (and pop up pdb at the end of successful run")

    parser.add_option("-q", "--quiet", dest="verbose", action="store_false",
                      help="suppress output (TODO)")

    parser.add_option("-r", "--random", dest="random",
                      action="store_true", default=False,
                      help="get articles randomly")
    return parser.parse_args()
'''

def create_parser():
    root_parser = ArgumentParser(description='article fetch operations')
    root_parser.add_argument('--list_home', help='list lookup directory')
    add_subparsers(root_parser.add_subparsers())
    return root_parser


def add_subparsers(subparsers):
    parser_list = subparsers.add_parser('list')
    parser_list.add_argument('target_list', nargs='?',
                             help='Name of the list or list file')
    parser_list.set_defaults(func=get_list)

    parser_cat = subparsers.add_parser('category')
    parser_cat.add_argument('category_title', nargs='?',
                             help='Name of the category')
    parser_cat.add_argument('-l', '--limit', type=int, default=DEFAULT_LIMIT,
                            help='number of articles')
    parser_cat.set_defaults(func=get_category)

    parser_rand = subparsers.add_parser('random')
    parser_rand.add_argument('-l', '--limit', type=int, default=DEFAULT_LIMIT,
                            help='number of articles')
    parser_rand.set_defaults(func=get_random)

    return


@article_list.needs_alm
def get_list(alm, target_list=None, **kw):
    target_list_path = os.path.join(alm.output_path, target_list + article_list.DEFAULT_EXT)
    if target_list_path:
        al = article_list.ArticleList.from_file(target_list_path)
        titles = al.titles
        page_ds = wapiti.get_infos_by_title(titles)
        filename = target_list
        start_louper(alm, page_ds=page_ds, filename=filename)
    else:
        raise IOError('%s does not exist' % target_list_path)


def get_category(**kw):
    print 'Fetching ', kw['limit'], ' members of category ', kw['limit'], '...'
    page_ds = wapiti.get_category(kw['category_title'], count=kw['limit'], to_zero_ns=True)
    filename = get_filename(kw['category'][:15])
    start_louper(None, page_ds=page_ds, filename=filename)

def get_random(**kw):
    print 'Fetching', kw['limit'], ' random articles...'
    page_ds = wapiti.get_random(kw['limit'])
    filename = get_filename('random')
    start_louper(None, page_ds=page_ds, filename=filename)

@article_list.needs_alm
def start_louper(alm, page_ds=None, filename=None, debug=False, **kwargs):
    # TODO: more generalized path manager
    output_path = os.path.join(alm.output_path, '..', 'fetch_data')
    res_filename = os.path.join(output_path, filename + '.json')
    report_filename = os.path.join(output_path, filename + '-report.html')

    lpr = Louper(page_ds, filename=res_filename, inputs=DEFAULT_INPUTS, **kwargs)

    dash = LoupeDashboard(lpr)
    dash.run()

    try:
        lpr.run()
    finally:
        lpr.close()
        with codecs.open(report_filename, 'w', 'utf-8') as rf:
            rf.write(dash.get_report())
        if debug:
            import pdb;pdb.set_trace()


def main():
    parser = create_parser()
    args = parser.parse_args()
    kwargs = dict(args._get_kwargs())
    args.func(**kwargs)

'''
def main():
    opts, args = parse_args()
    kwargs = opts.__dict__
    # TODO: better output filenames

    if kwargs.get('random'):
        print 'Fetching ', opts.limit, ' random articles...'
        page_ds = wapiti.get_random(opts.limit)
        filename = get_filename('random')
    elif kwargs.get('recursive'):
        print 'Fetching members of category', opts.category, '...'
        page_ds = wapiti.get_category_recursive(opts.category, page_limit=opts.limit, to_zero_ns=True)
        filename = get_filename(opts.category[:15])
    else:
        print 'Fetching members of category', opts.category, '...'
        page_ds = wapiti.get_category(opts.category, count=opts.limit, to_zero_ns=True)
        filename = get_filename(opts.category[:15])

    res_filename = 'results/'+filename+'.json'
    report_filename = 'results/' + filename + '-report.html'

    lpr = Louper(page_ds, filename=res_filename, inputs=DEFAULT_INPUTS, **kwargs)

    dash = LoupeDashboard(lpr)
    dash.run()

    try:
        lpr.run()
    finally:
        lpr.close()
        with codecs.open(report_filename, 'w', 'utf-8') as rf:
            rf.write(dash.get_report())
        if kwargs.get('debug'):
            import pdb;pdb.set_trace()
'''

if __name__ == '__main__':
    main()
