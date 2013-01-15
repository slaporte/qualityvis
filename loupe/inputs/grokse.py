from base import Input
from wapiti import get_json
from stats import dist_stats


class PageViews(Input):
    prefix = 'pv'
    def fetch(self):
        return get_json('http://stats.grok.se/json/en/latest90/' + self.page_title)

    stats = {
        '90_days': lambda f: dist_stats(f['daily_views'].values()),
    }
