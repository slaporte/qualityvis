import realgar
from . import Input, get_json
from stats import dist_stats
from datetime import timedelta, datetime

def parse_date_string(stamp):
    return datetime.strptime(stamp, '%Y%m%d%H%M%S')


class HistoryError(Exception):
    pass


def mean(vals):
    return sum(vals) / len(vals)

def median(vals):
    copy = sorted(vals)
    size = len(vals)
    if size % 2 == 1:
        return copy[(size - 1) / 2]
    else:
        return (copy[size/2 - 1] + copy[size/2]) / 2

def pow_diff(vals, power):
    m = mean(vals)
    return [(v - m) ** power for v in vals]

def variance(vals):
    return mean(pow_diff(vals, 2))

def std_dev(vals):
    return variance(vals) ** 0.5

def rel_std_dev(vals):
    return std_dev(vals) / mean(vals)

def skewness(vals):
    return (sum(pow_diff(vals, 3)) / 
            ((len(vals) - 1) * (std_dev(vals) ** 3)))

def kurtosis(vals):
    return (sum(pow_diff(vals, 4)) / 
            ((len(vals) - 1) * (std_dev(vals) ** 4)))

def num_stats(vals):
    return {
        'mean':     mean(vals),
        'median':   median(vals),
        'variance': variance(vals),
        'std_dev':  std_dev(vals),
        'rel_std_dev':  rel_std_dev(vals),
        'skewness': skewness(vals),
        'kurtosis': kurtosis(vals),
        'size': len(vals)
    }

