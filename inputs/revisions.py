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
        'blank_count': len([x for x in revisions if x['rev_len'] == 0]),
        'deleted_count': len([x for x in revisions if x['rev_deleted'] > 0]),
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

    return revs

REVERT_WINDOW = 4
SLEUTHING_FACTOR = 10
from collections import OrderedDict


def partition_reverts(revs):
    reverted = OrderedDict()
    clean = []
    for i, rev in enumerate(revs):
        if rev['rev_id'] in reverted:
            continue
        window = REVERT_WINDOW  # if comment contains 'revert' do something
        if 'revert' in rev['rev_comment'].lower():
            window += SLEUTHING_FACTOR
        wrevs = revs[max(i - window, 0):i]
        for wi, wrev in enumerate(wrevs):
            if wrev['rev_sha1'] == rev['rev_sha1']:
                # found a revert thang
                wreverted = dict([(r['rev_id'], r) for r in wrevs[wi + 1:]])
                reverted.update(wreverted)
                reverted[rev['rev_id']] = rev
                break

    clean = [r for r in revs if r['rev_id'] not in reverted]
    return reverted.values(), clean


class Revisions(Input):
    def fetch(self):
        ret = {}
        revs = get_json('http://ortelius.toolserver.org:8089/all/?title=' + self.page_title.replace(' ', '_'))
        ret['article'] = preprocess_revs(revs['article'])
        ret['talk'] = preprocess_revs(revs['talk'])

        ret['article_reverted'], ret['article_without_reverted'] = partition_reverts(ret['article'])
        ret['talk_reverted'], ret['talk_without_reverted'] = partition_reverts(ret['talk'])
        return ret

    stats = {
        'revs_without_reverted': lambda f: all_revisions(f['article_without_reverted']),
        'revs_reverted': lambda f: all_revisions(f['article_reverted']),
        'revs': lambda f: all_revisions(f['article']),
        'talks_without_reverted': lambda f: all_revisions(f['talk_without_reverted']),
        'talks_reverted': lambda f: all_revisions(f['talk_reverted']),
        'talks': lambda f: all_revisions(f['talk']),
    }
