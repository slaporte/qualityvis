from data_utils import cast_table, get_random_subtable
from distance_utils import get_redundant_attrs, compute_attr_dist_matrix

in_subtable = get_random_subtable(in_data, 1000)
data_distances = compute_attr_dist_matrix(in_subtable)

kept, dropped = get_redundant_attrs(data_distances, corr_lower=0.01, corr_upper=0.99)

out_data = cast_table(in_data, attr_selector=kept)
out_subtable = get_random_subtable(out_data, 1000)
out_distance = compute_attr_dist_matrix(out_subtable)

