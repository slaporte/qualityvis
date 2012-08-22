import realgar
from . import Input, get_url


class Wikitrust(Input):
    def fetch(self):
        # TODO need rev_id
        return get_url('http://en.collaborativetrust.com/WikiTrust/RemoteAPI?method=quality&revid=' + str(self.page_id)) 

    stats = {
        'wikitrust': lambda f: str(f.text)
    }