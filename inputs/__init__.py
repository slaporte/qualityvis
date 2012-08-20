

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


def list_stats(prefix, func):
    from stats import mean, median, variance, std_dev, rel_std_dev, skewness, kurtosis
    stats = {
        'mean': lambda vals: mean(vals),
        'median':   lambda vals: median(vals),
        'variance': lambda vals: variance(vals),
        'std_dev':  lambda vals: std_dev(vals),
        'rel_std_dev':  lambda vals: rel_std_dev(vals),
        'skewness': lambda vals: skewness(vals),
        'kurtosis': lambda vals: kurtosis(vals),
        'size': lambda vals: len(vals)
    } 

    ret = {}
    def get_stats_func(name, func):
        return lambda x: stats[name](func(x))

    for k, stats_func in stats.items():
        ret[str(prefix)+'_'+str(k)] = get_stats_func(k, func)

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
