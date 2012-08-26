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
DEFAULT_TIMEOUT  = 15


class WikiException(Exception): pass
CategoryMember = namedtuple("CategoryMember", "page_id, ns, title")
Page = namedtuple("Page", "title, req_title, namespace, page_id, rev_id, rev_text, is_parsed, fetch_date, fetch_duration")


def api_req(action, params=None, raise_exc=True, **kwargs):
    all_params = {'format': 'json',
                  'servedby': 'true'}
    all_params.update(kwargs)
    all_params.update(params)
    all_params['action'] = action

    headers = {'accept-encoding': 'gzip'}

    resp = requests.Response()
    resp.results = None
    try:
        if action == 'edit':
            resp = requests.post(API_URL, params=all_params, headers=headers, timeout=DEFAULT_TIMEOUT)
        else:
            resp = requests.get(API_URL, params=all_params, headers=headers, timeout=DEFAULT_TIMEOUT)

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


def get_category_old(cat_name, count=500, cont_str=""):
    ret = []
    if not cat_name.startswith('Category:'):
        cat_name = 'Category:' + cat_name
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
            print resp.error  # log
            raise
        ret.extend([CategoryMember(page_id=cm['pageid'],
                                   ns     =cm['ns'],
                                   title  =cm['title'])
                     for cm in qres['categorymembers']
                     if cm.get('pageid')])
        try:
            cont_str = resp.results['query-continue']['categorymembers']['cmcontinue']
        except:
            cont_str = None

    return ret

"""
http://en.wikipedia.org/w/api.php?action=query&generator=categorymembers
&gcmtitle=Category:Featured_articles_that_have_appeared_on_the_main_page
&prop=info&inprop=subjectid&format=json
"""


def get_category(cat_name, count=500, to_zero_ns=False, cont_str=""):
    ret = []
    if not cat_name.startswith('Category:'):
        cat_name = 'Category:' + cat_name
    while len(ret) < count and cont_str is not None:
        cur_count = min(count - len(ret), 500)
        params = {'generator': 'categorymembers',
                  'gcmtitle':   cat_name,
                  'prop':       'info',
                  'inprop':     'title|pageid|ns|subjectid',
                  'gcmlimit':    cur_count,
                  'gcmcontinue': cont_str}
        resp = api_req('query', params)
        try:
            qres = resp.results['query']
        except:
            print resp.error  # log
            raise
        for k, cm in qres['pages'].iteritems():
            if not cm.get('pageid'):
                continue
            namespace = cm['ns']
            if namespace != 0 and to_zero_ns:  # non-Main/zero namespace
                try:
                    _, _, title = cm['title'].partition(':')
                    page_id = cm['subjectid']
                    namespace = 0
                except KeyError as e:
                    continue  # TODO: log
            else:
                title = cm['title']
                page_id = cm['pageid']

            ret.append(CategoryMember(title = title,
                                      page_id = page_id,
                                      ns = namespace))
        try:
            cont_str = resp.results['query-continue']['categorymembers']['gcmcontinue']
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

def get_talk_page(title):
    params = {'prop': 'revisions',
              'titles': 'Talk:' + title,
              'rvprop': 'content',
             }
    return api_req('query', params).results['query']['pages'].values()[0]['revisions'][0]['*']


def get_backlinks(title, **kwargs):
    params = {'list': 'backlinks',
              'bltitle': title,
              'bllimit': 500,  # TODO
              'blnamespace': 0
              }

    return api_req('query', params).results['query']['backlinks']


def get_langlinks(title, **kwargs):
    params = {'prop': 'langlinks',
              'titles': title,
              'lllimit': 500,  # TODO?
              }
    query_results = api_req('query', params).results['query']['pages'].values()[0]['langlinks']
    ret = [link.get('lang') for link in query_results if link.get('lang')]
    return ret


def get_feedback_stats(page_id, **kwargs):
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
