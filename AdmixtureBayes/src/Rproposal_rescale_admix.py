from Rtree_operations import update_all_admixtures, get_number_of_admixes
from copy import deepcopy
from numpy.random import normal
from math import sqrt

class updater(object):
    
    def __init__(self, sigma):
        self.sigma=sigma

    def __call__(self):
        return normal(scale=self.sigma)

def rescale_admixtures(tree, sigma=0.01, pks={}):
    k=get_number_of_admixes(tree)
    pks['rescale_admixtures_param']=sigma
    new_tree=deepcopy(tree)
    if k>0:
        updat=updater(sigma/sqrt(k))
        new_tree=update_all_admixtures(new_tree, updat)
        if new_tree is None:
            return tree,1,0 #rejecting by setting backward jump probability to 0.
    else:
        return new_tree,1,0.234 #not to have to deal with the admix=0 case, I return 0.234 such that the adaptive parameter is not affected by these special cases.
    return new_tree ,1,1

class rescale_admixtures_class(object):
    new_nodes=0
    proposal_name='rescale_admixtures'
    
    def __call__(self, *args, **kwargs):
        return rescale_admixtures(*args, **kwargs)


if __name__=='__main__':
    from tree_plotting import plot_graph
    from Rcatalogue_of_trees import tree_on_the_border2_with_children
    plot_graph(tree_on_the_border2_with_children)
    new_tree=rescale(tree_on_the_border2_with_children)
    plot_graph(new_tree)
    
    print 'old_tree', tree_on_the_border2_with_children
    print 'new_tree', new_tree
    