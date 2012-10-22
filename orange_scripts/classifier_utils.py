import Orange
from Orange import orange


def get_test_results(classifiers, test_data):
    return Orange.evaluation.testing.test_on_data(classifiers, test_data)


