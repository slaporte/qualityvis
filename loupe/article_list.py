from __future__ import unicode_literals

import os
import json
import codecs
from functools import wraps
from datetime import datetime
from collections import namedtuple
from argparse import ArgumentParser

from lib import wapiti

DEFAULT_LIMIT = 100
DEFAULT_SOURCE = 'enwiki'
FORMAT = 'v1'

###########
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
DEFAULT_EXT = '.txt'

ArticleIdentifier = namedtuple('ArticleIdentifier', 'name source')


class ArticleListManager(object):
    def __init__(self, search_path=None):
        if search_path is None:
            default_path = os.getenv('ARTICLE_LIST_HOME') or os.getcwd()
            search_path = [default_path]
        self.search_path = search_path
        self._output_path = None

    def lookup(self, filename):
        if not filename:
            return None
        for search_dir in self.search_path:
            if os.path.isdir(search_dir):
                if os.path.isfile(filename):
                    return os.path.join(search_dir, filename)
                elif os.path.isfile(filename + DEFAULT_EXT):
                    return os.path.join(search_dir, filename + DEFAULT_EXT)
        if os.path.isfile(filename):
            return filename
        return None

    def get_full_list(self):
        ret = []
        for search_dir in self.search_path:
            try:
                ret.extend([fn for fn in os.listdir(search_dir)
                            if fn.endswith(DEFAULT_EXT)])
            except IOError:
                pass
        return ret

    @property
    def output_path(self):
        if self._output_path:
            return self._output_path
        else:
            return self.search_path[0]


class ArticleList(object):
    def __init__(self, actions=None, comments=None, file_metadata=None):
        if actions is None:
            actions = []
        self.actions = actions
        self.comments = comments or {}
        self.file_metadata = file_metadata or {}

    @classmethod
    def from_file(cls, path):
        with codecs.open(path, 'r', encoding='utf-8') as f:
            f_contents = f.read()
        return cls.from_string(f_contents)

    @classmethod
    def from_string(cls, contents):
        actions, comments, file_metadata = al_parse(contents)
        return cls(actions, comments, file_metadata)

    @property
    def next_action_id(self):
        return len(self.actions) + 1

    @property
    def file_metadata_string(self):
        date = datetime.utcnow()
        created = self.file_metadata.get('created',
                                         datetime.strftime(date, DATE_FORMAT))
        name = self.file_metadata.get('name', '(unknown)')
        format = self.file_metadata.get('format', FORMAT)
        tmpl = '# created={created} name={name} format={format}'
        return tmpl.format(created=created, name=name, format=format)

    def include(self, article_list, term=None, source=None):
        self.do_action('include', article_list, term=term, source=source)

    def exclude(self, article_list, term=None, source=None):
        self.do_action('exclude', article_list, term=term, source=source)

    def xor(self):
        # todo
        pass

    def do_action(self, action, article_list, term=None, source=None):
        newact = ListAction(id=self.next_action_id,
                            action=action,
                            articles=article_list,
                            term=term,
                            source=source)
        self.actions.append(newact)

    def get_articles(self):
        article_set = set()
        for action in self.actions:
            action_articles = set([ArticleIdentifier(a, action.source)
                                    for a in action.articles])
            if action.action == 'include':
                article_set = article_set.union(action_articles)
            elif action.action == 'exclude':
                article_set = article_set - action_articles
            else:
                raise Exception('wut')
        return article_set

    def to_string(self):
        #todo: file metadata
        output = []
        i = 0
        for action in self.actions:
            meta_str = action.get_meta_string()
            output.append(meta_str)
            output += action.articles

        ret = [self.file_metadata_string]
        ai = 0
        for i in xrange(len(self.comments) + len(output)):
            if self.comments.get(i) is not None:
                ret.append(self.comments[i])
            else:
                ret.append(output[ai])
                ai += 1
        return '\n'.join(ret)

    def write(self, path):
        output = self.to_string()
        with codecs.open(path, 'w', encoding='utf-8') as f:
            f.write(output)


class ListAction(object):
    metadata_attrs = ('id', 'action', 'term', 'date', 'source')
    valid_actions = ('include', 'exclude')

    def __init__(self, id, action, articles=None, term=None, date=None, source=None, extra_attrs=None):
        self.id = id
        self.action = action
        self.term = term or '(custom)'
        if date is None:
            date = datetime.utcnow()
        elif isinstance(date, basestring):
            date = datetime.strptime(date, DATE_FORMAT)
        elif not hasattr(date, 'strftime'):
            raise ValueError('expected date-like object for argument "date"')
        self.date = date
        self.source = source or DEFAULT_SOURCE
        self.extra_attrs = extra_attrs or {}
        if articles is None:
            articles = []
        self.articles = articles

    @classmethod
    def from_meta_string(cls, string, default_id=1, default_action='include'):
        metadata = parse_meta_string(string)
        extra_attrs = {}
        kw = {}
        for k in metadata:
            if k in cls.metadata_attrs:
                kw[k] = metadata[k]
            else:
                extra_attrs[k] = metadata[k]
        if not kw:
            raise ValueError('no metadata found')
        if not kw.get('id'):
            kw['id'] = default_id
        if not kw.get('action'):
            kw['action'] = default_action
        if kw['action'] not in cls.valid_actions:
            raise ValueError('unrecognized action: ' + str(kw['action']))
        kw['extra_attrs'] = extra_attrs
        return cls(**kw)

    def get_meta_string(self):
        ret = '# '
        for attr in self.metadata_attrs:
            attrval = getattr(self, attr)
            if hasattr(attrval, 'strftime'):
                attrval = attrval.strftime(DATE_FORMAT)
            ret += str(attr) + '=' + str(attrval) + ' '
        return ret


