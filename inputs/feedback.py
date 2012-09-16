import wapiti
from base import Input


class FeedbackV4(Input):
    prefix = 'f4'
    def fetch(self):
        return wapiti.get_feedback_stats(page_id=self.page_id)

    stats = {
        'trustworthy': lambda f: f[0]['total'] / f[0]['count'] if f[0]['count'] else 0,
        'objective': lambda f: f[1]['total'] / f[1]['count'] if f[1]['count'] else 0,
        'complete': lambda f: f[2]['total'] / f[2]['count'] if f[2]['count'] else 0,
        'wellwritten': lambda f: f[3]['total'] / f[3]['count'] if f[3]['count'] else 0,
        'count_trustworthy': lambda f: f[0]['count'],
        'count_objective': lambda f: f[1]['count'],
        'count_complete': lambda f: f[2]['count'],
        'count_wellwritten': lambda f: f[3]['count'],
        'count_total': lambda f: sum([x['count'] for x in f]),
        'countall_total': lambda f: sum([x['countall'] for x in f])
    }


class FeedbackV5(Input):
    prefix = 'f5'
    def fetch(self):
        return wapiti.get_feedbackv5_count(page_id=self.page_id)

    stats = {
        'comments': lambda f: f,
    }
