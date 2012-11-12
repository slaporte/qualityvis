from data_utils import cast_table
from mdp.nodes import FANode
from Orange.data import Table, Domain
import Orange

fa_node = FANode(max_cycles=500, verbose=True)

dom_data = cast_table(in_data, attr_selector='d_')
dom_stats = Orange.statistics.basic.Domain(dom_data)
new_attrs = []
for attr in dom_data.domain.features:
    attr_c = Orange.feature.Continuous(attr.name + "_n")
    attr_c.getValueFrom = Orange.classification.ClassifierFromVar(whichVar=attr)
    transformer = Orange.data.utils.NormalizeContinuous()
    attr_c.getValueFrom.transformer = transformer
    transformer.average = dom_stats[attr].avg
    transformer.span = dom_stats[attr].dev
    new_attrs.append(attr_c)

new_domain = Orange.data.Domain(new_attrs, dom_data.domain.classVar)
norm_dom_data = Orange.data.Table(new_domain, dom_data)

fa_res = fa_node.execute(norm_dom_data.to_numpy()[0])
out_data = Table(fa_node.A)

from stats import dist_stats
in_domain = norm_dom_data.domain
LATENT_COUNT = min(len(in_domain.attributes)/2, len(fa_node.A))
latent_attrs = []
weights = fa_node.A.transpose()
for i in range(LATENT_COUNT):
    cur_weights = weights[i]
    abs_stats = dist_stats([abs(x) for x in cur_weights])
    median = abs_stats['mean']
    dev_cutoff = abs_stats['std_dev']
    latent_attrs.append([(in_domain[i], x) for i, x in enumerate(cur_weights) if abs(x) > median+dev_cutoff])
    
#sorted([(a,b) for a,b in zip(in_domain.features, fa_node.sigma)], key=lambda x: x[1], reverse=True)