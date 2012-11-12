import Orange
from Orange.evaluation import scoring

import data_utils

def get_test_results(classifiers, test_data):
    return Orange.evaluation.testing.test_on_data(classifiers, test_data, store_examples=True)


def get_accuracy_scores(tr):
    ret = {}
    metrics = { 'MSE': scoring.MSE(tr),
                'MAE': scoring.MAE(tr),
                'RAE': scoring.RAE(tr),
                'RSE': scoring.RSE(tr),
                'RRSE': scoring.RRSE(tr),
                'RMSE': scoring.RMSE(tr) }
    for i, cn in enumerate(tr.classifier_names):
        ret[cn] = dict([(mn, metrics[mn][i]) for mn in metrics])

    return ret


def test_results_to_table(tr, keep_metas=True, keep_attrs=False):
    attrs = []
    is_cont = tr.class_values is None # None if continuous, non-None if discrete

    new_attrs = {}
    for i, cn in enumerate(tr.classifier_names):
        feat_name = 'cls_'+cn
        if is_cont:
            feat = data_utils.make_c_feature(feat_name)
        else:
            feat = data_utils.make_d_feature(feat_name, tr.class_values) # TODO: untested
        new_attrs[feat] = [ r.classes[i] for r in tr.results ]

    try:
        orig_table = tr.examples
    except AttributeError:
        if keep_metas or keep_attrs:
            raise
        else:
            # did not use save_examples on test results, need to construct table from scratch
            # TODO
            raise

    if not keep_attrs:
        attr_selector = lambda x: False
    else:
        attr_selector = None

    return data_utils.cast_table(orig_table,
                                 new_attrs=new_attrs,
                                 attr_selector=attr_selector,
                                 keep_metas=keep_metas)
