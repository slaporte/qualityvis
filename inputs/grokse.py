from base import Input
from wapiti import get_json
from stats import dist_stats

def daily_views(d):
    days = d['daily_views']
    return [days[k] for k in days]


class PageViews(Input):
    def fetch(self):
        return get_json('http://stats.grok.se/json/en/latest90/' + self.page_title)

    stats = {
        'pv_dist': lambda f: dist_stats(daily_views(f)),
    }
