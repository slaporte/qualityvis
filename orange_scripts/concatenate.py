import Orange
from argparse import ArgumentParser, FileType
import os

import data_utils

DEFAULT_EXTENSION = '.tab'
INIT_RANDOM_SEED = 0


def generate_output_filename(input_filenames, ext=None):
    from string import punctuation, whitespace
    if not input_filenames:
        raise ValueError('expected a list of at least one filename')
    prefixes = []
    for f_path in input_filenames:
        f_name = os.path.split(f_path)[1]
        prefix = [x for x in f_name.split(punctuation + whitespace) if x][0]
        prefix = prefix[:5]
        prefixes.append(prefix)
    sorted_prefixes = sorted(prefixes)
    if ext is None:
        _, ext = os.path.splitext(input_filenames[0])
        ext = ext or DEFAULT_EXTENSION
    return '_'.join(sorted_prefixes) + '_joined' + ext


def random_trim(in_table, count, use_refs=True):
    # Orange's random sampling API may be the worst I've ever seen
    exclude_count = len(in_table) - count
    if exclude_count <= 0:
        return in_table
    elif exclude_count == 1:
        exclude_count += 0.0001
    idx_selector = Orange.data.sample.SubsetIndices2(p0=exclude_count)
    if not getattr(in_table, 'random_generator', None):
        in_table.random_generator = Orange.misc.Random(INIT_RANDOM_SEED)
    idx_selector.random_generator = in_table.random_generator
    indices = [i for i, x in enumerate(idx_selector(in_table)) if x]
    if use_refs:
        return in_table.get_items_ref(indices)
    else:
        return in_table.get_items(indices)


def trunc_trim(in_table, count, use_refs=True):
    if len(in_table) <= count:
        return in_table
    indices = range(0, count)
    if use_refs:
        return in_table.get_items_ref(indices)
    else:
        return in_table.get_items(indices)


def concatenate(input_files, output=None, max_per=None, max_total=None, do_random=True):
    ap_files = [os.path.abspath(in_file.name) for in_file in input_files]
    for in_file in input_files:
        in_file.close()
    if not output:
        dir_path, _ = os.path.split(ap_files[0])
        output_filename = generate_output_filename(ap_files)
        output_path = os.path.join(dir_path, output_filename)
        output = open(output_path, 'w')
    output_filename = os.path.abspath(output.name)
    output.close()

    if do_random:
        table_trim = random_trim
    else:
        table_trim = trunc_trim

    tables = [data_utils.load_table(apf) for apf in ap_files]
    subtables = []
    for tab in tables:
        if max_per and len(tab) > int(max_per):
            tab = table_trim(tab, max_per)
        subtables.append(tab)

    concatted = data_utils.concatenate_tables(tables)
    if max_total and len(concatted) > int(max_total):
        concatted = table_trim(concatted, max_total)
    data_utils.save_table(output_filename, concatted)
    return


def create_parser():
    parser = ArgumentParser(description='concatenate and trim datasets')
    parser.add_argument('--max_per', type=int,
                        help='maximum number of rows to take from each file')
    parser.add_argument('--max_total', type=int,
                        help='maximum number of rows in the final dataset')
    parser.add_argument('--output', type=FileType('w'),
                        help='filename for the output dataset')
    parser.add_argument('--no_random', dest='do_random', action='store_false',
                        help='trim by truncation instead of random selection')
    parser.add_argument('input_files', nargs='+', type=FileType('r'))
    # TODO: deduplication key
    return parser

if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()
    kwargs = dict(args._get_kwargs())
    concatenate(**kwargs)
