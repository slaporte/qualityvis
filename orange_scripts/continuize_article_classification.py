import data_utils

CLASS_SCORES = { 'FA': 0.9, 'GA': 0.5 }

c_feat = data_utils.get_mapped_c_feature('R_ah_current', 'C_ah_current', CLASS_SCORES)

out_data = data_utils.cast_table(in_data, new_class_var=c_feat)