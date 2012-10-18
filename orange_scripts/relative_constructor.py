import Orange
from Orange import orange

attrs = [attribute.name for attribute in in_data.domain.attributes if attribute.name.startswith('d_') and str(attribute.var_type) == 'Continuous']
rel_attrs = []

for attr in attrs:
    attr_name = 'w_per_' + attr
    rel_attrs.append(orange.FloatVariable(attr_name, getValueFrom=lambda i, r, n=attr: i[n] > 0.0 and i['d_word_count'] / i[n] or 0.0))

new_domain = Orange.data.Domain(rel_attrs, in_data.domain.class_var)
new_domain.addmetas(in_data.domain.getmetas())
out_data = orange.ExampleTable(new_domain, in_data)