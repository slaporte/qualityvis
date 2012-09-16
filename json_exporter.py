import json
import codecs
import tablib
from itertools import chain
from optparse import OptionParser
from collections import namedtuple

'''
http://orange.biolab.si/doc/reference/Orange.data.formats/
'''
OrangeType = namedtuple('OrangeType', 'f_type, flag')

CONTINUOUS = OrangeType('c', '')
DISCRETE = OrangeType('d', '')
IGNORE = OrangeType('s', 'i')
meta_features = {'title': OrangeType('s', 'meta'),
                 'id': OrangeType('s', 'meta'),
                 'ah_topic': OrangeType('s', 'meta'),
                 'ah_current': OrangeType('d', 'meta'),
                 'ah_actions': IGNORE,
                 'a_assessment': IGNORE
                }


def flatten_dict(root, prefix_keys=True):
    dicts = [([], root)]
    ret = {}
    seen = set()
    for path, d in dicts:
        if id(d) in seen:
            continue
        seen.add(id(d))
        for k, v in d.items():
            new_path = path + [k]
            prefix = '_'.join(new_path) if prefix_keys else k
            if hasattr(v, 'items'):
                dicts.append((new_path, v))
            else:
                ret[prefix] = v
    return ret


def load_results(file_name):
    return (json.loads(line.strip()) for line in codecs.open(file_name, encoding='utf-8'))


def get_column_names(flat_row_list, count=100):
    if not flat_row_list:
        return []
    all_keys = [f.iterkeys() for f in flat_row_list[:count]]
    column_names = set(chain.from_iterable(all_keys))
    return list(column_names)


def get_column_types(dataset, count=100):
    #dataset = dataset[:count]
    ret = {}
    for header in dataset.headers:
        if header in meta_features:
            ret[header] = meta_features[header]
            continue
        try:
            value_set = set(dataset[header])
        except Exception as e:
            import pdb;pdb.set_trace()
        try:
            [float(f) for f in value_set if f is not '']
        except:
            ret[header] = IGNORE
        else:
            if len(value_set) > 10:
                ret[header] = CONTINUOUS
            elif len(value_set) > 1:
                ret[header] = DISCRETE
            else:
                ret[header] = IGNORE

    return ret

def ordered_yield(data, ordering, default=None):
    for o in ordering:
        yield data.get(o, default)
    return

def results_to_csv(file_name):
    output_name = file_name.partition('.')[0] + '.tab'
    results = load_results(file_name)
    flat = [flatten_dict(row) for row in results]
    column_names = get_column_names(flat)
    column_names = sorted(column_names)
    tab_results = tablib.Dataset(headers=column_names)
    for row in flat:
        row_list = []
        for val in ordered_yield(row, column_names, ''):
            row_list.append(val)
        tab_results.append(row_list)
    column_types = get_column_types(tab_results)
    tab_results.insert(0, [c.f_type for c in ordered_yield(column_types, column_names, IGNORE)])
    tab_results.insert(1, [c.flag for c in ordered_yield(column_types, column_names, IGNORE)])
    with codecs.open(output_name, 'w', 'utf-8') as output:
        output.write(tab_results.tsv.decode('utf-8'))


def parse_args():
    parser = OptionParser()
    return parser.parse_args()

if __name__ == '__main__':
    opts, args = parse_args()
    file_name = args[0]
    results_to_csv(file_name)
