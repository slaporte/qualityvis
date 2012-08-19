

class Input(object):
    source = None

    @classmethod
    def fetch(cls, title, rev_id, page_id, dom):
        return cls.source(title, rev_id, page_id, dom)

    @classmethod
    def process(cls, fetch_results):
        ret = {}
        for k, func in cls.stats.items():
            try:
                if fetch_results:
                    res = func(fetch_results)
                else:
                    res = None
            except Exception as e:
                ret[k] = e
            else:
                ret[k] = res
        return ret


def get_url(url, params=None, raise_exc=True):
    import requests
    if params is None:
        params = {}
    resp = requests.Response()
    try:
        resp = requests.get(url, params=params)
    except Exception as e:
        if raise_exc:
            raise
        else:
            resp.error = e
    return resp


def get_json(*args, **kwargs):
    import json
    resp = get_url(*args, **kwargs)
    return json.loads(resp.text)
