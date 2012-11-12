import itertools
import warnings
from collections import Counter, OrderedDict, Mapping, Iterable

import Orange
from Orange import orange

# TODO: get_boolean_feature(new_feat_name, predicate, default=False)
class DiscreteValueMapper(object):
    """
    Maps from one value to another, based on a dictionary, primarily used
    in Feature.get_value_from scenarios.

    A class was used to get around pickling issues. Trained classifiers
    typically include a domain, which includes Features, which must all be
    picklable.
    """
    def __init__(self, source_feat_name, value_map, default):
        self.source_feat_name = source_feat_name
        self.value_map = value_map
        self.default = default

    def __call__(self, inst, r):
        try:
            val = inst[self.source_feat_name]
            if val.is_DK() or val.is_DC():
                return val.value
            real_value = val.value
        except (TypeError, AttributeError):
            # unknown attribute or no 'value' attribute
            return self.default
        return self.value_map.get(real_value, self.default)


def make_c_feature(name):
    """convenience method for Orange.feature.Descriptor.make"""
    ret, _ = Orange.feature.Descriptor.make(name,
                                            Orange.feature.Type.Continuous)
    return ret


def make_d_feature(name, values):
    """This is pretty fast and loose; there are cases where
    discrete features are incompatible, be careful."""
    ret, _ = Orange.feature.Descriptor.make(name,
                                            Orange.feature.Type.Discrete,
                                            unordered_values=values)
    return ret

# question: will a mars classifier trained to return a continuous score still
# return that score if the input instance has a discrete class?


def get_mapped_c_feature(source_feat_name, new_feat_name, value_map, default=0.0):
    ret = make_c_feature(new_feat_name)
    ret.get_value_from = DiscreteValueMapper(source_feat_name, value_map, default)

    ret.__dict__['source_feat_name'] = source_feat_name
    # custom; useful for sanity checking
    # use dict to get around warnings. easier than silly filters.

    return ret


def cast_domain(in_domain,
                attr_selector=None,
                new_attrs=None,
                new_class_var=None,
                keep_metas=True):

    if callable(attr_selector):
        predicate = attr_selector
    elif isinstance(attr_selector, basestring):
        predicate = lambda x: x.startswith(attr_selector)
    elif hasattr(attr_selector, '__iter__'):
        predicate = lambda x: x in attr_selector
    elif attr_selector is None:
        predicate = lambda x: True
    else:
        raise TypeError('expected an iterable of attribute names, callable'
                        'predicate, or feature name prefix.')

    if new_attrs is None:
        new_attrs = []
    old_attrs = in_domain.attributes.clone()
    all_attrs = old_attrs + new_attrs
    kept_attrs = [a for a in old_attrs if predicate(a.name)]
    kept_attrs.extend(new_attrs)

    old_class_var = in_domain.class_var
    if isinstance(new_class_var, basestring):
        matches = [a for a in all_attrs if a.name == new_class_var]
        new_class_var = matches[0]
    elif new_class_var is None:
        new_class_var = old_class_var

    new_domain = Orange.data.Domain(kept_attrs, new_class_var)
    if keep_metas:
        new_domain.addmetas(in_domain.getmetas())

    metas = new_domain.getmetas()
    if new_domain.class_var !=  old_class_var and old_class_var not in metas:
        new_meta_id = Orange.feature.Descriptor.new_meta_id()
        new_domain.add_meta(new_meta_id, old_class_var)
    return new_domain


def get_table_attr_names(in_table, incl_metas=True):
    # TODO: multiclass vars (in_table.domain.class_vars
    try:
        class_var = [in_table.domain.class_var]
    except AttributeError:
        class_var = []
    if incl_metas:
        metas = in_table.domain.getmetas().values()
    else:
        metas = []
    to_search = itertools.chain(in_table.domain.attributes,
                                metas,
                                class_var)
    return [a.name for a in to_search]


def cast_table(in_table,
               attr_selector=None,
               new_attrs=None,
               new_class_var=None,
               keep_metas=True):
    try:
        if new_class_var.source_feat_name not in get_table_attr_names(in_table):
            warnings.warn('Source feature for new class variable not present in source'
                          ' table domain.')
    except (TypeError, AttributeError):
        pass  # no source_feat_name available

    if isinstance(new_attrs, Mapping):
        new_attr_values = new_attrs.values()
        new_attrs = new_attrs.keys()
        if any([len(val_list) < len(in_table) for val_list in new_attr_values]):
            raise ValueError('Value lists for new attributes must be as long or'
                             ' longer than the number of examples in a table.')
    else:
        new_attr_values = None

    new_domain = cast_domain(in_table.domain, attr_selector, new_attrs, new_class_var, keep_metas)
    ret = Orange.data.Table(new_domain, in_table)

    # Will this cause problems with mutating examples that are in other tables?
    if new_attr_values:
        for i, attr in enumerate(new_attrs):
            for j, ex in enumerate(ret):
                ret[j][attr] = new_attr_values[i][j]
    return ret


def get_special_attr_ratio(data):
    ret = {}
    counter = Counter()
    attr_names = [a.name for a in data.domain.attributes]
    for i in data:
        counter.update([v.variable.name for v in i if v.is_special()])

    data_len = len(data)+0.0
    for an in attr_names:
        ret[an] = counter[an]/data_len
        ret = OrderedDict(sorted(ret.items(), key=lambda x: x[1], reverse=True))
    return ret


def clean_missing_data(data, attr_threshold=0.06):
    missing_attr_ratios = get_special_attr_ratio(data)
    kept_attrs = set()
    for k,v in missing_attr_ratios.items():
        if v < attr_threshold:
            kept_attrs.add(k)
    kept_attr_data = cast_table(data, attr_selector=kept_attrs)
    clean_instances = [i for i, x in enumerate(kept_attr_data) if not any([v.is_special() for v in x])]
    return kept_attr_data.get_items(clean_instances)


def purge_uniform_features(data, limit=2):
    feat_vals = dict([(x.name, set()) for x in data.domain.features])
    good_feats = set()
    for i, feat_name in enumerate(feat_vals):
        for inst in data:
            if feat_name in good_feats:
                continue
            feat_vals[feat_name].add(inst[i].value)
            if len(feat_vals[feat_name]) >= limit:
                good_feats.add(feat_name)

    return cast_table(data, attr_selector=list(good_feats))


def get_random_subtable(data, count=None):
    import random
    if count is None:
        count = len(data)/4 or len(data)
    else:
        count = min(len(data), count)
    random_indices = random.sample(range(len(data)), count)
    return data.get_items(random_indices)
