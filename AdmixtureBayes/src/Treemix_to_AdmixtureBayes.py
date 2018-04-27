import subprocess
from copy import deepcopy
#from newick import parse_tree
from Rtree_operations import (pretty_string, insert_children_in_tree, insert_admixture_node_halfly, 
                              graft, rearrange_root, get_leaf_keys,remove_outgroup, rename_key,
                              node_is_admixture, get_real_children, prune_double_nodes, rename_rootname,
                              mother_or_father, remove_children,rearrange_root_foolproof)
from meta_proposal import new_node_naming_policy
#from tree_plotting import plot_graph
from construct_covariance_choices import save_stage
import warnings
import os
from tree_to_data import unzip, gzip



class vertice_dictionary():
    
    TYPES=['Treemix_V',
           'Treemix_N',
           'AdmB']
    
    def __init__(self):
        
        self.treemix_numbered_vertices=[]
        self.treemix_newick_format=[]
        self.admixture_string_nodes=[]
        
        
        
    def get_list(self, type):
        if type==vertice_dictionary.TYPES[0]:
            return self.treemix_numbered_vertices
        elif type==vertice_dictionary.TYPES[1]:
            return self.treemix_newick_format
        elif type==vertice_dictionary.TYPES[2]:
            return self.admixture_string_nodes
        else:
            assert False, 'wrong type provided'
    
    def get_3_lists(self, type1, type2, type3=None):
        available_types=deepcopy(vertice_dictionary.TYPES)
        list1=self.get_list(type1)
        available_types.remove(type1)
        list2=self.get_list(type2)
        available_types.remove(type2)
        list3=self.get_list(available_types[0])
        return list1,list2,list3
            
            
    def insert_mapping(self, from_object, to_object, from_type, to_type):
        from_list, to_list, third_list=self.get_3_lists(from_type, to_type)
        index=None
        if from_object in from_list:
            index=from_list.index(from_object)
        if to_object in to_list:
            index=to_list.index(to_object)
        if index is None:
            from_list.append(from_object)
            to_list.append(to_object)
            third_list.append(None)
        else:
            #print 'index',index
            if from_object in from_list:
                to_list[index]=to_object
            if to_object in to_list:
                from_list[index]=from_object

    def get_value(self, from_object, from_type, to_type):
        from_list, to_list, _ = self.get_3_lists(from_type, to_type)
        index=from_list.index(from_object)
        return to_list[index]
    
    
    
    def __str__(self):
        res=''
        if not self.treemix_newick_format:
            return res
        for adm, treemix_V, treemix_N in zip(self.admixture_string_nodes, self.treemix_numbered_vertices, self.treemix_newick_format):
            res+='{:6}'.format(str(adm))
            res+='{:6}'.format(str(treemix_V))
            res+=str(treemix_N)+'\n'
        return res[:-1] #erasing the last line change
        
        
class node(object):
    
    def __init__(self):
        self.count=0
        
    def __call__(self):
        self.count+=1
        print 'n'+str(self.count)
        return 'n'+str(self.count)
    
class adm_node(object):
    
    def __init__(self):
        self.count=0
        
    def __call__(self):
        self.count+=1
        return 'a'+str(self.count), 'x'+str(self.count)
    

# def unzip_file(filename):
#     reduced_filename='.'.join(filename.split(".")[:-1])
#     take_copy_args=['cp', filename, filename+".tmp"]
#     move_back_args=['mv', filename+'.tmp', filename]
#     args=['gunzip', '-f', filename]
#     subprocess.call(take_copy_args)
#     subprocess.call(args)
#     subprocess.call(move_back_args)
#     return reduced_filename

class vertix(object):
    
    def __init__(self, name, L_name=None, N_name=None, root=False):
        self.name=name
        self.L_name=L_name
        self.N_name=N_name
        self.root=root
        
    def is_leaf(self):
        return self.L_name is not None
    
    def is_migration(self):
        return self.N_name is None
    
    def is_root(self):
        return self.root
    

def read_vertices(filename_vertices):
    vertices={}
    with open(filename_vertices, 'r') as f:
        for lin in f.readlines():
            a=lin.split()
            is_mig=(a[3]=='MIG')
            V_name=a[0]
            if not is_mig:
                L_name=a[1]
                N_name=a[-1].rstrip()
                is_root=(a[2]=='ROOT')
                if L_name!='NA':
                    vertices[V_name]=vertix(V_name, L_name=L_name, N_name=N_name, root=False)
                else:
                    vertices[V_name]=vertix(V_name, N_name=N_name, root=is_root)
            else:
                vertices[V_name]=vertix(V_name)
    return vertices

