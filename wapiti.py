
import time
from datetime import datetime
import re
import itertools
import requests
import json
from sys import maxint

from collections import namedtuple
from functools import partial

IS_BOT = False

if IS_BOT:
    PER_CALL_LIMIT = 5000
else:
    PER_CALL_LIMIT = 500

API_URL = "http://en.wikipedia.org/w/api.php"
DEFAULT_CONC     = 100
DEFAULT_PER_CALL = 4
DEFAULT_TIMEOUT  = 15
DEFAULT_HEADERS = { 'User-Agent': 'Loupe/0.0.0 Mahmoud Hashemi makuro@gmail.com' }
DEFAULT_MAX_COUNT = maxint


class WikiException(Exception):
    pass
PageIdentifier = namedtuple("PageIdentifier", "page_id, ns, title")
Page = namedtuple("Page", "title, req_title, namespace, page_id, rev_id, rev_text, is_parsed, fetch_date, fetch_duration")
RevisionInfo = namedtuple('RevisionInfo', 'page_title, page_id, namespace, rev_id, rev_parent_id, user_text, user_id, length, time, sha1, comment, tags')


def parse_timestamp(timestamp):
    return datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%SZ')

import urllib2
import socket
socket.setdefaulttimeout(DEFAULT_TIMEOUT)
from StringIO import StringIO
import gzip


class FakeResponse(object):
    pass


def fake_requests(url, params=None, headers=None, use_gzip=True):
    ret = FakeResponse()
    full_url = url
    try:
        if params:
            url_vals = encode_url_params(params)
            full_url = url + '?' + url_vals
    except:
        pass

    if not headers:
        headers = DEFAULT_HEADERS
    if use_gzip and not headers.get('Accept-encoding'):
        headers['Accept-encoding'] = 'gzip'

    req = requests.Request(url, params=params, headers=headers, method='GET', prefetch=False)
    full_url = req.full_url  # oh lawd, usin requests to create the url for now
    req = urllib2.Request(full_url, headers=headers)
    resp = urllib2.urlopen(req)
    resp_text = resp.read()
    resp.close()
    if resp.info().get('Content-Encoding') == 'gzip':
        comp_resp_text = resp_text
        buf = StringIO(comp_resp_text)
        f = gzip.GzipFile(fileobj=buf)
        resp_text = f.read()

    ret.text = resp_text
    ret.status_code = resp.getcode()
    ret.headers = resp.headers
    return ret


def get_url(url, params=None, raise_exc=True):
    resp = FakeResponse()
    try:
        resp = fake_requests(url, params)
    except Exception as e:
        if raise_exc:
            raise
        else:
            resp.error = e
    return resp


def get_json(*args, **kwargs):
    resp = get_url(*args, **kwargs)
    return json.loads(resp.text)


def api_req(action, params=None, raise_exc=True, **kwargs):
    all_params = {'format': 'json',
                  'servedby': 'true'}
    all_params.update(kwargs)
    all_params.update(params)
    all_params['action'] = action

    headers = {'accept-encoding': 'gzip'}

    resp = FakeResponse()
    resp.results = None
    try:
        if action == 'edit':
            #TODO
            resp = requests.post(API_URL, params=all_params, headers=headers, timeout=DEFAULT_TIMEOUT)
        else:
            resp = fake_requests(API_URL, all_params)

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

    mw_error = resp.headers.getheader('MediaWiki-API-Error')
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


def api_req_old(action, params=None, raise_exc=True, **kwargs):
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


def get_category_old(cat_name, count=PER_CALL_LIMIT, cont_str=""):
    ret = []
    if not cat_name.startswith('Category:'):
        cat_name = 'Category:' + cat_name
    while len(ret) < count and cont_str is not None:
        cur_count = min(count - len(ret), PER_CALL_LIMIT)
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
        ret.extend([PageIdentifier(page_id=cm['pageid'],
                                   ns=cm['ns'],
                                   title=cm['title'])
                     for cm in qres['categorymembers']
                     if cm.get('pageid')])
        try:
            cont_str = resp.results['query-continue']['categorymembers']['cmcontinue']
        except:
            cont_str = None

    return ret


