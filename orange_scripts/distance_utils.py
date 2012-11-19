from __future__ import unicode_literals
from collections import Counter, defaultdict
from itertools import chain
from functools import partial

import Orange
from Orange.feature.scoring import Relief
from Orange.feature import Type
from Orange.clustering import kmeans
from Orange import distance

import data_utils


def get_relief_scores(data, k=10, m=400):
    # TODO: better k and n
    relief = Relief(k=k, m=m)
    return [(a, relief(a, data)) for a in data.domain.attributes]


def get_centered_value(data_points):
    counts = Counter([x.value for x in data_points])
    counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    majority_val, majority_count = counts[0]

    if data_points[0].var_type == Type.Continuous and \
            majority_count < 0.666*len(data_points):
        return sum([x.value for x in data_points], 0.0)/len(data_points)
    #elif data_points[0].var_type != Type.Discrete:
    #    raise ValueError('only supports Continuous and Discrete variables '
    #                     '(variable: '+data_points[0].variable.name+')')
    else:
       return majority_val


def get_class_centroids(data):
    try:
        c_var  = data.domain.class_var
        c_vals = c_var.values
    except AttributeError:
        raise ValueError('only works on discrete-classed datasets')
    domain = data.domain
    ret = []
    for cv in c_vals:
        c_data = data.filter_ref(**{c_var.name: cv})
        c_centroid = Orange.data.Instance(domain)
        for a in domain.attributes:
            attr_values = [x[a] for x in c_data]
            c_centroid[a] = get_centered_value(attr_values)
        ret.append((cv, c_centroid))
    return ret


def get_class_centroids_kmeans(data):
    try:
        c_var  = data.domain.class_var
        c_vals = c_var.values
    except AttributeError:
        raise ValueError('only works on discrete-classed datasets')
    domain = data.domain
    ret = []
    for cv in c_vals:
        c_data = data.filter_ref(**{c_var.name: cv})
        c_cluster = kmeans.Clustering(c_data, centroids=1)
        ret.append((cv, c_cluster.centroids[-1]))
    return ret


def get_sigmoid_func(func, data, sigma=2):
    "sigma is the theoretical 'width' of a standard deviation."

    res = [func(x) for x in data]
    avg_res = sum(res, 0.0) / len(res)
    variances = [(v - avg_res) ** 2 for v in res]
    variance = sum(variances, 0.0) / len(res)
    std_dev = variance ** 0.5
    old_func = func
    out_func = lambda x, rw=None: sigma*( old_func(x) - avg_res) / std_dev

    return out_func


def get_norm_func(func, data, avg_center=False, norm_scale=True, zero_center=False):
    if avg_center:
        res = [func(x) for x in data]
        avg_res = sum(res, 0.0) / len(res)
        variances = [(v - avg_res) ** 2 for v in res]
        variance = sum(variances, 0.0) / len(res)
        std_dev = variance ** 0.5
        old_func = func
        func = lambda x, rw=None: 2*( old_func(x) - avg_res) / std_dev

    if not norm_scale:
        return func

    res = [func(x) for x in data]
    max_res, min_res = max(res), min(res)
    if zero_center:
        return lambda x, rw=None: ((func(x) - min_res) / (max_res - min_res)) - 0.5
    else:
        return lambda x, rw=None: ((func(x) - min_res) / (max_res - min_res))


def get_norm_distance_func(centroid, data): # TODO: funcs other than Manhattan?
    dist_func = distance.Manhattan(data)
    dist_func = partial(dist_func, centroid)
    return get_norm_func(dist_func, data)


def _value_from_wrapper(function):
    return lambda example, return_what=None: function(example)


def get_norm_dist_features(data, prefix='dist_', norm_data=None):
    ret = []
    if norm_data is None:
        norm_data = data
    centroid_tuples = get_class_centroids(data)
    for c_val, c_centroid in centroid_tuples:
        c_dist_feat = data_utils.make_c_feature(prefix+c_val)
        norm_dist_func = get_norm_distance_func(c_centroid, norm_data)
        c_dist_feat.get_value_from = _value_from_wrapper(norm_dist_func)
        ret.append(c_dist_feat)
    return ret


def get_class_exemplars(data, ordered_class_vals, count=30):
    "count is per-class"
    ret = {}
    class_vals = data.domain.class_var.values
    assert set(class_vals) == set(ordered_class_vals) and \
        len(class_vals) == len(ordered_class_vals) # TODO try/except/bettermsg

    centroid_dict = dict(get_class_centroids(data))
    centroid_distances = {}
    dist_tuples = []
    for c_val in ordered_class_vals:
        c_centroid = centroid_dict[c_val]
        norm_dist_func = get_norm_distance_func(c_centroid, data)
        centroid_distances[c_val] = [norm_dist_func(x) for x in data]
    dist_tuples = zip(data, *centroid_distances.values())

    for i, c_val in enumerate(ordered_class_vals):
        if i == 0:
            sorted_dists = sorted(dist_tuples, key=lambda x: x[i+1]/x[-1] if x[-1] else 1.0)
        else:
            sorted_dists = sorted(dist_tuples, key=lambda x: x[i+1]/x[i] if x[i] else 1.0)
        ret[c_val] = [x[0] for x in sorted_dists[:count]]
    return ret


def get_exemplary_table(data, *a, **kw):
    exemplars = get_class_exemplars(data, *a, **kw)
    exemplar_set = set(chain.from_iterable(exemplars.values()))
    return data.get_items_ref([i for i,e in enumerate(data) if e in exemplar_set])


def get_exemplary_centroids(data, *a, **kw):
    exemplar_table = get_exemplary_table(data, *a, **kw)
    return get_class_centroids(exemplar_table)

from Orange.misc import SymMatrix

def compute_attr_dist_matrix(data):
    import numpy, statc

    attrs = data.domain.attributes
    matrix = SymMatrix(len(attrs))

    # why not just matrix.items = attrs?
    matrix.setattr(b'items', attrs)

    m = data.toNumpyMA("A")[0]
    averages = numpy.ma.average(m, axis=0)
    filleds = [list(numpy.ma.filled(m[:,i], averages[i])) for i in range(len(attrs))]
    for a1, f1 in enumerate(filleds):
        for a2 in range(a1):
            matrix[a1, a2] = (1.0 - statc.spearmanr(f1, filleds[a2])[0]) / 2.0
    return matrix


def get_redundant_attrs(attr_dists, corr_lower=0.001, corr_upper=0.999):
    """
    Returns a list of overcorrelated attribute names.
    Prioritizes the attributes with shortest name.
    """
    overcorrelated_dict = defaultdict(list)
    attrs = attr_dists.items
    for i, attr1 in enumerate(attrs):
        for j in range(0,i):
            attr2 = attrs[j]
            corr = attr_dists[i,j]
            if not corr_lower <= corr <= corr_upper:
                overcorrelated_dict[attr1.name].append((attr2.name, corr))
                overcorrelated_dict[attr2.name].append((attr1.name, corr))

    offender_list = sorted(overcorrelated_dict.items(), key=lambda x: len(x[1]), reverse=True)

    corr_sets = set()
    for attr, friends in overcorrelated_dict.items():
        corr_sets.add(frozenset([attr] + [f[0] for f in friends]))

    dropped_list = []
    for cs in corr_sets:
        long_attr_names = sorted(cs, key=lambda x: len(x))[1:]
        dropped_list.extend(long_attr_names)

    dropped_set = set(dropped_list)
    kept_list = [x.name for x in attrs if x.name not in dropped_set]

    return kept_list, list(dropped_set)
