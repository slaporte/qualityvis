import Orange
from Orange import orange
attributes = in_data.domain.attributes.clone()

C_ah_current = Orange.feature.Continuous("C_ah_current")    

def c_ah(inst, r):
    if inst['R_ah_current'] == 'FA':
        return 0.9
    elif inst['R_ah_current'] == 'GA':
        return 0.5
    else:
        return 0.0

C_ah_current.get_value_from = c_ah

new_domain = Orange.data.Domain(attributes, C_ah_current)
new_domain.addmetas(in_data.domain.getmetas())
out_data = orange.ExampleTable(new_domain, in_data)