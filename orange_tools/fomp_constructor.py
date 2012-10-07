import Orange
from Orange import orange
attributes = [a for a in in_data.domain.attributes if 'trimmed' not in a.name and 'kurtosis' not in a.name and 'skewness' not in a.name and 'variance' not in a.name and not a.name.startswith('rv_')]

fomp = Orange.feature.Discrete("fomp", values=['True', 'False'])    

def check_fomp(inst, return_what):
    try:
        if inst['ah_mainpage_age'] > 0 and inst['ah_current'] == 'FA': 
            return fomp('True')
        else:
            return fomp('False') 
    except TypeError:
        return fomp('False')

fomp.get_value_from = check_fomp

new_domain = Orange.data.Domain(attributes, in_data.domain.class_var)
new_domain.addmetas(in_data.domain.getmetas())
out_data = orange.ExampleTable(new_domain, in_data)