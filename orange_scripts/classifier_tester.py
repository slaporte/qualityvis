import Orange
import evaluation_utils as ev_utils

tr = ev_utils.get_test_results(in_classifiers, in_data[0])

acc_scores = ev_utils.get_accuracy_scores(tr)
# Orange.evaluation.scoring.R2(tr)

estimate_table = ev_utils.test_results_to_table(tr)
out_data = estimate_table