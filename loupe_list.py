from __future__ import unicode_literals
import codecs
import os
import argparse
import wapiti
import json
from datetime import datetime

from collections import namedtuple

DEFAULT_EXT = '.txt'
DEFAULT_SOURCE = 'enwiki'
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
DEFAULT_FETCH_LIMIT = 100
FORMAT = 'v1'


ArticleIdentifier = namedtuple('ArticleIdentifier', 'name source')

class ArticleListManager(object):
    def __init__(self, search_path=None):
        if search_path is None:
            search_path = [os.getcwd()]
        self.search_path = search_path

    def lookup(self, filename):
        #look up first filename in self.search_path
        #return path
        pass


class ArticleList(object):
    def __init__(self, actions=None, comments=None, file_metadata=None):
        if actions is None:
            actions = []
        self.actions = actions
        self.comments = comments or {}
        self.file_metadata = file_metadata or {}

    @classmethod
    def from_file(cls, path):
        with codecs.open(path, encoding='utf-8') as f:
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
    def from_meta_string(cls, string, default_id=1, default_action='include', defaults=True):
        metadata = parse_meta_string(string=string)
        extra_attrs = {}
        kw = {}
        for k in metadata:
            if k in cls.metadata_attrs:
                kw[k] = metadata[k]
            else:
                extra_attrs[k] = metadata[k]
        if not kw:
            raise ValueError('no metadata found')
        if not kw.get('id') and defaults:
            kw['id'] = default_id
        if not kw.get('action') and defaults:
            kw['action'] = default_action
        if kw['action'] not in cls.valid_actions and defaults:
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


def parse_meta_string(string):
    ret = {}
    string = string.strip().lstrip('#').strip()
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
                list_action = ListAction.from_meta_string(line)
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


def create_parser(parent=None):
    if parent is None:
        parser = argparse.ArgumentParser(description='alias mission control center')
    else:
        parser = parent.add_subparsers(title='list')
    parser.add_argument('--list_home', help='Lookup directory')

    subparsers = parser.add_subparsers()
    parser_show = subparsers.add_parser('show')
    parser_show.add_argument('target_list', help='Name of the list or list file', nargs='?')
    parser_show.set_defaults(func=show)

    parser_create = subparsers.add_parser('create')
    parser_create.add_argument('target_list', help='Name of the list or list file')
    parser_create.set_defaults(func=create)

    parser_include = subparsers.add_parser('include')
    parser_include.add_argument('search_target', help='Article, category, or template')
    parser_include.add_argument('target_list', help='Name of the list or list file')
    parser_include.add_argument('--limit', '-l', type=int, help='Number of articles', default=DEFAULT_FETCH_LIMIT)
    parser_include.add_argument('--recursive', '-R', help='Fetch recursively', default=True)
    parser_include.set_defaults(func=include)

    parser_exclude = subparsers.add_parser('exclude')
    parser_exclude.add_argument('search_target', help='Article, category, or template')
    parser_exclude.add_argument('target_list', help='Name of the list or list file')
    parser_exclude.add_argument('--limit', '-l', type=int, help='Number of articles', default=DEFAULT_FETCH_LIMIT)
    parser_exclude.add_argument('--recursive', '-R', help='Fetch recursively', default=True)
    parser_exclude.set_defaults(func=exclude)

    return parser


def show(path):
    if os.path.isdir(path):
        print '\n'.join([os.listdir(path)])
    elif os.path.isfile(path):
        a_list = ArticleList.from_file(path)
        print json.dumps(a_list.file_metadata, indent=4)
        print '\nTotal articles: ', len(a_list.get_articles()), '\n'
        import pdb; pdb.set_trace()


def create(list_name, list_home):
    # create empty list
    pass


def include(**kw):
    pass


def exclude(**kw):
    pass


def main(func, list_home=None, target_list=None, search_target=None, limit=DEFAULT_FETCH_LIMIT, **kw):
    list_home = list_home or os.getcwd()
    if not os.path.isdir(list_home):
        raise IOError('not a directory: ' + str(list_home))
    if target_list:
        if os.path.isfile(target_list):
            target_list_path = target_list
        else:
            alm = ArticleListManager(search_path=[list_home])
            target_list_path = alm.lookup(target_list)
    else:
        target_list_path = None
    if func is show:
        path = target_list_path or list_home
        show(path)
    elif func is create:
        outfile = list_home + '/' + target_list + DEFAULT_EXT
        if not target_list:
            raise IOError('not a valid filename: %s' % target_list)
        if target_list_path:
            raise IOError('list already exists: %s' % target_list_path)
        codecs.open(outfile, 'w', encoding='utf-8').close()
        print 'Created article list %s' % outfile
    else:
        outfile = list_home + '/' + target_list + DEFAULT_EXT
        if not target_list_path:
            raise IOError('file not found for target list: %s' % target_list)
        a_list = ArticleList.from_file(outfile)
        if search_target.startswith('Category:'):
            article_list = wapiti.get_category_recursive(search_target, count=limit, to_zero_ns=True)
        elif search_target.startswith('Template:'):
            article_list = wapiti.get_transcluded(page_title=search_target, limit=limit, to_zero_ns=True)
        if func is include:
            a_list.include([a[2] for a in article_list], source=DEFAULT_SOURCE, term=search_target)
            a_list.write(outfile)
        if func is exclude:
            a_list.exclude([a[2] for a in article_list], source=DEFAULT_SOURCE, term=search_target)
            a_list.write(outfile)
        import pdb; pdb.set_trace()


if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()
    kwargs = dict(args._get_kwargs())
    main(**kwargs)
