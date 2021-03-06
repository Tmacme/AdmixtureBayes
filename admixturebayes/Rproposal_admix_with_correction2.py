from numpy.random import choice, random, exponential
from numpy import zeros, insert, identity
from copy import deepcopy
from scipy.special import binom
from Rtree_operations import (get_number_of_admixes, node_is_admixture, insert_admixture_node_halfly, 
                              get_descendants_and_rest, graft, remove_admix, node_is_non_admixture,
                              make_consistency_checks, parent_is_spouse, halfbrother_is_uncle,
                              parent_is_sibling, other_branch, get_branch_length, change_admixture,
                              get_all_branches, get_all_branch_descendants_and_rest, remove_admix2,
                              pretty_string, readjust_length,get_keys_and_branches_from_children,
                              update_branch_length, get_specific_branch_lengths, get_leaf_keys,
                              update_specific_branch_lengths)
from random import getrandbits
from scipy.stats import expon
from numpy.linalg.linalg import pinv
from numpy.linalg import matrix_rank
from Rtree_to_coefficient_matrix import make_coefficient_matrix
from scipy.stats import norm
from operator import mul
#from tree_plotting import 




def _get_possible_starters(tree):
    return get_all_branches(tree)

def _get_possible_sources(tree, children, other, sink_key, sink_branch):
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
            if tree[child][0] in other and (child!=sink_key or 0!=sink_branch):
                res.append((child,0))
            elif tree[child][1] is not None and tree[child][1] in other and (child!=sink_key or 1!=sink_branch):
                res.append((child,1))
    return res

class addadmix_class(object):
    
    new_nodes=2
    proposal_name='addadmix'
    adaption=False
    input='tree'
    require_admixture=0
    admixture_change=1
    reverse_require_admixture=1
    reverse='deladmix'
    
    def __call__(self,*args, **kwargs):
        return addadmix(*args, **kwargs)
    
class deladmix_class(object):
    
    new_nodes=0
    adaption=False
    proposal_name='deladmix'
    input='tree'
    require_admixture=1
    admixture_change=-1
    reverse_require_admixture=0
    reverse='addadmix'
    
    def __call__(self,*args, **kwargs):
        return deladmix(*args, **kwargs)
    
def float_equal(x,y):
    return float((x-y)**2)<1e-5

def getcorrection_deleting(old_tree, new_tree, sigma, branches, U_matrix):
    
    node_keys=sorted(get_leaf_keys(old_tree))
    
    A,_,_= make_coefficient_matrix(old_tree, node_keys=node_keys, branch_keys=branches)
    B,_,_= make_coefficient_matrix(new_tree, node_keys=node_keys, branch_keys=branches[:-3])
    
    
    x_A=get_specific_branch_lengths(old_tree, branches)
    x_B=get_specific_branch_lengths(new_tree, branches[:-3])
    
    A2=A.dot(U_matrix)
    
    lambd=pinv(B.dot(B.T)).dot(A2-B).dot(x_A[:-3])
    
    mu_new=(B.T).dot(lambd)+x_A[:-3]
    
    x_new = mu_new + norm.rvs(scale=sigma, size= len(mu_new))
    
    q_forward=reduce(mul, norm.pdf(mu_new-x_new, scale=sigma))
    
    x_new=U_matrix.dot(x_new_reduced)
    #print 'x_A', x_A
    #print 'x_B', x_B
    #print 'x_new', x_new
    
    reverse_lambd=pinv(A.dot(A.T)).dot(B2-A).dot(x_new_reduced)
    reverse_mu_new=(A.T).dot(reverse_lambd)+x_new_reduced
    
    #print 'matrix_rank , dimension (A)', matrix_rank(A), A.shape
    #print 'matrix_rank , dimension (B)', matrix_rank(B), B.shape
    #print 'x_reverse', reverse_mu_new
    
    q_backward=reduce(mul, norm.pdf(reverse_mu_new-x_A, scale=sigma))

    #wear the new values
    #print branches
    
    new_tree=update_specific_branch_lengths(new_tree,branches, x_new)
    
    return new_tree, q_forward, q_backward

