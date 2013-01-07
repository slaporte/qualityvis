import Orange
from data_utils import (cast_table,
                        get_random_subtable,
                        load_table,
                        save_table,
                        clean_missing_data,
                        purge_uniform_features)
from distance_utils import get_redundant_attrs, compute_attr_dist_matrix
from os import path
import argparse

DEFAULT_CORR_MIN = 0.01
DEFAULT_CORR_MAX = 0.99
DEFAULT_SUBTABLE_LEN = 1000


def create_parser():
    parser = argparse.ArgumentParser(description='decorrelate')
    parser.add_argument('--corr_min', type=float, default=DEFAULT_CORR_MIN,
                        help='correlation minimum')
    parser.add_argument('--corr_max', type=float, default=DEFAULT_CORR_MAX,
                        help='correlation maximum')
    parser.add_argument('--subtable_limit', type=int, default=DEFAULT_SUBTABLE_LEN,
                        help='subtable size for computing attribute distance matrix')
    parser.add_argument('--out_file', type=argparse.FileType('w'),
                        help='output file name')
    parser.add_argument('input_file', nargs=1, type=argparse.FileType('r'),
                        help='input file')
    return parser


def decorrelate_data(input_file, corr_min=DEFAULT_CORR_MIN, corr_max=DEFAULT_CORR_MAX, subtable_limit=DEFAULT_SUBTABLE_LEN, out_file=None):
    input_file_name = input_file[0].name
    input_file[0].close()
    in_data = load_table(input_file_name)
    if out_file is None:
        base, ext = path.splitext(input_file_name)
        out_file = base + '_decorrelated' + ext
    c_vars = [a.name for a in in_data.domain if a.var_type == Orange.feature.Type.Continuous]
    out_data = cast_table(in_data, attr_selector=c_vars)
    clean_data = clean_missing_data(out_data)
    out_data = purge_uniform_features(clean_data)
    if len(out_data) > subtable_limit:
        in_subtable = get_random_subtable(out_data, subtable_limit)
    else:
        in_subtable = out_data
    data_distances = compute_attr_dist_matrix(in_subtable)
    kept, dropped = get_redundant_attrs(data_distances, corr_lower=corr_min, corr_upper=corr_max)
    out_data = cast_table(out_data, attr_selector=kept)
    #out_subtable = get_random_subtable(out_data, DEFAULT_SUBTABLE_LEN)
    #compute_attr_dist_matrix(out_subtable)
    save_table(out_file, out_data)
    return in_data, out_data


def main():
    parser = create_parser()
    args = parser.parse_args()
    kwargs = dict(args._get_kwargs())
    in_data, out_data = decorrelate_data(**kwargs)
    print len(in_data) - len(out_data), ' rows removed'
    print len(in_data.domain) - len(out_data.domain), ' attributes removed'


if __name__ == '__main__':
    main()
