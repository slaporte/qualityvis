
# select.py --protection-level pr_any --classes A,GA,FA [--keep-discrete] [--attrfile attrnames.txt] --output outputfile.tab file1.tab file2.tab

'''
    Select by protection-level
    Select by classes

'''

import argparse
from data_utils import (cast_table,
                        get_random_subtable,
                        load_table,
                        save_table)
from os import path
from collections import Counter
from json import dumps

DEFAULT_PROTECTION_LEVEL = 'pr_any'
DEFAULT_CLASSES = ['GA', 'FA']
DEFAULT_CLASS_VAR = 'ah_current' # ah_assessment_average

def json_print(data):
    return dumps(data, skipkeys=True, indent=2, sort_keys=True)


def create_parser():
    parser = argparse.ArgumentParser(description='Select')
    parser.add_argument('--protection_level', type=str, default=DEFAULT_PROTECTION_LEVEL,
                        help='Select articles without this protection level')
    parser.add_argument('--classes', type=str, action='append',
                        help='Select articles within these classes')
    parser.add_argument('--class_var', type=str, default=DEFAULT_CLASS_VAR,
                        help='Class attribute name')
    parser.add_argument('--attrfile', type=argparse.FileType('r'),
                        help='Module with list of attribute names to select')
    parser.add_argument('--output', type=argparse.FileType('w'),
                        help='output file name')
    parser.add_argument('input_file', nargs=1, type=argparse.FileType('r'),
                        help='input file')
    return parser


def select(input_file, protection_level, classes, class_var, attrfile, output):
    input_file_name = input_file[0].name
    input_file[0].close()
    in_data = load_table(input_file_name)
    if output is None:
        base, ext = path.splitext(input_file_name)
        output = base + '_selected' + ext
    if not classes:
        classes = DEFAULT_CLASSES
    if protection_level:
        protection_index = in_data.domain[protection_level]
        unprotected_index = [i for i, v in enumerate(in_data) if v[protection_index].native() != 'True']
        out_data = in_data.get_items(unprotected_index)
    kwargs = {}
    kwargs[class_var] = classes
    out_data = in_data.filter(**kwargs)
    out_data = cast_table(out_data, new_class_var=out_data.domain.class_var)
    if attrfile:
        in_data = cast_table(in_data, attr_selector=attrfile)
    save_table(output, out_data)
    return in_data, out_data


def main():
    parser = create_parser()
    args = parser.parse_args()
    kwargs = dict(args._get_kwargs())
    in_data, out_data = select(**kwargs)
    print len(in_data) - len(out_data), ' rows removed'
    print len(in_data.domain) - len(out_data.domain), ' attributes removed'
    print 'Input classes: \n', json_print(dict(Counter([x.get_class().native() for x in in_data])))
    print 'Output classes: \n', json_print(dict(Counter([x.get_class().native() for x in out_data])))
    import pdb; pdb.set_trace()

if __name__ == '__main__':
    main()