def get_root(vertices):
    for vertix in vertices.values():
        if vertix.is_root():
            return vertix
                
                
                
                
def match_vertices(filename_vertices, vd):
    admixture_vertices=[]
    with open(filename_vertices, 'r') as f:
        for lin in f.readlines():
            a=lin.split()
            is_root=(a[2]=='ROOT')
            is_mig=(a[3]=='MIG')
            if not is_root and not is_mig:
                V_name=a[0]
                N_name=a[-1].rstrip()
                vd.insert_mapping(from_object=N_name, to_object=V_name, from_type='Treemix_N', to_type='Treemix_V')
            if is_mig:
                admixture_vertices.append((a[0],(a[5],a[6])))
    return vd, admixture_vertices
    
def get_edge_lengths(filename_edges):
    edges={}
    with open(filename_edges, 'r') as f:
        for lin in f.readlines():
            a=lin.split()
            edges[(a[0],a[1])]=a[2]
    return edges

def get_edge_lengths2(filename_edges):
    edges={}
    with open(filename_edges, 'r') as f:
        for lin in f.readlines():
            a=lin.split()
            if a[4]=='MIG':
                edges[(a[0],a[1])]=None
            else:
                edges[(a[0],a[1])]=a[2]
    return edges

def parse_admixtures(admixture_strings):
    from_to_weights={}
    for adm_string in admixture_strings:
        a=adm_string.split()
        weight=float(a[0])
        from_N=a[4]
        to_N=a[5]
        from_to_weights[from_N]=(to_N,weight)
    return from_to_weights

def parse_admixtures2(admixture_strings):
    from_to_weights={}
    for adm_string in admixture_strings:
        a=adm_string.split()
        weight=float(a[0])
        from_N=a[4]
        to_N=a[5]
        from_to_weights[(from_N,to_N)]=float(weight)
    return from_to_weights

class Node():
    
    def __init__(self, name):
        self.name=name
        self.parents=[]
        self.children=[]
        
    def add_child(self, child_node):
        self.children.append(child_node)
        
    def add_parent(self, parent_node):
        self.parents.append(parent_node)
    
    def get_parents(self):
        return self.parents
        
    def has_children(self):
        return len(self.children)>0
        
def construct_pointers(edges):
    all_nodes={}
    for parent,child in edges.keys():
        if parent in all_nodes:
            parent_node=all_nodes[parent]
        else:
            parent_node=Node(parent)
            all_nodes[parent]=parent_node
        if child in all_nodes:
            child_node=all_nodes[child]
        else:
            child_node=Node(child)
            all_nodes[child]=child_node
        all_nodes[parent].add_child(child_node)
        all_nodes[child].add_parent(parent_node)
    return all_nodes

def get_leaf_nodes(nodes):
    res=[]
    for node in nodes.values():
        if not node.has_children():
            res.append(node)
    return res

def tree_structure_to_Rtree_structure(leaf_nodes, edge_lengths, root_name):
    ready_lineages=leaf_nodes
    waiting_lineages=[]
    res_tree={}
    while len(ready_lineages)>1 or len(waiting_lineages)>0:
        node=ready_lineages.pop()
        parents=node.get_parents()
        added_node=[None]*5
        for parent in parents:
            d=edge_lengths[(parent.name, node.name)]
            if d is None:
                added_node[1]=parent.name
                added_node[1+3]=0
            else:
                added_node[0]=parent.name
                added_node[0+3]=float(d)
            if parent.name in waiting_lineages:
                waiting_lineages.remove(parent.name)
                ready_lineages.append(parent)
            else:
                waiting_lineages.append(parent.name)
        res_tree[node.name]=added_node
    tree=rename_rootname(res_tree,old_name=root_name, new_name='r')
    for key, val in tree.items():
        print key,':',val
    return insert_children_in_tree(tree)
        

def read_tree_structure(edges, root_name):
    all_nodes=construct_pointers(edges)
    leaf_nodes=get_leaf_nodes(all_nodes)
    #leaf_names=[leaf.name for leaf in leaf_nodes]
    return tree_structure_to_Rtree_structure(leaf_nodes, edges, root_name)

def find_first_non_admix(key,tree):
    next_key=key
    while True:
        key=next_key
        children=get_real_children(tree[key])
        found_1=False
        found_0=False
        if len(children)==0:
            break
        for child in children:
            if mother_or_father(tree, child_key=child, parent_key=key)==0:
                next_key=child
                found_0=True
            else:
                found_1=True
        if len(children)==1:
            assert found_0,'admixture branch on admixture branch?'
            continue
        elif len(children)==2:
            if not found_1 and found_0:
                break
            if found_1 and found_0:
                continue
            assert found_0, 'two admixture branches to the same coalescence node'
    return key
    

