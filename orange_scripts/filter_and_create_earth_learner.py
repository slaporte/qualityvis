from data_utils import cast_table
from Orange.regression.earth import EarthLearner

if globals().get('in_data'):
    out_data = cast_table(in_data, attr_selector='rv_wo_undid_')

    out_classifier = EarthLearner(out_data, 
        degree=1, 
        terms=30, 
        penalty=1.0, 
        thresh=0.001, 
        min_span=0, 
        new_var_penalty=1, 
        fast_k=20, 
        fast_beta=1, 
        store_instances=False)
    out_classifier.name = 'rv_Earth'