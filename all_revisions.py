from bottle import route, run, JSONPlugin, request
import bottle
from datetime import datetime
import os
import oursql
from bottle_compressor import CompressorPlugin

compressor_plugin = CompressorPlugin()
bottle.install(compressor_plugin)

bottle.install(JSONPlugin())
# TODO: timestamp
from bottle_compressor import CompressorPlugin
compressor_plugin = CompressorPlugin()
bottle.install(compressor_plugin)


def parse_date_string(stamp):
    return datetime.strptime(stamp, '%Y%m%d%H%M%S')

ALL_PROPS = ["rev_sha1", "rev_len", "rev_text_id", "rev_timestamp", "rev_minor_edit", "rev_user_text", "rev_comment", "rev_parent_id", "rev_deleted", "rev_page", "rev_user", "rev_id"]

DESIRED_PROPS = ["rev_sha1", "rev_len", "rev_timestamp", "rev_minor_edit", "rev_user_text", "rev_comment", "rev_deleted", "rev_user", "rev_id"]

class ArticleHistory(object):
    '''article history object'''
    def __init__(self, title, namespace=0):
        db = oursql.connect(db='enwiki_p',
            host="enwiki-p.rrdb.toolserver.org",
            read_default_file=os.path.expanduser("~/.my.cnf"))
        cursor = db.cursor(oursql.DictCursor)
        cursor.execute(u'''
            SELECT      {}
            FROM        revision
            INNER JOIN  page ON revision.rev_page = page.page_id
            WHERE       page_title = ? AND page.page_namespace = ?;
            '''.format(', '.join(DESIRED_PROPS)), (title, namespace))
        self.revisions = cursor.fetchall()


@route('/revisions/<title:path>')
def get_revisions(title):
    article = ArticleHistory(title)
    return {'result': article.revisions}

@route('/all')
@route('/all/')
def get_everything():
    title = request.query.title
    article = ArticleHistory(title)
    talk    = ArticleHistory(title, 1)
    return {'article': article.revisions, 'talk': talk.revisions}

if __name__ == '__main__':
    run(host='0.0.0.0', port=8089, reloader=True, server='twisted', debug=True)
