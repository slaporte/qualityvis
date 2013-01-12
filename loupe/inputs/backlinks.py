import wapiti
from base import Input

class Backlinks(Input):
    prefix = 'bl'
    
    def fetch(self):
        return wapiti.get_backlinks(self.page_title)

    stats = {
        'count': lambda f_res: len(f_res),
    }