def adjust_admixture_proportions(rTree_structure, vertice_dictionary, admixtures):
    for key, node in rTree_structure.items():
        if node_is_admixture(node):
            ## We are now in the situation that 
            ##     source 
            ##      /    \
            ##  \  /      \ /
            ##   node     b_child_1
            ##    |             \
            ##    |              |
            ##  a_child_1      b_child_2
            ##   / \               / \
            ##      \ /               |
            ##     a_child_2         ...
            ##        |               | 
            ##       ...            b_child_m
            ##        |                / \
            ##      a_child_k             | 
            ##         / \               d_child_1 
            ##        |                     
            ##     c_child_1
            ##       / \
            ##And we want to find the c_child_1 and d_child_1 
            #because the admixtures-dictionary contains the admixture proportion with the item  
            #(c_child_1_N,d_child_1):adm_proportion.
            admixture_parent=node[1]
            c_child_1=find_first_non_admix(key,rTree_structure)
            d_child_1=find_first_non_admix(admixture_parent, rTree_structure)
            c_child_1_N=vertice_dictionary[c_child_1].N_name
            d_child_1_N=vertice_dictionary[d_child_1].N_name
            rTree_structure[key][2]=1.0-admixtures[(d_child_1_N, c_child_1_N)]
    return rTree_structure

def get_leaf_remappings(vd):
    '''
    calculates the before and after key that should be changed such that a tree goes from V-leaves to admb-leaves
    '''
    remaps=[]
    for vertix in vd.values():
        if vertix.is_leaf():
            remaps.append((vertix.name, vertix.L_name))
    return remaps

def remap_leaves(tree, vertice_dictionary):
    remaps=get_leaf_remappings(vertice_dictionary)
    for key_from, key_to in remaps:
        tree=rename_key(tree, old_key_name=key_from, new_key_name=key_to)
        
    return tree
            
               
def make_Rtree(edges,  vertice_dictionary,admixtures):
    root_name=get_root(vertice_dictionary).name
    rTree_structure=read_tree_structure(edges, root_name)
        #print pretty_string(rTree_structure)
    print 'Before inserting admixture proportions:', pretty_string(rTree_structure)
    tree=adjust_admixture_proportions(rTree_structure, vertice_dictionary, admixtures)
    print 'After admixture proportions, before double node pruning',pretty_string(tree)
    tree=prune_double_nodes(tree)
    print 'After pruning, before renaming tree leaves',pretty_string(tree)
    tree=remap_leaves(tree, vertice_dictionary)
    print 'After remapping tree leaves',pretty_string(tree)
    return tree
    
    
        
def add_admixtures(tree, vd, adm_vertices, edges, admixtures):
    a_names=adm_node()
    for source_key_V, (source_parent_key_V, source_child_key_V) in adm_vertices:
        source_child_key_B=vd.get_value(source_child_key_V, 'Treemix_V','AdmB')
        source_child_key_N=vd.get_value(source_child_key_V, 'Treemix_V','Treemix_N')
        sink_child_key_N, weight=admixtures[source_child_key_N]
        sink_child_key_B=vd.get_value(sink_child_key_N, 'Treemix_N', 'AdmB')
        sink_child_V=vd.get_value(sink_child_key_N, 'Treemix_N', 'Treemix_V')
        sink_name, source_name=a_names()
        
        t3=float(edges[(source_key_V, source_child_key_V)])
        t4=float(edges[(source_parent_key_V, source_key_V)])
        u1=t3/(t3+t4)
        
        
        tree=insert_admixture_node_halfly(tree, sink_child_key_B, 0, insertion_spot=0, admix_b_length=0, new_node_name=sink_name, admixture_proportion= 1-weight)
        #print 'tree after inserting admixture', tree
        tree=graft(tree, sink_name, source_child_key_B, u1, source_name, 0, remove_branch=1)
    return tree

def initor(a):
    if not isinstance(a, basestring):
        return a[0]
    else:
        return a