def getcorrection_adding(old_tree, new_tree, sigma, branches, U_matrix):
    
    node_keys=sorted(get_leaf_keys(old_tree))
    
    A,_,_= make_coefficient_matrix(old_tree, node_keys=node_keys, branch_keys=branches[:-3])
    B,_,_= make_coefficient_matrix(new_tree, node_keys=node_keys, branch_keys=branches)
    
    
    x_A=get_specific_branch_lengths(old_tree, branches[:-3])
    x_B=get_specific_branch_lengths(new_tree, branches)
    
    B2=B.dot(U_matrix)
    
    lambd=pinv(B2.dot(B2.T)).dot(A-B2).dot(x_A)
    
    mu_new=(B2.T).dot(lambd)+x_A
    
    x_new_reduced=mu_new+norm.rvs(scale=sigma, size= len(mu_new))
    
    q_forward=reduce(mul, norm.pdf(mu_new-x_new_reduced, scale=sigma))
    
    x_new=U_matrix.dot(x_new_reduced)
    print 'x_A', x_A
    print 'x_B', x_B
    print 'mu_new', mu_new
    print 'x_new_reduced', x_new_reduced
    print 'x_new', x_new
    
    reverse_lambd=pinv(A.dot(A.T)).dot(B2-A).dot(x_new_reduced)
    reverse_mu_new=(A.T).dot(reverse_lambd)+x_new_reduced
    
    print 'matrix_rank , dimension (A)', matrix_rank(A), A.shape
    print 'matrix_rank , dimension (B)', matrix_rank(B), B.shape
    print 'mu_reverse', reverse_mu_new
    
    q_backward=reduce(mul, norm.pdf(reverse_mu_new-x_A, scale=sigma))

    #wear the new values
    #print branches
    
    new_tree=update_specific_branch_lengths(new_tree,branches, x_new)
    
    
    return new_tree, q_forward, q_backward


