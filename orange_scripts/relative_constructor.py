import Orange
from Orange import orange
from Orange.regression.earth import EarthLearner

attrs = [attribute.name for attribute in in_data.domain.attributes if attribute.name.startswith('d_') and str(attribute.var_type) == 'Continuous']
rel_attrs = []

for attr in attrs:
    attr_name = 'w_per_' + attr
    rel_attrs.append(orange.FloatVariable(attr_name, getValueFrom=lambda i, r, n=attr: i[n] > 0.0 and i['d_word_count'] / i[n] or 0.0))

new_domain = Orange.data.Domain(rel_attrs, in_data.domain.class_var)
new_domain.addmetas(in_data.domain.getmetas())
out_data = orange.ExampleTable(new_domain, in_data)

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
out_classifier.name = 'rel_d_Earth'