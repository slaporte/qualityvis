from base import Input, get_json
from stats import dist_stats
from datetime import timedelta, datetime

def parse_date_string(stamp):
    return datetime.strptime(stamp, '%Y%m%d%H%M%S')

def revision_calc(revisions):
    return {
        'count':    len(revisions),
        'minor_count':  int(sum([rev['rev_minor_edit'] for rev in revisions])),
        'byte_count': '',  # TODO
        'IP_edit_count':  len([rev for rev in revisions if rev['rev_user'] == 0]),
        'revert_estimate':  len([rev for rev in revisions if 'revert' in rev['rev_comment'].lower()]),
        'most_recent_edit_date': str(parse_date_string(revisions[-1]['rev_timestamp'])),
        'most_recent_edit_age': str(datetime.now() - parse_date_string(revisions[-1]['rev_timestamp'])),
        'first_edit_date': str(parse_date_string(revisions[0]['rev_timestamp'])),
        'first_edit_age': str(datetime.now() - parse_date_string(revisions[0]['rev_timestamp'])),
        # TODO: stats by editor (top %, 5+ edits), by date (last 30 days), length stats
        }


class Revisions(Input):
    def fetch(self):
        return get_json('http://ortelius.toolserver.org:8089/all/?title=' + self.page_title.replace(' ', '_'))

    stats = {
        'article_revs': lambda f: revision_calc(f['article']),
        'talk_revs': lambda f: revision_calc(f['talk'])
    }
