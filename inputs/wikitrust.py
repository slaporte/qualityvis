import realgar
from . import Input, get_url

def get_wikitrust(title, page_id, rev_id, text):
    return get_url('http://en.collaborativetrust.com/WikiTrust/RemoteAPI?method=quality&revid=' + str(rev_id)) 


class wikitrust(Input):
    fetch = get_wikitrust
    fetch = staticmethod(fetch)

    stats = {
        'wikitrust': lambda f: str(f.text)
    }