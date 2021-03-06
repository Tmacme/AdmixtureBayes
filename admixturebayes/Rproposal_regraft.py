from copy import deepcopy
from numpy.random import choice, random, exponential
from scipy.stats import expon, uniform
from Rtree_operations import (get_parents, is_root, get_descendants_and_rest, 
node_is_non_admixture, has_child_admixture, insert_children_in_tree,
remove_parent_attachment, graft, node_is_admixture, get_real_parents, halfbrother_is_uncle,
get_branch_length, get_all_branch_descendants_and_rest, other_branch)
from random import getrandbits
#from os import urandom
#from tree_warner import check

def get_possible_regrafters(tree):
    res=[]
    for key in tree:
        parents=get_real_parents(tree[key])
        #print parents
        for branch, parent in enumerate(parents):
            #print key,(not is_root(parent)),node_is_non_admixture(tree[parent]),(not has_child_admixture(tree, parent))
            #if (not is_root(parent)) and node_is_non_admixture(tree[parent]) and (not has_child_admixture(tree, parent)):
            if parent=='r' or (node_is_non_admixture(tree[parent]) and not halfbrother_is_uncle(tree, key, parent)):
                res.append((key,branch))
    return res

def _get_possible_branches(tree, children, other):
    '''
    returns the keys of all non-rooted nodes, that can be grafted into.
    '''
    res=[]
    for oth in other:
        if oth in tree:
            res.append((oth,0))
            if tree[oth][1] is not None:
                res.append((oth,1))
    for child in children:
        if child in tree:
            if tree[child][0] in other:
                res.append((child,0))
            elif tree[child][1] is not None and tree[child][1] in other :
                res.append((child,1))
    
    #removing closed branches, that is branches from admixture to root or from leaves to root. Normally, they would get the position of root, but because they are indespensible, they get a closed category.
    #this clumsy exception suggests, that the root should have its own key in the tree.
    res=[(r,w) for r,w in res if tree[r][3+w]!='closed_branch']
    
    return res

class regraft_class(object):
    
    new_nodes=1
    proposal_name='regraft'
    input='tree'
    require_admixture=0
    reverse_require_admixture=0
    adaption=False
    reverse='regraft'
    admixture_change=0
    
    def __call__(self,*args, **kwargs):
        return make_regraft(*args, **kwargs)

def make_regraft(tree, new_node=None, pks={}):
    possible_nodes= get_possible_regrafters(tree)
    
    assert len(possible_nodes)>0, 'There were no regraft locations possible, which is strange because the root is regraftable and always look the same.'
    
    new_tree= deepcopy(tree)
    regraft_key, regraft_branch= possible_nodes[choice(len(possible_nodes), 1)[0]]
    pks['regraft_key']=regraft_key
    pks['regraft_branch']=regraft_branch
    #print 'regrafter', regrafter
    new_tree, remove_distrub, remove_val, remove_par = remove_parent_attachment(new_tree, regraft_key, regraft_branch)
    q_backward=back_density(remove_distrub, remove_val, remove_par)
    #pretty_print(new_tree)
    children, other= get_all_branch_descendants_and_rest(new_tree, regraft_key, regraft_branch)
    candidates=thin_out_sibling(new_tree, other, regraft_key)+[('r',0)]
    ch= choice(len(candidates),1)[0]
    recipient_key, recipient_branch=candidates[ch]
    #print 'regrafter', regraft_key, regraft_branch
    #print 'into_tree', candidates, candidates[ch]
    #print 'new_tree',new_tree
    new_tree, q_forward= regraft(new_tree, regraft_key, regraft_branch, recipient_key, new_node=new_node, which_branch=recipient_branch)
    #_, new_other =  get_descendants_and_rest(new_tree, regrafter)
    #print len(other), len(new_other)

    return new_tree, q_forward, q_backward

def thin_out_sibling(tree, branches, key):
#     print 'branches', branches
#     for r,w in branches:
#         if r!='r':
#             print r,w,tree[r][3+w]
    return [(r,w) for r,w in branches if (r!='r' and tree[r][3+w]!='closed_branch' and r!=key)]

