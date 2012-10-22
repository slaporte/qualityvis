import itertools
import warnings

import Orange
from Orange import orange

"""
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
metas = in_data.domain.getmetas()
new_domain.addmetas(metas)

old_class_var = in_data.domain.class_var
if new_domain.class_var != old_class_var and old_class_var not in metas:
    new_meta_id = Orange.feature.Descriptor.new_meta_id()
    new_domain.add_meta(new_meta_id, old_class_var)

out_data = orange.ExampleTable(new_domain, in_data)
"""

# TODO: get_boolean_feature(new_feat_name, predicate, default=False)
class DiscreteValueMapper(object):
    """
    Maps from one value to another, based on a dictionary, primarily used
    in Feature.get_value_from scenarios.
    
    A class was used to get around pickling issues. Trained classifiers
    typically include a domain, which includes Features, which must all be
    picklable.
    """
    def __init__(self, source_feat_name, value_map, default):
        self.source_feat_name = source_feat_name
        self.value_map = value_map
        self.default = default

    def __call__(self, inst, r):
        try:
            val = inst[self.source_feat_name]
            if val.is_DK() or val.is_DC():
                return val.value
            real_value = val.value
        except (TypeError, AttributeError):
            # unknown attribute or no 'value' attribute
            return self.default
        return self.value_map.get(real_value, self.default)

    
def make_c_feature(name):
    """convenience method for Orange.feature.Descriptor.make"""
    ret, _ = Orange.feature.Descriptor.make(name,
                                            Orange.feature.Type.Continuous)
    return ret

# question: will a mars classifier trained to return a continuous score still
# return that score if the input instance has a discrete class?


def get_mapped_c_feature(source_feat_name, new_feat_name, value_map, default=0.0):
    ret = make_c_feature(new_feat_name)
    ret.get_value_from = DiscreteValueMapper(source_feat_name, value_map, default)

    ret.__dict__['source_feat_name'] = source_feat_name
    # custom; useful for sanity checking
    # use dict to get around warnings. easier than silly filters.
    
    return ret


def cast_domain(in_domain, attr_selector=None, new_class_var=None, keep_metas=True):
    if new_class_var is None:
        new_class_var = in_domain.class_var

    if callable(attr_selector):
        predicate = attr_selector
    elif isinstance(attr_selector, basestring):
        predicate = lambda x: x.startswith(attr_selector)
    elif hasattr(attr_selector, '__iter__'):
        predicate = lambda x: x in attr_selector
    elif attr_selector is None:
        predicate = lambda x: True
    else:
        raise TypeError('expected an iterable of attribute names, callable'
                        'predicate, or feature name prefix.')

    old_attrs = in_domain.attributes.clone()
    old_class_var = in_domain.class_var
    
    new_attrs = [a for a in old_attrs if predicate(a.name)]
    
    new_domain = Orange.data.Domain(new_attrs, new_class_var)
    if keep_metas:
        new_domain.addmetas(in_domain.getmetas())
        
    metas = new_domain.getmetas()
    if new_domain.class_var !=  old_class_var and old_class_var not in metas:
        new_meta_id = Orange.feature.Descriptor.new_meta_id()
        new_domain.add_meta(new_meta_id, old_class_var)
    return new_domain


def get_table_attr_names(in_table, incl_metas=True):
    # TODO: multiclass vars (in_table.domain.class_vars
    try:
        class_var = [in_table.domain.class_var]
    except AttributeError:
        class_var = []
    if incl_metas:
        metas = in_table.domain.getmetas().values()
    else:
        metas = []
    to_search = itertools.chain(in_table.domain.attributes,
                                metas,
                                class_var)
    return [a.name for a in to_search]


# new_attrs/precompute
# if precompute, make dictionary of new features to calculation functions
#      and set get_value_from to None on all new features
# 
# finally: re-set all get_value_from operations
def cast_table(in_table, attr_selector=None, new_class_var=None, keep_metas=True):
    try:
        if new_class_var.source_feat_name not in get_table_attr_names(in_table):
            warnings.warn('Source feature for new class variable not present in source'
                          ' table domain.')
    except (TypeError, AttributeError):
        pass  # no source_feat_name available
            
    new_domain = cast_domain(in_table.domain, attr_selector, new_class_var, keep_metas)
    return Orange.data.Table(new_domain, in_table)
