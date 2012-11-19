from data_utils import cast_table, make_c_feature
import distance_utils as d_utils

BASE_SCORES = {'FA': 0.9, 'GA':0.7}
SIGMA_WIDTH = 0.2/5

r_scores = d_utils.get_relief_scores(in_data)
r_scores.sort(key=lambda x: x[1], reverse=True)

narrow_data = cast_table(in_data, attr_selector=[x[0].name for x in r_scores[:40]])
dist_feats = d_utils.get_norm_dist_features(narrow_data)
exemplary_table = d_utils.get_exemplary_table(narrow_data, ['FA', 'GA'])
exem_dist_feats = d_utils.get_norm_dist_features(exemplary_table, 'dist_E', narrow_data)

out_data = cast_table(narrow_data, new_attrs=dist_feats+exem_dist_feats)

get_score_boost = lambda x, rw=None: (x['dist_EGA'] - x['dist_EFA']) / (x['dist_EGA'] + x['dist_EFA'])

get_score_boost_ga = d_utils.get_sigmoid_func(get_score_boost, out_data.filter_ref(R_ah_current='GA'), SIGMA_WIDTH)
get_score_boost_fa = d_utils.get_sigmoid_func(get_score_boost, out_data.filter_ref(R_ah_current='FA'), SIGMA_WIDTH)

score_boost_feat = make_c_feature('score_boost')
def bucketed_score_boost(ex, rw=None):
    if ex['R_ah_current'] == 'FA':
        return get_score_boost_fa(ex)
    else:
        return get_score_boost_ga(ex)
score_boost_feat.get_value_from = bucketed_score_boost
boosted_data = cast_table(out_data, new_attrs=[score_boost_feat])

total_score_feat = make_c_feature('total_score')
def total_score(ex, rw=None, base_scores=BASE_SCORES):
    base_score = base_scores[ex['R_ah_current'].value]
    return base_score + ex['score_boost']
total_score_feat.get_value_from = total_score
scored_data = cast_table(boosted_data, new_class_var=total_score_feat)

id_score_dict = dict([(x['id'].value, x.get_class().value) for x in scored_data])

est_score_feat = make_c_feature('est_score')
def lookup_score(ex, rw=None):
    return id_score_dict(ex['id'])
est_score_feat.get_value_from = lookup_score

out_data = cast_table(in_data, new_class_var=est_score_feat)
