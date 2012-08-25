import wapiti
from base import Input

class Backlinks(Input):
    def fetch(self):
        return wapiti.get_backlinks(self.page_title)

    stats = {
        'backlinks': lambda f_res: len(f_res),
    }
