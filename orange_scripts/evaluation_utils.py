import Orange
from Orange import orange

from collections import Counter
import data_utils
from stats import dist_stats # TODO: module/PATH structure gettin really ugly now

def get_test_results(classifiers, test_data):
    return Orange.evaluation.testing.test_on_data(classifiers, test_data, store_examples=True)


def get_one_accuracy_score(scores,
                           target_mean,
                           target_stddev=0.2,
                           target_skewness=0.3,
                           target_kurtosis=2.5):
    s_stats = dist_stats(scores)
    mean_comp = 0.5 * min(1.0, abs((target_mean - s_stats['mean'])/target_mean))
    stddev_comp = 0.25 * min(1.0, abs((target_stddev - s_stats['std_dev'])/target_stddev))
    skew_comp = 0.15 * min(1.0, abs((target_skewness - s_stats['skewness'])/target_skewness))
    kurt_comp = 0.1 * min(1.0, abs((target_kurtosis - s_stats['kurtosis'])/target_kurtosis))
    
    return 1.0 - (mean_comp + stddev_comp + skew_comp + kurt_comp)


def get_accuracy_scores(tr, verbose=True):
    "tr = Test Results (an ExperimentResults object)"
    ret = []
    actual_classes = Counter([r.actual_class for r in tr.results])
    if len(actual_classes) > 200:
        raise TypeError("probably too many actual class values for get_accuracy_scores()")
    
    for i, cn in enumerate(tr.classifier_names):
        weighted_c_score_sum = 0.0
        for ac, ac_count in actual_classes.items():
            # separate estimates for each class
            c_estimates = [r.classes[i] for r in tr.results if r.actual_class == ac]
            acc_score = get_one_accuracy_score(c_estimates, ac) # TODO: custom moments for each class?
            if verbose:
                print '   ',cn,'classifier accuracy for',ac,': ', acc_score
            weighted_c_score_sum += (acc_score*ac_count)/len(c_estimates)
        classifier_score = weighted_c_score_sum/len(actual_classes)
        ret.append(classifier_score)
        if verbose:
            print 'Overall accuracy for', cn,': ',classifier_score 
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

        
