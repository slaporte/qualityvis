import realgar
from . import Input, get_json, list_stats

def get_pageviews(title, **kw):
    return get_json('http://stats.grok.se/json/en/latest90/' + title) 

def daily_views(d):
    days = d['daily_views']
    return [days[k] for k in days]

class pageViews(Input):
    fetch = get_pageviews
    fetch = staticmethod(fetch)

    stats = {
        'daily_views': lambda f: daily_views(f)
    }
    stats.update(list_stats('views_count', daily_views))