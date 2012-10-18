import Orange

class WeightedStackedClassifier(Orange.classification.Classifier):
    def __init__(self, cf_weight_map, name='WeightedStackedClassifier'):
        self.name = name
        if not cf_weight_map:
            raise ValueError('expected a mapping of classifiers to weights (use 0 for default weight).')
        self.cf_weight_map = cf_weight_map
        total_weight = sum([float(w) for w in cf_weight_map.values()], 0.0)
        if total_weight == 0.0:
            total_weight = float(len(cf_weight_map))
            for cf, weight in self.cf_weight_map.items():
                self.cf_weight_map[cf] = 1 / total_weight
        else:
            for cf, weight in self.cf_weight_map.items():
                self.cf_weight_map[cf] = weight/total_weight
        self.total_weight = total_weight
        
    def __call__(self, *a, **kw):
        cf_votes = {}
        vote_dict = {}
        value_res_map = {}
        for cf, weight in self.cf_weight_map.items():
            res = cf(*a, **kw)
            cf_votes[cf] = res
            try:
                res_key = getattr(res, 'value', None) or res[0].value
            except AttributeError:
                print repr(type(res)), repr(res),
                
            try:
                vote_dict[res_key] += weight
                value_res_map[res_key] = res
            except KeyError:
                vote_dict[res_key] = weight
                value_res_map[res_key] = res
        sorted_res = sorted(vote_dict.items(), key=lambda x: x[1])
        if len(sorted_res) > 2:
            print '!!!! this is not a good thing', repr(sorted_res)
        return value_res_map[sorted_res[-1][0]]
    
cf_weight_map = dict([ (cf, 0) for cf in in_classifiers])
if cf_weight_map:
    out_classifier = WeightedStackedClassifier(cf_weight_map)