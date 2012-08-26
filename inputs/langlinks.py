import wapiti
from base import Input

class LangLinks(Input):
    def fetch(self):
        return wapiti.get_langlinks(self.page_title)

    stats = {
        'langlinks': lambda f_res: len(f_res),
    }