def parse_meta_string(string_orig):
    ret = {}
    string = string_orig.strip().lstrip('#').strip()
    parts = string.split()
    for part in parts:
        k, _, v = part.partition('=')
        ret[k] = v
    return ret


def al_parse(contents):
    lines = contents.splitlines()
    file_metadata = ''
    cur_action = None
    ret_actions = []
    comments = {}
    for i, orig_line in enumerate(lines):
        line = orig_line.strip()
        if not line:
            comments[i] = ''
            continue
        if line.startswith("#"):
            try:
                list_action = ListAction.from_meta_string(line,
                                                          default_id=len(ret_actions)+1)
            except ValueError:
                if not ret_actions:
                    try:
                        file_metadata = parse_meta_string(line)
                        continue
                    except:
                        pass
                comments[i] = line
            else:
                cur_action = list_action
                ret_actions.append(list_action)
        else:
            if not cur_action:
                cur_action = ListAction(1, 'include')
                ret_actions.append(cur_action)
            cur_action.articles.append(line)
    return ret_actions, comments, file_metadata


def needs_alm(f):
    # currently depends on keyword arguments to work
    @wraps(f)
    def decorated(alm=None, *a, **kw):
        if alm is not None:
            return f(alm=alm, *a, **kw)
        list_home = kw.get('list_home')
        list_home = list_home or os.getenv('ARTICLE_LIST_HOME') or os.getcwd()
        if not os.path.isdir(list_home):
            raise IOError('not a directory: ' + str(list_home))
        alm = ArticleListManager(search_path=[list_home])
        kw['alm'] = alm
        return f(*a, **kw)
    return decorated


@needs_alm
def show(alm, target_list=None, **kw):
    target_list_path = alm.lookup(target_list)
    if target_list_path:
        a_list = ArticleList.from_file(target_list_path)
        print json.dumps(a_list.file_metadata, indent=4)
        print '\nTotal articles: ', len(a_list.get_articles()), '\n'
    elif target_list is None:
        print 'Article lists in ', repr(alm.search_path)
        print '\n'.join(alm.get_full_list())


@needs_alm
def create(alm, target_list, **kw):
    existent = alm.lookup(target_list)
    if existent:
        raise IOError('list already exists: %s' % target_list)
    if not target_list or '.' in target_list:
        raise ValueError('expected non-empty string without dots')

    out_filename = os.path.join(alm.output_path, target_list + DEFAULT_EXT)
    codecs.open(out_filename, 'w', encoding='utf-8').close()
    print 'Created article list %s' % out_filename


@needs_alm
def list_op(alm, op_name, search_target, target_list, limit=DEFAULT_LIMIT, recursive=False, **kw):
    target_list_path = alm.lookup(target_list)
    if not target_list_path:
        raise IOError('file not found for target list: %s' % target_list)
    a_list = ArticleList.from_file(target_list_path)
    if search_target.startswith('Category:'):
        article_list = wapiti.get_category_recursive(search_target, page_limit=limit, to_zero_ns=True)
    elif search_target.startswith('Template:'):
        article_list = wapiti.get_transcluded(page_title=search_target, limit=limit, to_zero_ns=True)

    if op_name == 'include':
        a_list.include([a[2] for a in article_list], source=DEFAULT_SOURCE, term=search_target)
        a_list.write(target_list_path)
    elif op_name == 'exclude':
        a_list.exclude([a[2] for a in article_list], source=DEFAULT_SOURCE, term=search_target)
        a_list.write(target_list_path)
    # TODO: summary
    # TODO: tests
    # TODO: convert this function to a decorator thing


def create_parser():
    root_parser = ArgumentParser(description='article list operations')
    root_parser.add_argument('--list_home', help='list lookup directory')
    add_subparsers(root_parser.add_subparsers())
    return root_parser


def add_subparsers(subparsers):
    parser_show = subparsers.add_parser('show')
    parser_show.add_argument('target_list', nargs='?',
                             help='Name of the list or list file')
    parser_show.set_defaults(func=show)

    parser_create = subparsers.add_parser('create')
    parser_create.add_argument('target_list',
                               help='name of the list or list file')
    parser_create.set_defaults(func=create)

    op_parser = ArgumentParser(description='parses generic search op args.',
                               add_help=False)
    op_parser.add_argument('search_target',
                           help='article, category, or template')
    op_parser.add_argument('target_list',
                           help='name or path of article list')
    op_parser.add_argument('--limit', '-l', type=int,
                           default=DEFAULT_LIMIT,
                           help='number of articles')
    op_parser.add_argument('--recursive', '-R', action='store_true',
                           help='Fetch recursively')
    op_parser.set_defaults(func=list_op)

    parser_include = subparsers.add_parser('include', parents=[op_parser])
    parser_include.set_defaults(op_name='include')

    parser_exclude = subparsers.add_parser('exclude', parents=[op_parser])
    parser_exclude.set_defaults(op_name='exclude')

    return


def main():
    parser = create_parser()
    args = parser.parse_args()
    kwargs = dict(args._get_kwargs())
    args.func(**kwargs)


if __name__ == '__main__':
    main()