def addadmix(tree,new_node_names=None,pks={}, fixed_sink_source=None, new_branch_length=None, new_to_root_length=None, check_opposite=False, preserve_root_distance=True):
    '''
    This proposal adds an admixture to the tree. There are a lot of free parameters but only 5 are in play here:
        c1: the branch length of the source population
        c2: the branch length of the population genes are migrating into. 
        u1: the position of the admixture source on the source population branch
        u2: the position of the admixture destination on the sink population branch
        w: the admixture proportion.
        The connecting function, h, (see Green & Hastie 2009) is
            h(c1,c2,u1,u2,w)=(c1*u1, c1*(1-u1), c2*u2, c2*(1-u2), 0.5*w)
    '''
    
    possible_nodes=_get_possible_starters(tree)
        
    no_admixtures=get_number_of_admixes(tree)
    new_tree= deepcopy(tree)
    #print possible_nodes
    sink_key, sink_branch=possible_nodes[choice(len(possible_nodes), 1)[0]]
    if fixed_sink_source is not None:
        sink_key,sink_branch,source_key,source_branch = fixed_sink_source
    children, other= get_all_branch_descendants_and_rest(tree, sink_key, sink_branch)
    candidates=other+[('r',0)]
    ch= choice(len(candidates),1)[0]
    if fixed_sink_source is None:
        source_key, source_branch=candidates[ch]

    pks['sink_key']=sink_key
    pks['source_key']=source_key
    pks['source_branch']=source_branch
    pks['sink_branch']=sink_branch
    #print 'children', children
    #print 'candidates', candidates
    #print 'sink', (sink_key, sink_branch)
    #print 'source', (source_key,source_branch)
    #print 'new_tree',new_tree
    if fixed_sink_source is not None:
        new_tree, forward_density, backward_density, multip, U_matrix, branches= insert_admix(new_tree, source_key, source_branch, sink_key, sink_branch, pks=pks, new_branch_length=new_branch_length, new_to_root_length=new_to_root_length, preserve_root_distance=preserve_root_distance)
    elif new_node_names is None:
        new_tree, forward_density, backward_density, multip, U_matrix, branches= insert_admix(new_tree, source_key, source_branch, sink_key, sink_branch, pks=pks, preserve_root_distance=preserve_root_distance)
    else:
        new_tree, forward_density ,backward_density, multip, U_matrix, branches= insert_admix(new_tree, source_key, source_branch, sink_key, sink_branch, pks=pks, source_name=new_node_names[0], sink_name=new_node_names[1], preserve_root_distance=preserve_root_distance)
    
    
    choices_forward=float(len(possible_nodes)*len(candidates))*2
    choices_backward=float(len(_get_removable_admixture_branches(new_tree)))
    
    new_tree, qforward2, qbackward2 = getcorrection_adding(tree, new_tree, 0.1, branches, U_matrix)
    
    pks['forward_density']=forward_density
    pks['backward_density']=backward_density
    pks['forward_choices']=choices_forward
    pks['backward_choices']=choices_backward
    
    if check_opposite:
        pks2={}
        t,f,b=deladmix(new_tree,pks=pks2, fixed_remove=(pks['sink_new_name'], pks['sink_new_branch']), check_opposite=False, preserve_root_distance=preserve_root_distance)
        if (float_equal(forward_density,pks2['backward_density']) and 
            choices_forward==pks2['backward_choices'] and
            float_equal(backward_density, pks2['forward_density']) and
            choices_backward==pks2['forward_choices']):
            print 'test passed'
        else:
            print 'TEST FAILED'
            print forward_density, "==", pks2['backward_density'], ":", forward_density==pks2['backward_density']
            print backward_density, "==", pks2['forward_density'], ":", backward_density==pks2['forward_density']
            print choices_forward, "==", pks2['backward_choices'], ":", choices_forward==pks2['backward_choices']
            print choices_backward, "==", pks2['forward_choices'], ":", choices_backward==pks2['forward_choices']
            print pretty_string(tree)
            print pretty_string(new_tree)
            print pretty_string(t)
            for key, val in pks.items():
                print key, ': ', val
            print "-----------"
            for key, val in pks2.items():
                print key, ': ', val
            assert False

    return new_tree,forward_density/choices_forward*qforward2, backward_density/choices_backward*multip*qbackward2

    
def get_admixture_branch_length(x=None):
    if x is None:
        x=expon.rvs()
        return x, expon.pdf(x)
    else:
        return expon.pdf(x)
    
def get_root_branch_length(x=None):
    return get_admixture_branch_length(x)
    
def get_admixture_proportion(x=None):
    if x is None:
        return random(),1
    else: 
        return 1
    
def get_insertion_spot(x=None, length=1.0):
    if x is None:
        return random(), 1.0/length
    else:
        return 1.0/length
    

