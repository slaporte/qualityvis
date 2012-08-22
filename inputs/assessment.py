import realgar
from . import Input

class Assessment(Input):
    def fetch(self):
        return realgar.get_talk_page(self.page_title)

    stats = {
        'assessment': lambda f_res: f_res # process,
    }
