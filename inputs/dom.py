from . import Input
from pyquery import PyQuery


class DOM(Input):
    @staticmethod
    def fetch(title, rev_id, page_id, text):
        return PyQuery(text)

    stats = {
        'paragraph_count': lambda f: len(f('p'))
    }