def insert_admix(tree, source_key, source_branch, sink_key, sink_branch, source_name=None, sink_name=None, pks={}, new_branch_length=None, new_to_root_length=None, preserve_root_distance=False):
    #print "new branch", new_branch_length
    branches=get_all_branches(tree)
    new_branches=deepcopy(branches)
    branch_indices={branch:n for n,branch in enumerate(branches)}
    no_branches=len(branches)
    U_matrix=identity(no_branches)
    branch_lengths=get_specific_branch_lengths(tree, branches)
    total_length=sum(branch_lengths)
    if sink_name is None:
        sink_name=str(getrandbits(128)).strip()
    if source_name is None:
        source_name=str(getrandbits(128)).strip()
    if source_key=='r':
        u1,q1=get_root_branch_length()
        if new_to_root_length is not None:
            u1,q1 = new_to_root_length, get_root_branch_length(new_to_root_length)
        U_matrix=insert(U_matrix, U_matrix.shape[0], [u1/total_length]*U_matrix.shape[1], axis=0)
    else:
        u1,q1=get_insertion_spot(length=get_branch_length(tree,source_key,source_branch))
        index=branch_indices[(source_key, source_branch)]
        insertion=[0]*U_matrix.shape[1]
        insertion[index]=1.0-u1
        U_matrix[index,index]=u1
        U_matrix=insert(U_matrix, U_matrix.shape[0], insertion, axis=0)
    branches.append((source_name, 0))
    
    u2,q2=get_insertion_spot(length=get_branch_length(tree,sink_key,sink_branch))
    index=branch_indices[(sink_key, sink_branch)]
    insertion=[0]*U_matrix.shape[1]
    insertion[index]=1.0-u2
    U_matrix[index,index]=u2
    #print U_matrix
    U_matrix=insert(U_matrix, U_matrix.shape[0], insertion, axis=0)
    branches.append((sink_name,0))

    if new_branch_length is not None:
        t4,q4= new_branch_length, get_admixture_branch_length(new_branch_length)
    else:
        t4,q4=get_admixture_branch_length()
    u3,q3=get_admixture_proportion()
    U_matrix=insert(U_matrix, U_matrix.shape[0], [t4/total_length]*U_matrix.shape[1], axis=0)
    branches.append((sink_name,1))
    
    tree=insert_admixture_node_halfly(tree, sink_key, sink_branch, u2, admix_b_length=t4, new_node_name=sink_name, admixture_proportion= u3)
    #print 'tree after inserting admixture', tree
    tree=graft(tree, sink_name, source_key, u1, source_name, source_branch, remove_branch=1)

    #print 'old_t1', tree[sink_name][3]
    if preserve_root_distance:
        tree[sink_name], multip=readjust_length(tree[sink_name])
    else:
        multip=1.0
    #print 'new_t1', tree[sink_name][3]
    
    new_branch=1
    if random()<0.5:
        new_branch=0
        tree[sink_name]=change_admixture(tree[sink_name])
        branches[-2:]=list(reversed(branches[-2:]))
    pks['t5']=t4
    pks['t1']=u1
    pks['sink_new_name']=sink_name
    pks['sink_new_branch']=new_branch    
    #print 'tree after grafting', tree
    return tree,q1*q2*q3*q4,1, multip, U_matrix, branches


