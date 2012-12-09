from __future__ import unicode_literals
import json
import codecs
#import tablib
from itertools import chain
from optparse import OptionParser
from collections import namedtuple
import export_settings
import os
import glob
import time
from collections import defaultdict
from pprint import pprint

'''
http://orange.biolab.si/doc/reference/Orange.data.formats/
'''
OrangeType = namedtuple('OrangeType', 'f_type, flag')

CONTINUOUS = OrangeType('c', '')
DISCRETE = OrangeType('d', '')
IGNORE = OrangeType('s', 'ignore')
CLASS = OrangeType('d', 'class')
META_STR = OrangeType('s', 'meta')
META_DISCRETE = OrangeType('d', 'meta')
meta_features = {'title': META_STR,
                 'id': META_STR,
                 'ah_topic': META_DISCRETE,
                 'ah_actions': META_STR,
                 'ah_assessment': META_DISCRETE,
                 'ah_current': CLASS
                }
DEFAULT_COLUMNS = export_settings.COLUMNS


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


def get_column_names(flat_row_list, filter_list=None, count=100):
    if not flat_row_list:
        return []
    all_keys = [f.iterkeys() for f in flat_row_list[:count]]
    column_names = set(chain.from_iterable(all_keys))
    if filter_list:
        filter_list = set(filter_list)
        return [c for c in column_names if c in filter_list]
    else:
        return list(column_names)


def get_column_types(dataset, count=200):
    headers = dataset[0]
    dataset = dataset[1:count + 1]
    ret = {}
    for i, header in enumerate(headers):
        if header in meta_features:
            ret[header] = meta_features[header]
            continue
        try:
            value_list = [d[i] for d in dataset]
            value_set = set(value_list) - set([''])
            # Orange handles empty string as a missing value
        except Exception as e:
            import pdb;pdb.set_trace()
        try:
            [float(f) for f in value_set]
        except:
            if len(value_set) < 10:
                ret[header] = DISCRETE
            else:
                ret[header] = META_STR
        else:
            if not value_set:
                ret[header] = IGNORE
            elif len(value_set) <= 2 and all([type(v) is bool for v in value_set]):
                ret[header] = DISCRETE
            else:
                ret[header] = CONTINUOUS

    return ret


def sort_column_names(column_names):
    column_names = sorted(column_names)
    for mname, mtype in meta_features.iteritems():
        try:
            column_names.remove(mname)
        except:
            continue
        if mtype is CLASS:
            column_names.append(mname)
        else:
            column_names.insert(0, mname)
    return column_names


def ordered_yield(data, ordering, default=None):
    for o in ordering:
        yield data.get(o, default)
    return


def tmp_clean_data(data):
    ret = []
    for d in data:
        wc_val = d.get('d_word_count')
        if wc_val is None:
            #import pdb;pdb.set_trace()
            continue
        elif isinstance(wc_val, basestring):
            #import pdb;pdb.set_trace()
            continue
        else:
            ret.append(d)
    return ret


def results_to_tsv(file_name):
    output_name = file_name.partition('.')[0] + '.tab'
    results = load_results(file_name)
    flat = [flatten_dict(row) for row in results]
    flat = tmp_clean_data(flat)
    column_names = get_column_names(flat)
    column_names = sort_column_names(column_names)

    tab_results = [column_names]
    for row in flat:
        tab_results.append(list(ordered_yield(row, column_names, '')))
    column_types = get_column_types(tab_results)
    tab_results.insert(1, [c.f_type for c in ordered_yield(column_types, column_names, IGNORE)])
    tab_results.insert(2, [c.flag for c in ordered_yield(column_types, column_names, IGNORE)])
    import pdb;pdb.set_trace()
    with codecs.open(output_name, 'w', 'utf-8') as output:
        for row in tab_results:
            output.write('\t'.join([unicode(v) for v in row]))
            output.write('\n')
    return len(flat), column_types


def get_sorted_files(directory=None, ext=''):
    ret = []
    if directory is None:
        directory = os.getcwd()
    for f in glob.glob(directory + '/*' + ext):
        stats = os.stat(f)
        lastmod_date = time.localtime(stats[8])
        ret.append((lastmod_date, f))
    return [x[1] for x in sorted(ret, key=lambda f: f[0], reverse=True)]


def parse_args():
    parser = OptionParser()
    return parser.parse_args()

if __name__ == '__main__':
    opts, args = parse_args()
    try:
        file_name = args[0]
    except IndexError as ie:
        try:
            file_name = get_sorted_files('results', '.json')[0]
        except IndexError as ie:
            print 'No json files found in results folder'
    print 'Exporting', file_name, '...'
    total_rows, column_types = results_to_tsv(file_name)
    type_survey = defaultdict(int)
    total_columns = 0
    #TODO: option for default column names
    for h, t in column_types.iteritems():
        type_survey[t] += 1
        total_columns += 1
    print 'Type summary: '
    pprint(dict(type_survey))
    print 'Exported', total_rows, 'rows and', total_columns, 'columns.'