def treemix_file_to_admb_files(filename_treeout, filename_vertices, filename_edges, 
                               outgroup=None, snodes=None, prefix='', force=True, 
                               return_format=['None', 'arbitrary_rooted','outgroup_rooted','outgroup_removed','outgroup_removed_tuple']):
    return_format=initor(return_format)
    tree=read_treemix_file2(filename_treeout, filename_vertices, filename_edges)
    arbitrary_rooted=deepcopy(tree)
    nodes=get_leaf_keys(tree)
    if snodes is not None:
        snodes_set=set(snodes)
        if outgroup is not None:
            snodes_set=set(snodes+[outgroup])
            if outgroup not in snodes:
                warnings.warn('outgroup added to the beginning of the admbayes realization of the treemix mle, even though it is not requested in snodes.')
                snodes.append(outgroup)
        assert set(nodes)==set(snodes), 'the nodes of the treemix file does not match, the supplied nodes'
    else:
        snodes=nodes
    save_stage(tree, 4, prefix='not_needed', full_nodes=snodes, before_added_outgroup_nodes=['not_needed'], after_reduce_nodes=['not_needed'], filename=
               prefix+'_treemix_arbitrary_rooted_tree.txt')
    if outgroup is not None:
        if force:
            tree=rearrange_root_foolproof(tree, outgroup)
        else:
            tree=rearrange_root(tree, outgroup)
        save_stage(tree, 4, prefix='not_needed', full_nodes=snodes, before_added_outgroup_nodes=['not_needed'], after_reduce_nodes=['not_needed'], filename=
               prefix+'_treemix_outgroup_rooted_tree.txt')
        outgroup_rooted=deepcopy(tree)
        tree,add=remove_outgroup(tree, remove_key=outgroup, return_add_distance=True)
        snodes.remove(outgroup)
        save_stage(tree, 4, prefix='not_needed', full_nodes=snodes, before_added_outgroup_nodes=['not_needed'], after_reduce_nodes=['not_needed'], filename=
               prefix+'_treemix_outgroup_rooted_removed_tree.txt')
        save_stage(add, 2, prefix='not_needed', full_nodes=snodes, before_added_outgroup_nodes=['not_needed'], after_reduce_nodes=['not_needed'], filename=
               prefix+'_treemix_outgroup_rooted_removed_add.txt')
        outgroup_removed=deepcopy(tree)
    if return_format=='arbitrary_rooted':
        return arbitrary_rooted
    if return_format=='outgroup_rooted':
        return outgroup_rooted
    if return_format=='outgroup_removed':
        return outgroup_removed
    if return_format=='outgroup_removed_tuple':
        return outgroup_removed, add

def read_treemix_file(filename_treeout, filename_vertices, filename_edges, outgroup=None):
    np=new_node_naming_policy()
    if filename_treeout.endswith('.gz'):
        filename_treeout=unzip(filename_treeout)
    if filename_vertices.endswith('.gz'):
        filename_vertices=unzip(filename_vertices)
    if filename_edges.endswith('.gz'):
        filename_edges=unzip(filename_edges)
    with open(filename_treeout, 'r') as f:
        newick_tree=f.readline().rstrip()
        admixtures=parse_admixtures(map(str.rstrip,f.readlines()))
    edges= get_edge_lengths2(filename_edges)    
    #print newick_tree
    tree,translates=parse_newick_tree(newick_tree)
    vd=vertice_dictionary()
    for adm_key, treemix_N_key in translates.items():
        vd.insert_mapping(adm_key, treemix_N_key, 'AdmB', 'Treemix_N')
    #print '-------------------------'
    #print vd
    vd, adm_vertices=match_vertices(filename_vertices, vd)
    #matched_admixtures=match_admixtures(admixtures, adm_vertices)
   # print '-------------------------'
   # print vd
   # print adm_vertices
    edges=get_edge_lengths(filename_edges)
  #  print edges
    tree=insert_children_in_tree(tree)
    reverse_translates={v:k for k,v in translates.items()}
#     for k,c in translates.items():
#         print k, ':', c
#     for k,v in tree.items():
#         print k,':',v
#     print translates
#     print admixtures
    tree=add_admixtures(tree, vd, adm_vertices, edges, admixtures)
    if outgroup is not None:
        tree=rearrange_root(tree, outgroup)
        
    
    return tree


def read_treemix_file2(filename_treeout, filename_vertices, filename_edges, outgroup=None):
    if filename_treeout.endswith('.gz'):
        filename_treeout=unzip(filename_treeout)
    if filename_vertices.endswith('.gz'):
        filename_vertices=unzip(filename_vertices)
    if filename_edges.endswith('.gz'):
        filename_edges=unzip(filename_edges)
    with open(filename_treeout, 'r') as f:
        newick_tree=f.readline().rstrip()
        admixtures=parse_admixtures2(map(str.rstrip,f.readlines()))
    vertice_dictionary= read_vertices(filename_vertices)  
    print vertice_dictionary
    edges= get_edge_lengths2(filename_edges)     
    #print newick_tree
    tree=make_Rtree(edges, vertice_dictionary, admixtures)
    print pretty_string(tree)
    #tree=remove_children(tree)
    if outgroup is not None:
        tree=rearrange_root(tree, outgroup)
        print 'after rearrangement'
        print pretty_string(tree)
    return tree

    
    
