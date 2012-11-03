import Orange

class DummyLearner(Orange.classification.Learner):
    def __init__(self, classifier, name=None):
        self.classifier = classifier
        if name is None:
            self.name = getattr(classifier, 'name', classifier.__class__.__name__ + 'DummyLearner')
        else:
            name = name
        
    def __call__(self, data, weight_id=None):
        # Screw weight id
        return self.classifier
    
out_learner = DummyLearner(in_classifier)