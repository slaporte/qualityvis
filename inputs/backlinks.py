import realgar
from . import Input


class Backlinks(Input):
    fetch = realgar.get_backlinks
    fetch = staticmethod(fetch)

    stats = {
        'backlinks': lambda f_res: len(f_res),
    }
