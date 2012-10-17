import Orange
from Orange import orange

def get_attr_names(in_table):
    return [a.name for a in in_table.domain.attributes]

def select_attributes(in_table, attr_selector):
    if callable(attr_selector):
        predicate = attr_selector
    elif hasattr(attr_selector, '__iter__') \
         and not isinstance(attr_selector, basestring):
        predicate = lambda x: x in attr_selector
    else:
        raise TypeError('expected an iterable of attribute names or callable predicate.')
        
    attrs = [a for a in in_table.domain.attributes if predicate(a.name)]
    new_domain = Orange.data.Domain(attrs, in_table.domain.class_var)
    new_domain.addmetas(in_table.domain.getmetas())
    return orange.ExampleTable(new_domain, in_table)


out_data = select_attributes(in_data, lambda x: x.startswith('dom'))