import wapiti

import bottle
from bottle import route, run, request, JSONPlugin

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

input_mods = [importer.find_module(name).load_module(name)
              for (importer, name, _) in pkgutil.walk_packages('.')
              if name.startswith('inputs.') and not name.startswith('inputs.base')]

AVAIL_INPUTS = {}

for im in input_mods:
    for m in im.__dict__.itervalues():
        if type(m) is type and hasattr(m, 'fetch'):
            AVAIL_INPUTS[m.__name__] = m
            AVAIL_INPUTS[m.__name__.lower()] = m
AVAIL_INPUTS.pop('Input', None)

@route('/<input_name>/')
@route('/<input_name>/<page_title>')
@route('/<input_name>/<page_title>/')
@route('/<input_name>/<page_title>/<page_id:int>')
def do_input(input_name, page_title='', page_id=None):
    in_type = AVAIL_INPUTS.get(input_name.lower())
    page_title = request.query.title or page_title
    page_id = request.query.page_id or page_id
    if in_type is None:
        raise Exception('No input found with name "' + input_name + '"')
    if not page_title:
        raise Exception('You must pass in a page title (and preferably a page id)')
    if not page_id:
        page = wapiti.get_articles(titles=page_title, parsed=False)[0]
        page_id = page.page_id
    # TODO: optional page_id, do lookup if None
    in_obj = in_type(page_title, page_id)
    results = in_obj()
    results['durations'] = in_obj.durations
    return results
    #return in_obj.results

if __name__ == '__main__':
    bottle.debug(True)
    run(host='0.0.0.0', port=8700, server='gevent', reloader=True)
