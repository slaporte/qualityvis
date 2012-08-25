from bottle import route, run, template, redirect, request
from datetime import datetime
import os
import oursql
#import jsonp_bottle

# TODO: timestamp


def parse_date_string(stamp):
    return datetime.strptime(stamp, '%Y%m%d%H%M%S')


class ArticleHistory:
    '''article history object'''
    def __init__(self, title, namespace=0):
        db = oursql.connect(db='enwiki_p',
            host="enwiki-p.rrdb.toolserver.org",
            read_default_file=os.path.expanduser("~/.my.cnf"),
            charset=None,
            use_unicode=False)
        cursor = db.cursor(oursql.DictCursor)
        cursor.execute('''
            SELECT  revision.*
           FROM        revision
            INNER JOIN  page ON revision.rev_page = page.page_id
            WHERE       page_title = ? AND page.page_namespace = ?;
            ''', (title, namespace))
        self.revisions = cursor.fetchall()


@route('/revisions/<title>')
def get_revisions(title):
    article = ArticleHistory(title)
    return {'result': article.revisions}


@route('/all/<title>')
def get_everything(title):
    article = ArticleHistory(title)
    talk    = ArticleHistory(title, 1)
    return {'article': article.revisions, 'talk': talk.revisions}

if __name__ == '__main__':
    run(host='0.0.0.0', port=8089, reloader=True, debug=True)
