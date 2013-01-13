from __future__ import unicode_literals
import os
from os.path import join as pjoin
import shutil

import ConfigParser
from argparse import ArgumentParser

import article_list

_DEFAULT_DIR_PERMS = 0755
_CURDIR = os.path.abspath(os.path.dirname(__file__))
_CONF_NAME = 'loupe.conf'

class Loupe(object):
    def __init__(self, config, path):
        self.config = config
        self.path = path

    @classmethod
    def from_path(cls, path=None, config_name=_CONF_NAME):
        path = path or os.getenv('LOUPE_HOME') or os.getcwd()
        path = os.path.normpath(path)
        config = ConfigParser.SafeConfigParser()
        config.read(pjoin(path, config_name))

        return cls(config, path)

    @classmethod
    def init_new(cls, path):
        if not isinstance(path, basestring):
            path = path[0]  # friggin nargs=1
        path = os.path.normpath(path)
        if os.path.exists(path):
            # TODO: force?
            raise IOError('path already exists: %s' % path)

        os.makedirs(path, _DEFAULT_DIR_PERMS)
        os.mkdir(pjoin(path, 'article_lists'), _DEFAULT_DIR_PERMS)
        os.mkdir(pjoin(path, 'inputs'), _DEFAULT_DIR_PERMS)
        os.mkdir(pjoin(path, 'fetch_data'), _DEFAULT_DIR_PERMS)
        os.mkdir(pjoin(path, 'projects'), _DEFAULT_DIR_PERMS)

        _init_default_config(path)

        return cls.from_path(path)

    @property
    def lists_home(self):
        return pjoin(self.path, 'article_lists')


def _init_default_config(path):
    init_conf = pjoin(path, _CONF_NAME)
    shutil.copyfile(pjoin(_CURDIR, 'default.conf'), init_conf)
    os.chmod(init_conf, 0600)


def init_home(path, **kw):
    Loupe.init_new(path)


def create_parser():
    prs = ArgumentParser(description='Loupe: great prices, great deals')
    prs.add_argument('--home', help='path to Loupe home directory')
    subprs = prs.add_subparsers()

    prs_init = subprs.add_parser('init')
    prs_init.add_argument('path', nargs=1,
                          help='path of new Loupe home directory')
    prs_init.set_defaults(func=init_home)

    prs_list = subprs.add_parser('list')
    article_list.add_subparsers(prs_list.add_subparsers())

    return prs
"""
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

    pass
"""


def main():
    parser = create_parser()
    args = parser.parse_args()
    kwargs = dict(args._get_kwargs())
    if args.func is not init_home:
        lou = Loupe.from_path(kwargs['home'])
        if not kwargs.get('list_home'):
            kwargs['list_home'] = lou.lists_home
    args.func(**kwargs)


if __name__ == '__main__':
    main()
