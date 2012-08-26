from base import Input, get_json
from stats import dist_stats
from datetime import datetime, timedelta
from itertools import chain
from math import ceil

RETURNING_ED_THRESHOLD = 5

def parse_date_string(stamp):
    return datetime.strptime(stamp, '%Y%m%d%H%M%S')


def set_info(revisions):
    editor_counts = get_editor_counts(revisions)
    sorted_editor_counts = sorted(editor_counts.iteritems(), key=lambda (k, v): v, reverse=True)

    return {
        'count':    len(revisions),
        'minor_count':  int(sum([rev['rev_minor_edit'] for rev in revisions])),
        'byte_count': sum([rev['rev_diff'] for rev in revisions]),
        'abs_byte_dist': dist_stats([abs(rev['rev_diff']) for rev in revisions]) if revisions else {},
        'IP_edit_count':  len([rev for rev in revisions if rev['rev_user'] == 0]),
        'revert_estimate':  len([rev for rev in revisions if 'revert' in rev['rev_comment'].lower()]),
        'ed_returning': len([(a, c) for (a, c) in editor_counts.iteritems() if c > RETURNING_ED_THRESHOLD]),
        'ed_unique': len(editor_counts),
        'ed_top_20': get_top_percent_editors(.20, sorted_editor_counts, len(revisions)),
        'ed_top_5': get_top_percent_editors(.05, sorted_editor_counts, len(revisions)),
        'ed_highest': sorted_editor_counts[0] if sorted_editor_counts else None,
        }


def newer_than(num_days, rev_list):
    ret = []
    bound = datetime.now() - timedelta(days=num_days)
    for i in range(0, len(rev_list)):
        if rev_list[i]['rev_parsed_date'] < bound:
            continue
        else:
            ret = rev_list[i:]
            break
    return ret


def get_editor_counts(revisions):
    authors = {}
    for rev in revisions:
        user = rev['rev_user_text']
        try:
            authors[user] += 1
        except KeyError:
            authors[user] = 1
    return authors


def get_top_percent_editors(percent, sorted_editor_counts, rev_len):
    if sorted_editor_counts:
        threshold = int(ceil(len(sorted_editor_counts) * percent))
        top_editors = sorted_editor_counts[:threshold]
        total = sum([v for (k, v) in top_editors], 0)
        return total / float(rev_len)
    else:
        return 0.0


def all_revisions(revisions):
    if revisions:
        ret = {
        'all': set_info(revisions),
        'last_30_days': set_info(newer_than(30, revisions)),
        'last_2_days': set_info(newer_than(2, revisions)),
        'most_recent_edit_age': str(datetime.now() - revisions[-1]['rev_parsed_date']),
        'first_edit_date': str(revisions[0]['rev_parsed_date']),
        'first_edit_age': str(datetime.now() - revisions[0]['rev_parsed_date']),
        'most_recent_edit_date': str(revisions[-1]['rev_parsed_date'])
        # TODO: stats by editor (top %, 5+ edits), by date (last 30 days), length stats
        }
    else:
        ret = {
        'all': None,
        'last_30_days': None,
        'last_2_days': None,
        'most_recent_edit_age': None,
        'first_edit_date': None,
        'first_edit_age': None,
        'most_recent_edit_date': None
        }
    return ret


def preprocess_revs(revs):
    prev_len = 0
    for rev in revs:
        rev['rev_parsed_date'] = parse_date_string(rev['rev_timestamp'])
        rev['rev_diff'] = rev['rev_len'] - prev_len
        prev_len = rev['rev_len']
    return


class Revisions(Input):
    def fetch(self):
        revs = get_json('http://ortelius.toolserver.org:8089/all/?title=' + self.page_title.replace(' ', '_'))
        preprocess_revs(revs['article'])
        preprocess_revs(revs['talk'])
        return revs

    stats = {
        'article_revs': lambda f: all_revisions(f['article']),
        'talk_revs': lambda f: all_revisions(f['talk'])
    }