def get_category(cat_name, count=PER_CALL_LIMIT, to_zero_ns=False, cont_str=""):
    ret = []
    if not cat_name.startswith('Category:'):
        cat_name = 'Category:' + cat_name
    while len(ret) < count and cont_str is not None:
        cur_count = min(count - len(ret), PER_CALL_LIMIT)
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

            ret.append(PageIdentifier(title=title,
                                      page_id=page_id,
                                      ns=namespace))
        try:
            cont_str = resp.results['query-continue']['categorymembers']['gcmcontinue']
        except:
            cont_str = None

    return ret


# TODO: default 'limit' to infinity/all
def get_transcluded(page_title=None, page_id=None, namespaces=None, limit=PER_CALL_LIMIT, to_zero_ns=True):
    ret = []
    cont_str = ""
    params = {'generator':  'embeddedin',
              'prop':       'info',
              'inprop':     'title|pageid|ns|subjectid'}
    if page_title and page_id:
        raise ValueError('Expected one of page_title or page_id, not both.')
    elif page_title:
        params['geititle'] = page_title
    elif page_id:
        params['geipageid'] = str(page_id)
    else:
        raise ValueError('page_title and page_id cannot both be blank.')
    if namespaces is not None:
        try:
            if isinstance(namespaces, basestring):
                namespaces_str = namespaces
            else:
                namespaces_str = '|'.join([str(int(n)) for n in namespaces])
        except TypeError:
            namespaces_str = str(namespaces)
        params['geinamespace'] = namespaces_str
    while len(ret) < limit and cont_str is not None:
        cur_count = min(limit - len(ret), PER_CALL_LIMIT)
        params['geilimit'] = cur_count
        if cont_str:
            params['geicontinue'] = cont_str

        resp = api_req('query', params)
        try:
            qres = resp.results['query']
        except:
            print resp.error  # log
            raise
        for k, pi in qres['pages'].iteritems():
            if not pi.get('pageid'):
                continue
            ns = pi['ns']
            if ns != 0 and to_zero_ns:  # non-Main/zero namespace
                try:
                    _, _, title = pi['title'].partition(':')
                    page_id = pi['subjectid']
                    ns = 0
                except KeyError as e:
                    continue  # TODO: log
            else:
                title = pi['title']
                page_id = pi['pageid']

            ret.append(PageIdentifier(title=title,
                                      page_id=page_id,
                                      ns=ns))
        try:
            cont_str = resp.results['query-continue']['embeddedin']['geicontinue']
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
        fetch_end_time = time.time()
        for page in pages:
            if not page.get('pageid') or not page.get('title'):
                continue
            title = page['title']
            pa = Page( title=title,
                       req_title=redirects.get(title, title),
                       namespace=page['ns'],
                       page_id=page['pageid'],
                       rev_id=page['revisions'][0]['revid'],
                       rev_text=page['revisions'][0]['*'],
                       is_parsed=parsed,
                       fetch_date=fetch_start_time,
                       fetch_duration=fetch_end_time - fetch_start_time)
            ret.append(pa)
    return ret


def get_talk_page(title):
    params = {'prop': 'revisions',
              'titles': 'Talk:' + title,
              'rvprop': 'content',
             }
    return api_req('query', params).results['query']['pages'].values()[0]['revisions'][0]['*']


def get_backlinks(title, count=PER_CALL_LIMIT, limit=DEFAULT_MAX_COUNT, cont_str='', **kwargs):
    ret = []
    while len(ret) < limit and cont_str is not None:
        params = {'list': 'backlinks',
                  'bltitle': title,
                  'blnamespace': 0,
                  'bllimit': PER_CALL_LIMIT,
                  }
        if cont_str:
            params['blcontinue'] = cont_str
        resp = api_req('query', params)
        for link in resp.results['query']['backlinks']:
            ret.append(resp.results['query']['backlinks'])
        try:
            cont_str = resp.results['query-continue']['backlinks']['blcontinue']
        except:
            cont_str = None
    return ret


