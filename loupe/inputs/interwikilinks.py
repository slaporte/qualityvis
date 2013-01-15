from lib import wapiti
from base import Input

class InterWikiLinks(Input):
    prefix = 'iw'

    def fetch(self):
        return wapiti.get_interwikilinks(self.page_title)

    stats = {
        'count': lambda f_res: len(f_res),
    }
