from Rtree_operations import (find_rooted_nodes, get_leaf_keys, node_is_admixture, node_is_leaf_node, 
                              get_branch_length, get_admixture_proportion_from_key, get_children,
                              mother_or_father, other_branch)
from scipy.stats import uniform, norm
from copy import deepcopy
from numpy import clip, cov, array, mean
from math import sqrt

def add_noise(p,branch_length):
    #return add_noise2(p, branch_length)
    sd=sqrt(branch_length)
    print 'sd',sd
    p=[a+norm.rvs(scale=sd) if 0<a<1 else a for a in p ]
    p=clip(p,0,1)
    return p

def add_noise2(p, branch_length):
    sd=sqrt(branch_length)
    p=[a+norm.rvs(scale=sd) for a in p ]
    return p

def merge_ps(w, p1,p2):
    #print p1
    #print p2
    res=[w*a+(1-w)*b for a,b in zip(p1,p2)]
    #print res
    return res

def produce_p_matrix(tree, nSNP):
    
    ps=uniform.rvs(size=nSNP)*0.2+0.4
    ps2=deepcopy(ps)
    p_org=deepcopy(ps)
    res={}
    (child_key1, child_branch1,l1),(child_key2, child_branch2, l2)=find_rooted_nodes(tree)
    
    ready_lineages=[(child_key1, child_branch1, ps), (child_key2, child_branch2, ps2)]
    started_admixtures={}
    
    while ready_lineages:
        k,b,p = ready_lineages.pop()
        branch_length=get_branch_length(tree,k,b)
        branch=(k,b)
        p=add_noise(p,branch_length)
        node=tree[k]
        children=get_children(node)
        if node_is_leaf_node(node):
            res[k]=p
        elif node_is_admixture(node):
            mate=(k,other_branch(b))
            if mate in started_admixtures:
                w=get_admixture_proportion_from_key(tree, k)
                p=merge_ps(w*(1-b)+b*(1-w), p, started_admixtures[mate])
                del started_admixtures[mate]
                k_new=children[0]
                b_new=mother_or_father(tree, k_new, k)
                ready_lineages.append((k_new, b_new, p))
            else:
                started_admixtures[branch]=p
        else:
            for child in children:
                k_new=child
                b_new=mother_or_father(tree, k_new, k)
                ready_lineages.append((k_new,b_new,p))
    return res

def calculate_covariance_matrix_from_p(ps, nodes=None):
    p_mat=[]
    if nodes is None:
        nodes=ps.keys()
    for node in nodes:
        p_mat.append(ps[node])
    m=array(p_mat)-mean(p_mat, axis=0)
    return cov(m)

if __name__=='__main__':
    from Rtree_operations import create_trivial_tree
    from generate_prior_trees import generate_phylogeny
    from Rtree_to_covariance_matrix import make_covariance
    tree=generate_phylogeny(3,1)
    nodes=['s1','s2','s3']
    print make_covariance(tree, node_keys=nodes)
    p=produce_p_matrix(tree,11)
    print p
    print calculate_covariance_matrix_from_p(p, nodes=nodes)
        
    
    