def get_langlinks(title, limit=DEFAULT_MAX_COUNT, cont_str='', **kwargs):
    ret = []
    while len(ret) < limit and cont_str is not None:
        params = {'prop': 'langlinks',
                  'titles': title,
                  'lllimit': PER_CALL_LIMIT,  # TODO?
                  }
        if cont_str:
            params['llcontinue'] = cont_str
        resp = api_req('query', params).results
        if resp['query']['pages'].values()[0].get('langlinks') is None:
            return []
        langs = resp['query']['pages'].values()[0].get('langlinks')
        for language in langs:
            ret.append(language['lang'])
        try:
            cont_str = resp.results['query-continue']['langlinks']['llcontinue']
        except:
            cont_str = None
    return ret


def get_interwikilinks(title, limit=DEFAULT_MAX_COUNT, cont_str='', **kwargs):
    params = {'prop': 'iwlinks',
              'titles': title,
              'iwlimit': 500,  # TODO?
              }
    try:
        query_results = api_req('query', params).results['query']['pages'].values()[0]['iwlinks']
    except KeyError:
        query_results = []
    return query_results


def get_feedback_stats(page_id, **kwargs):
    params = {'list': 'articlefeedback',
              'afpageid': page_id
              }
    # no ratings entry in the json means there are no ratings. if any of the other keys are missing
    # that's an error.
    return api_req('query', params).results['query']['articlefeedback'][0].get('ratings', [])


def get_feedbackv5_count(page_id, **kwargs):
    params = {'list': 'articlefeedbackv5-view-feedback',
              'afvfpageid': page_id,
              'afvflimit': 1
              }
    return api_req('query', params).results['articlefeedbackv5-view-feedback']['count']


def get_revision_infos(page_title=None, page_id=None, limit=PER_CALL_LIMIT, cont_str=""):
    ret = []
    params = {'prop': 'revisions',
              'rvprop': 'ids|flags|timestamp|user|userid|size|sha1|comment|tags'}
    if page_title and page_id:
        raise ValueError('Expected one of page_title or page_id, not both.')
    elif page_title:
        params['titles'] = page_title
    elif page_id:
        params['pageids'] = str(page_id)
    else:
        raise ValueError('page_title and page_id cannot both be blank.')

    resps = []
    res_count = 0
    while res_count < limit and cont_str is not None:
        cur_limit = min(limit - len(ret), PER_CALL_LIMIT)
        params['rvlimit'] = cur_limit
        if cont_str:
            params['rvcontinue'] = cont_str
        resp = api_req('query', params)
        try:
            qresp = resp.results['query']
            resps.append(qresp)

            plist = qresp['pages'].values()  # TODO: uuuugghhhhh
            if plist and not plist[0].get('missing'):
                res_count += len(plist[0]['revisions'])
        except:
            print resp.error  # log
            raise
        try:
            cont_str = resp.results['query-continue']['revisions']['rvcontinue']
        except:
            cont_str = None

    for resp in resps:
        plist = resp['pages'].values()
        if not plist or plist[0].get('missing'):
            continue
        else:
            page_dict = plist[0]
        page_title = page_dict['title']
        page_id = page_dict['pageid']
        namespace = page_dict['ns']

        for rev in page_dict.get('revisions', []):
            rev_info = RevisionInfo(page_title=page_title,
                                    page_id=page_id,
                                    namespace=namespace,
                                    rev_id=rev['revid'],
                                    rev_parent_id=rev['parentid'],
                                    user_text=rev.get('user', '!userhidden'),  # user info can be oversighted
                                    user_id=rev.get('userid', -1),
                                    time=parse_timestamp(rev['timestamp']),
                                    length=rev['size'],
                                    sha1=rev['sha1'],
                                    comment=rev.get('comment', ''),  # comments can also be oversighted
                                    tags=rev['tags'])
            ret.append(rev_info)
    return ret


def chunked_pimap(func, iterable, concurrency=DEFAULT_CONC, chunk_size=DEFAULT_PER_CALL, **kwargs):
    func = partial(func, **kwargs)
    chunked = (iterable[i:i + chunk_size]
               for i in xrange(0, len(iterable), chunk_size))
    pool = Pool(concurrency)
    return pool.imap_unordered(func, chunked)