def insert_admixtures(admixtures, translates, node_naming):
    admixture_proportion, _,_,_,origin, destination= admixtures.split()
    origin_key=translates[origin]
    destination_key=translates[destination]
    sink_key, source_key= node_naming(2) 
    tree[source_key]=tree[tree[origin_key][0], ]
    tree[origin_key]=[source_key, None, None,0,None]
    #tree[]=

def parse_newick_tree(newick_string):
    connects_with_lengths={}
    node_count=node()
    translates={}
    tree={}
    def reduce_newick(nstring, parent_key, node_count,tree, translates):
        nstring=nstring.strip()
        if ',' in nstring:
            i=0
            while nstring[i]!='(' and nstring[i]!=',':
                i+=1
            if nstring[i]==',':
                reduce_newick(nstring[:i], parent_key, node_count, tree,translates)
                reduce_newick(nstring[i+1:], parent_key, node_count, tree,translates)
                return None
            #i now has the index of the first (
            first_p=i
            count=0
            while count!=1:
                i+=1
                if nstring[i]=='(':
                    count-=1
                elif nstring[i]==')':
                    count+=1
            second_p=i
            first_nstring=nstring[first_p+1:second_p]
            to_come=nstring[second_p+1:]
            if to_come=='' or to_come[0]==';':
                reduce_newick(first_nstring, parent_key, node_count, tree,translates)  
            if to_come and to_come[0]==':':
                assert to_come[0]==':', 'unexptected to_come '+to_come
                node_val=node_count()
                key_name=node_val
                translates[key_name]=("("+first_nstring+")"+to_come.split(',')[0]).replace("'", '')
                reduce_newick(first_nstring, key_name, node_count,tree,translates)
                if ',' in to_come:
                    comma=to_come.split(',')
                    next_string=','.join(comma[1:])
                    reduce_newick(next_string, parent_key, node_count,tree,translates)
                    to_come=comma[0]
                blength=float(to_come.split(':')[1])
                tree[key_name]=[parent_key, None, None, blength, None]
        else:
            key,str_length= nstring.split(':')
            key_replaced=key.replace("'", '')
            tree[key_replaced]=[parent_key, None,None,float(str_length),None]
            translates[key_replaced]=nstring.replace("'", '')
        #nstring.split(',')
    reduce_newick(newick_string, 'r', node_count, tree,translates)
    return tree,translates
    
if __name__=='__main__':
    filename_treeout='../../../../Dropbox/Bioinformatik/AdmixtureBayes/annoying_treemix_output/trmx5.treeout'
    filename_vertices='../../../../Dropbox/Bioinformatik/AdmixtureBayes/annoying_treemix_output/trmx5.vertices'
    filename_edges='../../../../Dropbox/Bioinformatik/AdmixtureBayes/annoying_treemix_output/trmx5.edges'
    tree=treemix_file_to_admb_files(filename_treeout, filename_vertices, filename_edges, outgroup='out', snodes=None, prefix='sletmig'+os.sep, return_format='outgroup_rooted')
    #tree=read_treemix_file2('../../../../Dropbox/Bioinformatik/AdmixtureBayes/treemix_example3/new_one2.treeout',
    #                       '../../../../Dropbox/Bioinformatik/AdmixtureBayes/treemix_example3/new_one2.vertices',
    #                       '../../../../Dropbox/Bioinformatik/AdmixtureBayes/treemix_example3/new_one2.edges', outgroup='out')
    import tree_plotting
    tree_plotting.plot_as_directed_graph(tree)
    from tree_warner import check
    
    check(tree)

    print pretty_string(tree)
    import numpy as np
    print pretty_string(tree)
    from Rtree_to_covariance_matrix import make_covariance
    from reduce_covariance import reduce_covariance, Areduce
    cov=make_covariance(tree, node_keys=['out']+['s'+str(i) for i in range(1,11)])
    print cov
    cov2=np.loadtxt( '../../../../Dropbox/Bioinformatik/AdmixtureBayes/treemix_example3/anew.txt')
    np.set_printoptions(precision=6,  linewidth=200, suppress=True)
    print cov-cov2
    print reduce_covariance(cov-cov2,0)
    print Areduce(cov-cov2)
    
    