def back_density(distrub, val, par):
    if distrub=='r':
        return expon.pdf(val)
    if distrub=='u':#this looks kind of contraintuitive
        return uniform.pdf(val, scale=par)
    
def simulate_and_forward_density(distrub, par=None):
    if distrub == 'r':
        insertion_spot=expon.rvs()
        q=expon.pdf(insertion_spot)
    else:
        insertion_spot=uniform.rvs()
        branch_length=par
        q=uniform.pdf(insertion_spot*branch_length,scale=branch_length)
    return insertion_spot, q

def regraft(tree, remove_key,remove_branch, add_to_branch, new_node=None,which_branch=0):
    
    if add_to_branch=='r':
        insertion_spot, q=simulate_and_forward_density('r')
    else:
        branch_length=get_branch_length(tree, add_to_branch,which_branch)
        #print branch_length
        insertion_spot, q=simulate_and_forward_density('u', branch_length)
    if new_node is None:
        new_node=str(getrandbits(68)).strip()
    tree=graft(tree, remove_key, add_to_branch, insertion_spot, new_node, which_branch, remove_branch=remove_branch)
    return tree,q

if __name__=='__main__':
    
    import Rcatalogue_of_trees
    from tree_plotting import plot_graph, pretty_print
    
    
#     before_illegal_tree={'a': ['n1', 'c', 0.5, 0.06604174100033824, 0.1, 's2', None], 'c': ['e', 'n2', 0.5, 0.1, 0.1, 'a', None], 'e': ['f', None, None, 0.05, None, 'c', 's3'], 'f': ['r', None, None, 0.02, None, 'n1', 'e'], 's3': ['e', None, None, 0.3, None, None, None], 's2': ['a', None, None, 0.05, None, None, None], 's1': ['n2', None, None, 0.1, None, None, None], 's4': ['n1', None, None, 0.3, None, None, None], 'n1': ['f', None, None, 0.18395825899966176, None, 'a', 's4'], 'n2': ['r', None, None, 1.9890637488986214, None, 'c', 's1']}
#     plot_graph(before_illegal_tree)
#     removed= remove_parent_attachment(before_illegal_tree, 'n1')[0]
#     print removed
#     nt=graft(removed, 'n1', 'a', 0.0001, 'hallo', 1)
#     plot_graph(nt)
    
    tree2={'a': ['n5', 'c', 0.5, 0.07182199688586655, 0.1, 's2', None], 'c': ['n2', 'r', 0.5, 0.15000000000000002, 0.15000000000000002, 'a', None], 'b': ['n4', None, None, 0.0032455783560232784, None, 'n5', 's4'], 's3': ['n5', None, None, 0.2930455087788524, None, None, None], 's2': ['a', None, None, 0.05, None, None, None], 's1': ['n4', None, None, 0.10695449122114763, None, None, None], 's4': ['b', None, None, 0.3, None, None, None], 'n2': ['r', None, None, 0.0596819405846814, None, 'n4', 'c'], 'n4': ['n2', None, None, 0.007072481059295323, None, 'b', 's1'], 'n5': ['b', None, None, 0.12817800311413347, None, 'a', 's3']}
    
    print _get_possible_regrafters(tree2)
    
    #tr=insert_children_in_tree(Rcatalogue_of_trees.tree_on_the_border2)
    #tr1=deepcopy(tr)
    #for i in range(10000):
        #print 'before', tr
        #try:
        #tr=make_regraft(tr, new_node='n'+str(i+1))[0]
        #except Exception as e:
        #    print e
        #    plot_graph(tr, drawing_name=str(i)+'.png')
        #    tr=make_regraft(tr, new_node='n'+str(i+1))
        #    break
        #print 'after', tr
    newt=Rcatalogue_of_trees.tree_good
    print _get_possible_regrafters(newt)
    for _ in range(200):
        newt,forw,backw= make_regraft(newt)
        print 1*(forw<backw), 'for-bac',forw,backw
    pretty_print(newt)
    
    #plot_graph(tree_final)
    