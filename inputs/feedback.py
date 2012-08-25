import wapiti
from base import Input

class FeedbackV4(Input):
    def fetch(self):
        return wapiti.get_feedback_stats(page_id = self.page_id)

    stats = {
        'fb_trustworthy': lambda f: f[0]['total'] / f[0]['count'] if f[0]['count'] else 0,
        'fb_objective': lambda f: f[1]['total'] / f[1]['count'] if f[1]['count'] else 0,
        'fb_complete': lambda f: f[2]['total'] / f[2]['count'] if f[2]['count'] else 0,
        'fb_wellwritten': lambda f: f[3]['total'] / f[3]['count'] if f[3]['count'] else 0,
        'fb_count_trustworthy': lambda f: f[0]['count'],
        'fb_count_objective': lambda f: f[1]['count'],
        'fb_count_complete': lambda f: f[2]['count'],
        'fb_count_wellwritten': lambda f: f[3]['count'],
        'fb_count_total': lambda f: sum([x['count'] for x in f]),
        'fb_countall_total': lambda f: sum([x['countall'] for x in f])
    }
