import realgar
from . import Input, get_json

def get_google_news(title, **kw):
        return get_json('http://ajax.googleapis.com/ajax/services/search/news?v=1.0&q=' + title) 

def get_google_search(title, **kw):
        return get_json('http://ajax.googleapis.com/ajax/services/search/web?v=1.0&q=' + title) 


class googleNews(Input):
    fetch = get_google_news
    fetch = staticmethod(fetch)

    stats = {
        'google_news_results': lambda f: f['responseData']['cursor']['estimatedResultCount']
    }


class googleSearch(Input):
    fetch = get_google_search
    fetch = staticmethod(fetch)

    stats = {
        'google_search_results': lambda f: f['responseData']['cursor']['estimatedResultCount']
    }