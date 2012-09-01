import wapiti
from base import Input

class InterWikiLinks(Input):
    def fetch(self):
        return wapiti.get_interwikilinks(self.page_title)

    stats = {
        'interwikilinks': lambda f_res: len(f_res),
    }
