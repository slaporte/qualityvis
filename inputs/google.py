from base import Input
from wapiti import get_json


class GoogleNews(Input):
    prefix = 'gn'

    def fetch(self):
        return get_json('http://ajax.googleapis.com/ajax/services/search/news?v=1.0&q=' + self.page_title)

    def process(self, f_res):
        if f_res['responseStatus'] == 403 or not f_res.get('responseData', {}).get('cursor', {}).get('estimatedResultCount', {}):
            return {}
        else:
            return super(GoogleNews, self).process(f_res['responseData']['cursor']['estimatedResultCount'])

    stats = {
        'count': lambda f: f
    }


class GoogleSearch(Input):
    prefix = 'gs'

    def fetch(self):
        return get_json('http://ajax.googleapis.com/ajax/services/search/web?v=1.0&q=' + self.page_title)

    def process(self, f_res):
        if f_res['responseStatus'] == 403 or not f_res['responseData']:
            return {}
        else:
            return super(GoogleSearch, self).process(f_res['responseData']['cursor']['estimatedResultCount'])

    stats = {
        'count': lambda f: f
    }
