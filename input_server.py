import bottle
from bottle import route, run, JSONPlugin

from functools import partial
better_dumps = partial(bottle.json_dumps, indent=2,
    sort_keys=True, default=repr)
bottle.default_app().uninstall(JSONPlugin)
bottle.default_app().install(JSONPlugin(better_dumps))

# get list of inputs to serve
# handle serialization of requests
# hashing input code for remote execution
# caching results
import pkgutil
from inputs import Input

input_mods = [importer.find_module(name).load_module(name)
              for (importer, name, _) in pkgutil.walk_packages('.')
              if name.startswith('inputs.')]
AVAIL_INPUTS = {}

for im in input_mods:
    for m in im.__dict__.itervalues():
        if type(m) is type and issubclass(m, Input) and m is not Input:
            AVAIL_INPUTS[m.__name__] = m


@route('/<input_name>/<page_title>/<page_id:int>')
def do_input(input_name, page_title, page_id=None):
    in_type = AVAIL_INPUTS.get(input_name)
    if in_type is None:
        raise Exception('No input found with name "' + input_name + '"')
    # TODO: optional page_id, do lookup if None
    in_obj = in_type(page_title, page_id)
    results = in_obj()
    import pdb;pdb.set_trace()
    return results
    #return in_obj.results

if __name__ == '__main__':
    bottle.debug(True)
    run(host='0.0.0.0', port=8700, server='gevent')
