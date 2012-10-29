from data_utils import cast_table, make_c_feature
import distance_utils as d_utils

no_rv_data = cast_table(in_data, attr_selector=lambda x: not x.startswith('rv_') and not x.startswith('times_'))

r_scores = d_utils.get_relief_scores(no_rv_data)
r_scores.sort(key=lambda x: x[1], reverse=True)

narrow_data = cast_table(no_rv_data, attr_selector=[x[0].name for x in r_scores[:40]])
dist_feats = d_utils.get_norm_dist_features(narrow_data)
exemplary_table = d_utils.get_exemplary_table(narrow_data, ['FA', 'GA'])
exem_dist_feats = d_utils.get_norm_dist_features(exemplary_table, 'dist_E', narrow_data)

out_data = cast_table(narrow_data, new_attrs=dist_feats+exem_dist_feats)


get_score_boost = lambda x, rw=None: (x['dist_EGA'] - x['dist_EFA']) / (x['dist_EGA'] + x['dist_EFA'])
get_score_boost_ga = d_utils.get_norm_func(get_score_boost, out_data.filter_ref(R_ah_current='GA'),
avg_center=True,
norm_scale=True,
zero_center=True)
get_score_boost_fa = d_utils.get_norm_func(get_score_boost, out_data.filter_ref(R_ah_current='FA'),
avg_center=True,
norm_scale=True,
zero_center=True)
score_boost_feat = make_c_feature('score_boost')
def bucketed_score_boost(ex, rw=None):
    if ex['R_ah_current'] == 'FA':
        return get_score_boost_fa(ex)
    else:
        return get_score_boost_ga(ex)
score_boost_feat.get_value_from = bucketed_score_boost


out_data = cast_table(out_data, new_attrs=[score_boost_feat])
