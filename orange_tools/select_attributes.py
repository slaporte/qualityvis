import Orange
from Orange import orange

def get_attr_names(in_table):
    return [a.name for a in in_table.domain.attributes]

def select_attributes(in_table, attr_names):
    attrs = [a for a in in_table.domain.attributes if a.name in attr_names]
    new_domain = Orange.data.Domain(attrs, in_table.domain.class_var)
    new_domain.addmetas(in_table.domain.getmetas())
    return orange.ExampleTable(new_domain, in_table)

def remove_attributes(in_table, predicate):
    attr_names = get_attr_names(in_table)
    return select_attributes(in_table, [a for a in attr_names if predicate(a)])


out_data = remove_attributes(in_data, lambda x: not x.startswith('ah_'))