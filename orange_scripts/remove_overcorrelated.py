from data_utils import cast_table
from distance_utils import get_redundant_attrs, compute_attr_dist_matrix

kept, dropped = get_redundant_attrs(in_distance)

out_data = cast_table(in_data, attr_selector=kept)
out_distance = compute_attr_dist_matrix(out_data)