def revision_calc(revisions):
    if revisions == []:
        return
    first_edit_date = parse_date_string(revisions[0]['rev_timestamp'])
    age = datetime.now() - first_edit_date
    most_recent_edit_date = parse_date_string(revisions[-1]['rev_timestamp'])
    most_recent_edit_age = datetime.now() - most_recent_edit_date
    def get_by_period(year, month=0):
        by_period = []
        if month == 0:
            for rev in revisions:
                if rev['rev_timestamp'][:4] == str(year):
                    by_period.append(rev)
        else:
            for rev in revisions:
                if rev['rev_timestamp'][:6] == str(year) + str(month).zfill(2):
                    by_period.append(rev)
        return by_period

    def get_since(day_limit):
        recent_revs = []
        threshold = datetime.now() - timedelta(days=day_limit)
        for rev in revisions:
            if parse_date_string(rev['rev_timestamp']) > threshold:
                recent_revs.append(rev)
        return recent_revs

    def get_average_time_between_edits(revisions=None):
        times = []
        if revisions == None:
            revisions = revisions
        for rev in revisions:
            times.append(parse_date_string(rev['rev_timestamp']))
        time_diffs = []
        for i, time in enumerate(times):
            if time == times[0]:
                continue
            else:
                time_diffs.append(time - times[i - 1])
        if len(time_diffs) != 0:
            average = sum(time_diffs, timedelta(0)) / len(time_diffs)
            return average.total_seconds()
        else:
            return 0

    def get_edits_per_day(revisions=None):
        times = []
        if revisions == None:
            revisions = revisions
        for rev in revisions:
            times.append(parse_date_string(rev['rev_timestamp']))
        time_diffs = []
        for i, time in enumerate(times):
            if time == times[0]:
                continue
            else:
                time_diffs.append(time - times[i - 1])
        if len(time_diffs) != 0:
            return str(sum(time_diffs, timedelta(0)) / len(time_diffs))
        else:
            return 0

    def get_average_length(revisions=None):
        if revisions == None:
            revisions = revisions
        if len(revisions) != 0:
            return int(sum([rev['rev_len'] for rev in revisions]) / len(revisions))
        return 0

    def get_revert_estimate(revisions=None):
        reverts = 0
        if revisions == None:
            revisions = revisions
        for rev in revisions:
            if 'revert' in rev['rev_comment'].lower():
                reverts += 1
        return reverts

    def get_revision_total(revisions=None):
        if revisions == None:
            revisions = revisions
        return len(revisions)

    def get_minor_count(revisions=None):
        if revisions == None:
            revisions = revisions
        return int(sum([rev['rev_minor_edit'] for rev in revisions]))

    def get_anon_count(revisions=None):
        anon_count = 0
        if revisions == None:
            revisions = revisions
        for rev in revisions:
            if rev['rev_user'] == 0:
                    anon_count += 1
        return anon_count

    def get_editor_counts(revisions=None):
        authors = {}
        if revisions == None:
            revisions = revisions
        for rev in revisions:
            user = rev['rev_user_text']
            if user in authors:
                authors[user] += 1
            else:
                authors[user] = 1
        return authors

    def get_some_editors(num, revisions=None):
        if revisions == None:
            revisions = revisions
        authors = get_editor_counts(revisions)
        return dict([(a, c) for (a, c) in authors.items() if c > num])

    def get_top_editors(revisions=None):
        if revisions == None:
            revisions = revisions
        authors = get_editor_counts(revisions)
        return sorted(authors.iteritems(), key=lambda (k, v): v, reverse=True)

    def get_top_percent_editors(top=.20, revisions=None):
        if revisions == None:
            revisions = revisions
        editors = get_editor_counts(revisions)
        if(len(editors)) != 0:
            threshold = int(round(len(editors) * top))
            top_editors = get_top_editors(revisions)[:threshold]
            total = sum([v for (k, v) in top_editors], 0)
            return total / float(get_revision_total(revisions))
        else:
            return 0

    def get_editor_count(revisions=None):
        if revisions == None:
            revisions = revisions
        return len(get_editor_counts(revisions))

    def get_editor_bytes(revisions=None):
        authors = {}
        if revisions == None:
            revisions = revisions
        for rev in revisions:
            user = rev['rev_user_text']
            try:
                authors[user].append(rev['rev_len'])
            except KeyError:
                authors[user] = [rev['rev_len']]
        return authors

    return {'total_revisions':            get_revision_total(),
            'minor_count':                  get_minor_count(),
            'byte_count':                   get_editor_bytes(),
            'IP_edit_count':                get_anon_count(),
            'first_edit':                   str(first_edit_date),
            'most_recent_edit':             str(most_recent_edit_date),
            'average_time_between_edits':   get_average_time_between_edits(),
            'age':                          age.days,
            'recent_edit_age':              most_recent_edit_age.days,
            'editors_five_plus_edits':      len(get_some_editors(5)),
            'top_20_percent':               get_top_percent_editors(),
            'top_5_percent':                get_top_percent_editors(.05),
            'total_editors':                get_editor_count(),
            'average_length':               get_average_length(),
            'reverts_estimate':             get_revert_estimate(),
            'last_30_days_total_revisions': get_revision_total(get_since(30)),
            'last_30_days_minor_count':     get_minor_count(get_since(30)),
            'last_30_days_IP_edit_count':   get_anon_count(get_since(30)),
            'last_30_days_average_time_between_edits': get_average_time_between_edits(get_since(30)),
            'last_30_days_editors_five_plus_edits': len(get_some_editors(5, get_since(30))),
            'last_30_days_top_20_percent':  get_top_percent_editors(.20, get_since(30)),
            'last_30_days_top_5_percent':   get_top_percent_editors(.05, get_since(30)),
            'last_30_days_total_editors':   get_editor_count(get_since(30)),
            'last_30_days_average_length':  get_average_length(get_since(30)),
            'last_30_days_reverts_estimate': get_revert_estimate(get_since(30)),
            'last_500_total_revisions':     get_revision_total(revisions[:500]),
            'last_500_minor_count':         get_minor_count(revisions[:500]),
            'last_500_IP_edit_count':        get_anon_count(revisions[:500]),
            'last_500_average_time_between_edits': get_average_time_between_edits(revisions[:500]),
            'last_500_editors_five_plus_edits': len(get_some_editors(5, revisions[:500])),
            'last_500_top_20_percent':      get_top_percent_editors(.20, revisions[:500]),
            'last_500_top_5_percent':       get_top_percent_editors(.05, revisions[:500]),
            'last_500_total_editors':       get_editor_count(revisions[:500]),
            'last_500_average_length':      get_average_length(revisions[:500]),
            'last_500_reverts_estimate':    get_revert_estimate(revisions[:500]),
            'fetch_time':                   str(datetime.now()),
            'time_total':                   str(datetime.now() - time_1),
            'time_postdb':                  str(datetime.now() - time_2)
            }


class Revisions(Input):
    def fetch(self):
        return get_json('http://ortelius.toolserver.org:8089/all/' + self.page_title.replace(' ', '_')) 

    stats = {
        # todo fix "Object of type 'NoneType' has no len()" error
        #'revision_stats': lambda f: revision_calc(f['article']),
        #'talk_stats': lambda f: revision_calc(f['talk'])
    }