def deladmix(tree,pks={}, fixed_remove=None, check_opposite=False, preserve_root_distance=True):
    '''
    Reversible Jump MCMC transition which removes a random admixture branch. This is the reverse of the other proposal in this file. 
    '''
    
    #making copy that we can erase branches from. 
    cop=deepcopy(tree)
    
    candidates=_get_removable_admixture_branches(cop)
    #print candidates
    if len(candidates)==0:
        return tree,1,1
    if fixed_remove is None:
        remove_key, remove_branch = candidates[choice(len(candidates),1)[0]]
    else:
        remove_key, remove_branch = fixed_remove
    pks['remove_key']=remove_key
    pks['remove_branch']=remove_branch
    #get_keys_and_branches_from_children()
    #print 'remove', (remove_key, remove_branch)
    
    new_tree, (t1,t2,t3,t4,t5), alpha = remove_admix2(cop, remove_key, remove_branch, pks=pks)
    #pks['sink_key']=sink_key
    #pks['sink_branch']=sink_branch
    #pks['removed_alpha']=alpha
    pks['t1']=t1
    pks['t2']=t2
    pks['t3']=t3
    pks['t4']=t4
    pks['t5']=t5
    
    if preserve_root_distance:
        #print t1
        multip=(alpha**2+(1.0-alpha)**2)
        old_length=t2+multip*t1
        t1=old_length-t2
        #print old_length, t1,t2
        child_key, child_branch= get_keys_and_branches_from_children(tree, remove_key)[0]
        update_branch_length(new_tree, child_key, child_branch, old_length)
    else:
        multip=1.0
    backward_density= get_backward_remove_density(t1,t2,t3,t4,t5, alpha)
    forward_density= 1.0
    
    forward_choices=float(len(candidates))
    backward_choices=float(get_possible_admixture_adds(new_tree, pks['orphanota_key'], pks['orphanota_branch']))*2
    pks['forward_choices']=forward_choices
    pks['backward_choices']=backward_choices
    pks['forward_density']=forward_density
    pks['backward_density']=backward_density
    
    
    
    if check_opposite:
        pks2={}
        if t4 is None:
            new_to_root_length=t3
        else:
            new_to_root_length=None
        t,f,b=addadmix(new_tree,pks=pks2, fixed_sink_source=(pks['orphanota_key'],
                                                             pks['orphanota_branch'],
                                                             pks['sorphanota_key'],
                                                             pks['sorphanota_branch']), 
                       new_branch_length=t5, new_to_root_length=new_to_root_length, check_opposite=False,
                       preserve_root_distance=preserve_root_distance)
        if (float_equal(forward_density,pks2['backward_density']) and 
            forward_choices==pks2['backward_choices'] and
            float_equal(backward_density,pks2['forward_density']) and
            backward_choices==pks2['forward_choices']):
            print 'test passed'
        else:
            print 'TEST FAILED'
            print forward_density, "==", pks2['backward_density'], ":", forward_density==pks2['backward_density']
            print backward_density, "==", pks2['forward_density'], ":", backward_density==pks2['forward_density']
            print forward_choices, "==", pks2['backward_choices'], ":", forward_choices==pks2['backward_choices']
            print backward_choices, "==", pks2['forward_choices'], ":", backward_choices==pks2['forward_choices']
            
            print pretty_string(tree)
            print pretty_string(new_tree)
            print pretty_string(t)
            for key, val in pks.items():
                print key, ': ', val
            print "----------------"
            for key, val in pks2.items():
                print key, ': ', val
            assert False
    
    return new_tree, forward_density/forward_choices, backward_density/backward_choices*multip



def get_backward_remove_density(t1,t2,t3,t4,t5, alpha):
    '''
    remembering this ugly sketch:
    
                parent_key          sparent_key
                    |                |
                    |t_1             | t_4
                    |   __---- source_key
                  rkey/   t_5       \
                    |                \t_3
                    |t_2          sorphanota_key  
                orphanota_key   

    we want to get the density of all the choices. If 't_4 is None', it is because source_key was the root. So we want to find the density of the insertion spot on the
    parent_key-orphanota_key branch (=u2) the insertion spot on the sorphanota_key-sparent_key branch (=u1) (which could be exponentially distributed. We also want the density of t5
    and the admixture proportion, alpha
    '''
    if t4 is None:
        u1=t3
        q1=get_root_branch_length(u1)
    else:
        q1=get_insertion_spot(t3, t3+t4)
    q2=get_insertion_spot(t2, t1+t2)
    q3=get_admixture_branch_length(t5)
    q4=get_admixture_proportion(alpha)
    
    return q1*q2*q3*q4
    

def get_possible_admixture_adds(tree, sink_key,sink_branch):
    possible_nodes=_get_possible_starters(tree)
    children, other= get_all_branch_descendants_and_rest(tree, sink_key, sink_branch)
    candidates=other+[('r',0)]
    return len(possible_nodes)*len(candidates)

def _check_node(tree,key,direction):
    parent_key=tree[key][direction]
    return ((parent_key=='r' or node_is_non_admixture(tree[parent_key])) and 
            not parent_is_spouse(tree, key, other_branch(direction)) and
            (parent_key=='r' or not halfbrother_is_uncle(tree, key, parent_key)) and
            (parent_key=='r' or not (parent_is_spouse(tree,key,direction) and parent_is_sibling(tree, key, direction))))
        
