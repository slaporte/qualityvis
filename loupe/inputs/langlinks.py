from lib import wapiti
from base import Input

class LangLinks(Input):
    prefix = 'll'
    def fetch(self):
        return wapiti.get_langlinks(self.page_title)

    stats = {
        'count': lambda f_res: len(f_res),
    }
