import wapiti
import re
import copy
from base import Input
from dateutil.parser import parse
from collections import OrderedDict
from datetime import datetime


def find_rating(text, rating_type='assessment'):
    if rating_type == 'importance':
        ratings = re.findall(r'\|\s*((importance)\s*=\s*(.+?))(\b|\|)', text, re.I)
    else:
        ratings = re.findall(r'\|\s*((class)\s*=\s*(.+?))(\b|\|)', text, re.I)
    if not ratings:
        return None
    else:
        return [rating[2].strip(' \"\'').upper() for rating in ratings]


def average_rating(project_ratings, rating_type='assessment'):
    if not project_ratings:
        return 'NO'
    if rating_type == 'importance':
        # "Top", "High", "Mid", "Low" and "No"
        ratings = ['NO', 'LOW', 'MID', 'HIGH', 'TOP']
    else:
        # "FA", "A", "B", "C", "Start", "Stub", "Dab", "Category", "Template", "Book", "Current", "Future", "Redirect", "Needed" and "No"
        ratings = ['NO', 'STUB', 'START', 'C', 'B', 'A', 'GA', 'FA']
    score = 0
    for r in ratings:
        if project_ratings.count(r) > 0:
            score += project_ratings.count(r) * ratings.index(r)
    average = ratings[int(round(score / float(len(project_ratings))))]
    return average


def find_article_history(text):
    matches = re.findall(r'{{\s*Article[ hH]+istory(.+currentstatus.*?)}}', text, re.DOTALL)
    if not matches:
        return None
    else:
        if len(matches) > 1:
            print 'Warning: multiple ArticleHistory instances found.'
        return matches[0].strip().strip('|')  # get rid of excess whitespace and pipes


def tmpl_text_to_odict(text):
    ret = OrderedDict()
    pairs = text.split('|')
    for p in pairs:
        p = p.strip()
        if not p:
            continue
        k, _, v = p.partition('=')
        k = k.strip()
        v = v.strip()
        if not k:
            # blank key error
            #import pdb;pdb.set_trace()
            continue
        if k in ret:
            # duplicate key error
            #import pdb;pdb.set_trace()
            continue
        ret[k] = v
    return ret


class HistoryAction(object):
    def __init__(self, name, **kwargs):  # num, date_str, link, result_str, old_id_str):
        if not name or not action_name_re.match(name):
            raise ValueError('Expected HistoryAction name in the format "action#".')
        self.name = name
        self.num = int(name[6:])
        self.type = kwargs.pop('a_type')
        self.date = None
        date = kwargs.pop('date', None)
        date = date.replace('(UTC)', '')  # some date strings include timezone, but we'll ignore it since parse() can't handle it
        try:
            self.date = parse(date)
            self.date_broken = False
        except ValueError:
            self.date = datetime.utcfromtimestamp(0)
            self.date_broken = True
            print 'Could not parse date string: ', date

        self.link = kwargs.pop('link', None)
        self.result = kwargs.pop('result', None)
        self.old_id = kwargs.pop('oldid', None)
action_name_re = re.compile('^action\d+$')


def parse_article_history(hist_orig):
    actions = []
    hist_dict = copy.deepcopy(hist_orig)
    action_names = [k for k in hist_dict.keys() if action_name_re.match(k)]
    action_names.sort(key=lambda x: int(x[6:]))
    for a_name in action_names:
        cur_action = HistoryAction(name=a_name,
                                   a_type=hist_dict[a_name],
                                   **dict([(k[len(a_name):], v)
                                           for k, v in hist_dict.items()
                                           if k.startswith(a_name)])
                                   )
        actions.append(cur_action)
    return actions


def find_tmpl(text):
    ratings = re.findall(r'\|\s*((class|currentstatus)\s*=\s*(.+?))(\b|\|)', text, re.I)
    if not ratings:
        return None
    else:
        return [rating[2] for rating in ratings]


def parse_date(date):
    if date == '':
        return date
    try:
        return parse(date)
    except:
        return date


def age_secs(date):
    try:
        diff = datetime.utcnow() - date
        try:
            return diff.total_seconds()
        except TypeError:
            return 0
    except TypeError:
        return 0


class ArticleHistory(Input):
    prefix = 'ah'

    def fetch(self):
        return wapiti.get_talk_page(self.page_title)

    def process(self, f_res):
        ah_text = find_article_history(f_res)
        assessment_list = find_rating(f_res, rating_type='assessment') or []
        importance_list = find_rating(f_res, rating_type='importance') or []
        if ah_text:
            tmpl_dict = tmpl_text_to_odict(ah_text)
            actions = parse_article_history(tmpl_dict)
            ah = {'actions': actions,
                  'current': tmpl_dict.get('currentstatus', 'NO').strip(' \"\'').upper(),
                  'topic': tmpl_dict.get('topic').strip(' \"\'').capitalize(),
                  'itndate': parse_date(tmpl_dict.get('itndate')),
                  'dykdate': parse_date(tmpl_dict.get('dykdate')),
                  'maindate': parse_date(tmpl_dict.get('maindate')),
                  'assessment': average_rating(assessment_list, rating_type='assessment'),
                  'assessment_count': len(assessment_list),
                  'assessment_list': assessment_list,
                  'importance': average_rating(importance_list, rating_type='importance'),
                  'importance_count': len(importance_list),
                  'importance_list': importance_list,
                  }
            if actions:
                ah['oldest_action_age'] = age_secs(actions[0].date)
                ah['latest_action_age'] = age_secs(actions[-1].date)
            return super(ArticleHistory, self).process(ah)
        else:
            return super(ArticleHistory, self).process(
                { 'actions': [],
                  'current': 'NO',
                  'assessment': average_rating(assessment_list, rating_type='assessment'),
                  'assessment_count': len(assessment_list),
                  'assessment_list': assessment_list,
                  'importance': average_rating(importance_list, rating_type='importance'),
                  'importance_count': len(importance_list),
                  'importance_list': importance_list,
                })

    stats = {
        'article_history': lambda f: len(f.get('actions')),
        'oldest_action_age': lambda f: f.get('oldest_action_age', 0),
        'latest_action_age': lambda f: f.get('latest_action_age', 0),
        'mainpage_age': lambda f: age_secs(f.get('maindate')),
        'dyk_age': lambda f: age_secs(f.get('dykdate')),
        'itn_age': lambda f: age_secs(f.get('itndate')),
        'topic': lambda f: f.get('topic', ''),
        'current': lambda f: f.get('current', ''),
        'actions': lambda f: [{'type': action.type, 'result': action.result, 'date': str(action.date)} for action in f.get('actions')],
        'assessment_average': lambda f: f['assessment'],
        'assessment_count': lambda f: f['assessment_count'],
        'assessment_list': lambda f: f['assessment_list'],
        'importance_average': lambda f: f['importance'],
        'importance_count': lambda f: f['importance_count'],
        'importance_list': lambda f: f['importance_list']
    }