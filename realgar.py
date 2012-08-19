import gevent
from gevent.pool import Pool
from gevent import monkey
monkey.patch_all()

import time
import re
import itertools
import requests
import json

from collections import namedtuple
from functools import partial

from progress import ProgressMeter

API_URL = "http://en.wikipedia.org/w/api.php"
DEFAULT_CONC     = 100
DEFAULT_PER_CALL = 4
DEFAULT_TIMEOUT  = 30


class WikiException(Exception): pass
CategoryMember = namedtuple("CategoryMember", "page_id, ns, title")
Page = namedtuple("Page", "title, req_title, namespace, page_id, rev_id, rev_text, is_parsed, fetch_date, fetch_duration")


def api_req(action, params=None, raise_exc=True, **kwargs):
    all_params = {'format': 'json',
                  'servedby': 'true'}
    all_params.update(kwargs)
    all_params.update(params)
    all_params['action'] = action

    resp = requests.Response()
    resp.results = None
    try:
        if action == 'edit':
            resp = requests.post(API_URL, params=all_params)
        else:
            resp = requests.get(API_URL, params=all_params)

    except Exception as e:
        if raise_exc:
            raise
        else:
            resp.error = e
            resp.results = None
            return resp

    try:
        resp.results = json.loads(resp.text)
        resp.servedby = resp.results.get('servedby')
        # TODO: warnings?
    except Exception as e:
        if raise_exc:
            raise
        else:
            resp.error = e
            resp.results = None
            resp.servedby = None
            return resp

    mw_error = resp.headers.get('MediaWiki-API-Error')
    if mw_error:
        error_str = mw_error
        error_obj = resp.results.get('error')
        if error_obj and error_obj.get('info'):
            error_str += ' ' + error_obj.get('info')
        if raise_exc:
            raise WikiException(error_str)
        else:
            resp.error = error_str
            return resp

    return resp


def get_category(cat_name, count=500, cont_str=""):
    ret = []
    if not cat_name.startswith('Category:'):
        cat_name = 'Category:'+cat_name
    while len(ret) < count and cont_str is not None:
        cur_count = min(count - len(ret), 500)
        params = {'list':       'categorymembers',
                  'cmtitle':    cat_name,
                  'prop':       'info',
                  'cmlimit':    cur_count,
                  'cmcontinue': cont_str}
        resp = api_req('query', params)
        try:
            qres = resp.results['query']
        except:
            print resp.error # log
            raise
        ret.extend([ CategoryMember(page_id=cm['pageid'],
                                    ns    =cm['ns'],
                                    title =cm['title'])
                     for cm in qres['categorymembers']
                     if cm.get('pageid') ])
        try:
            cont_str = resp.results['query-continue']['categorymembers']['cmcontinue']
        except:
            cont_str = None

    return ret

def get_articles_by_title(titles, **kwargs):
    return get_articles(titles=titles, **kwargs)

def get_articles(page_ids=None, titles=None,
    parsed=True, follow_redirects=False, **kwargs):
    ret = []
    params = {'prop':   'revisions',
              'rvprop': 'content|ids'}

    if page_ids:
        if not isinstance(page_ids, basestring):
            try:
                page_ids = "|".join([str(p) for p in page_ids])
            except:
                pass
        params['pageids'] = str(page_ids)
    elif titles:
        if not isinstance(titles, basestring):
            try:
                titles = "|".join([unicode(t) for t in titles])
            except:
                print "Couldn't join: ", repr(titles)
        params['titles'] = titles
    else:
        raise Exception('You need to pass in a page id or a title.')

    if parsed:
        params['rvparse'] = 'true'
    if follow_redirects:
        params['redirects'] = 'true'

    fetch_start_time = time.time()
    parse_resp = api_req('query', params, **kwargs)
    if parse_resp.results:
        try:
            pages = parse_resp.results['query']['pages'].values()
            redirect_list = parse_resp.results['query'].get('redirects', [])
        except:
            print "Couldn't get_articles() with params: ", params
            print 'URL:', parse_resp.url
            return ret

        redirects = dict([(r['to'], r['from']) for r in redirect_list])
        # this isn't perfect since multiple pages might redirect to the same page
        for page in pages:
            if not page.get('pageid') or not page.get('title'):
                continue
            title = page['title']
            pa = Page( title = title,
                       req_title = redirects.get(title, title),
                       namespace = page['ns'],
                       page_id = page['pageid'],
                       rev_id = page['revisions'][0]['revid'],
                       rev_text = page['revisions'][0]['*'],
                       is_parsed = parsed,
                       fetch_date = fetch_start_time,
                       fetch_duration = time.time() - fetch_start_time)
            ret.append(pa)
    return ret


def get_backlinks(title, **kwargs):
    params = {'list': 'backlinks',
              'bltitle': title,
              'bllimit': 500,  # TODO
              'blnamespace': 0
              }

    return api_req('query', params).results['query']['backlinks']


def get_feedback_stats(title, page_id, **kwargs):
    params = {'list': 'articlefeedback',
              'afpageid': page_id
              }
    # no ratings entry in the json means there are no ratings. if any of the other keys are missing
    # that's an error.
    return api_req('query', params).results['query']['articlefeedback'][0].get('ratings', [])


def chunked_pimap(func, iterable, concurrency=DEFAULT_CONC, chunk_size=DEFAULT_PER_CALL, **kwargs):
    func = partial(func, **kwargs)
    chunked = (iterable[i:i + chunk_size]
               for i in xrange(0, len(iterable), chunk_size))
    pool = Pool(concurrency)
    return pool.imap_unordered(func, chunked)
