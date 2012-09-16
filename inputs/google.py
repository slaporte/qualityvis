from base import Input
from wapiti import get_json

class GoogleNews(Input):
    prefix = 'gn'
    def fetch(self):
        return get_json('http://ajax.googleapis.com/ajax/services/search/news?v=1.0&q=' + self.page_title)

    stats = {
        'google_news_results': lambda f: f['responseData']['cursor']['estimatedResultCount']
    }


class GoogleSearch(Input):
    prefix = 'gs'
    def fetch(self):
        return get_json('http://ajax.googleapis.com/ajax/services/search/web?v=1.0&q=' + self.page_title)

    stats = {
        'google_search_results': lambda f: f['responseData']['cursor']['estimatedResultCount']
    }