def _get_removable_admixture_branches(tree):
    res=[]
    for key, node in tree.items():
        if node_is_admixture(node):
            if _check_node(tree, key, 0):
                res.append((key,0))
            if _check_node(tree, key, 1):
                res.append((key, 1))
    return res


class Tester():
    
    def __init__(self, tree):
        self.tree=tree
        self.no_admixes=get_number_of_admixes(self.tree)
    
    def many_admixes(self, n=100):
        for i in xrange(n):
            self.tree=addadmix(self.tree, new_node_names=['n'+str(i)+a for a in ['o','n']])
            #plot_graph(self.tree)
            if self.no_admixes+1==get_number_of_admixes(self.tree):
                print 'INCREASED NUMBER OF ADMIXTURES BY ONE= '+'TRUE'
            else:
                print 'INCREASED NUMBER OF ADMIXTURES BY ONE= '+'FALSE'
            self.no_admixes=get_number_of_admixes(self.tree)
            ad=make_consistency_checks(self.tree, ['s1','s2','s3','s4'])
            if not ad[0]:
                print ad
                plot_graph(self.tree, drawing_name='bad.png')
                break
        plot_as_directed_graph(self.tree)
            
    def alternate_admixes(self, n=1000):
        for i in xrange(n):
            old_tree=deepcopy(self.tree)
            self.tree=addadmix(self.tree, new_node_names=['n'+str(i)+a for a in ['o','n']])
            if self.no_admixes+1==get_number_of_admixes(self.tree):
                print 'INCREASED NUMBER OF ADMIXTURES BY ONE= '+'TRUE'
            else:
                print 'INCREASED NUMBER OF ADMIXTURES BY ONE= '+'FALSE'
            ad=make_consistency_checks(self.tree, ['s1','s2','s3','s4'])
            if not ad[0]:
                print ad
                plot_graph(old_tree, drawing_name='good.png')
                plot_graph(self.tree, drawing_name='bad.png')
                break
            #plot_graph(self.tree)
            old_tree=deepcopy(self.tree)
            self.tree=deladmix(self.tree)
            if self.no_admixes==get_number_of_admixes(self.tree):
                print 'DECREASED NUMBER OF ADMIXTURES BY ONE= '+'TRUE'
            else:
                print 'DECREASED NUMBER OF ADMIXTURES BY ONE= '+'FALSE'
            #plot_graph(self.tree)
            print self.tree
            ad=make_consistency_checks(self.tree, ['s1','s2','s3','s4'])
            if not ad[0]:
                print ad
                plot_graph(old_tree, drawing_name='good.png')
                plot_graph(self.tree, drawing_name='bad.png')
                deladmix(old_tree)
                break
        
    

if __name__=="__main__":
    from tree_plotting import plot_as_directed_graph, plot_graph, pretty_print
    import Rtree_operations
    #plot_graph(Rtree_operations.tree_on_the_border2_with_children)
    #t=Tester(Rtree_operations.tree_on_the_border2_with_children)
    #t.many_admixes(10)
    from Rcatalogue_of_trees import tree_good, tree_one_admixture
    pks={}

    from Rtree_to_covariance_matrix import make_covariance
    print make_covariance(tree_good)
    newt,forw,backw=addadmix(tree_good,pks=pks, check_opposite=False, new_node_names=['g','h'], preserve_root_distance=True)
    print 'forw',forw
    print 'back',backw
    print 'pks',pks
    pretty_print(newt)
    print make_covariance(newt)
    
    pks={}
    newt,forw,backw=deladmix(newt,pks=pks, check_opposite=False, preserve_root_distance=True)
    print 'forw',forw
    print 'back',backw
    print 'pks',pks
    pretty_print(newt)
    print make_covariance(newt)
    
