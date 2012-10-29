import data_utils
from collections import Counter
from Orange.clustering import kmeans
from Orange import distance
from functools import partial

if globals().get('in_data'):
    dom_data = data_utils.cast_table(in_data[0], attr_selector='d_')
    get_distance = distance.Euclidean(dom_data)
    
    fa_data = dom_data.filter(R_ah_current='FA')
    fa_cluster = kmeans.Clustering(fa_data, centroids=1)
    fa_centroid = fa_cluster.centroids[-1]
    
    ga_data = dom_data.filter(R_ah_current='GA')
    ga_cluster = kmeans.Clustering(ga_data, centroids=1)
    ga_centroid = ga_cluster.centroids[-1]
    
    ga_distance = data_utils.make_c_feature('dist_GA')
    get_ga_distance = partial(get_distance, ga_centroid)
    ga_distance.get_value_from = get_ga_distance
    
    fa_distance = data_utils.make_c_feature('dist_FA')
    get_fa_distance = partial(get_distance, fa_centroid)
    fa_distance.get_value_from = get_fa_distance
    
    out_data = cast_table(dom_data, new_attrs=[fa_distance, ga_distance])