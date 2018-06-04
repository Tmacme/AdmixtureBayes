from reduce_covariance import reduce_covariance
from Rtree_operations import get_number_of_leaves, add_outgroup, get_number_of_admixes, scale_tree, scale_tree_copy
from tree_statistics import (identifier_to_tree_clean, generate_predefined_list_string, 
                             identifier_file_to_tree_clean, unique_identifier_and_branch_lengths)
from Rtree_to_covariance_matrix import make_covariance, get_populations
import numpy as np
from generate_sadmix_trees import effective_number_of_admixes, admixes_are_sadmixes
#def effective_number_of_admixes(t):
#   return np.random.choice(3)
from calculate_covariance_distances import open_cov_file_admb
from construct_covariance_choices import read_tree, read_one_line
import pandas as pd
import os
from copy import deepcopy
from tree_to_data import file_to_emp_cov

from tree_statistics import admixture_sorted_unique_identifier
from Rtree_operations import get_leaf_keys, rearrange_root_foolproof, remove_outgroup


from argparse import ArgumentParser
from collections import Counter
from subgraphing import get_subtree, get_unique_plottable_tree,get_and_save_most_likely_substrees

print 'imported software'

def get_list_of_turned_topologies(trees, true_tree):
    nodes=get_leaf_keys(true_tree)
    return [admixture_sorted_unique_identifier(tree, nodes) for tree in trees], admixture_sorted_unique_identifier(true_tree, nodes)


def get_covariance(outfile):
    cov, _, mult= open_cov_file_admb(outfile, None)
    return cov, mult

def always_true(**args):
    return True

def identity(x):
    return x

def iterate_over_output_file(outfile, 
                             cols=[], 
                             pre_thin_data_set_function=identity, 
                             while_thin_data_set_function=always_true,
                             row_summarize_functions=[],
                             thinned_d_dic=identity,
                             full_summarize_functions=[],
                             **constant_kwargs):
    
    df= pd.read_csv(outfile, usecols=cols)
    df = df[cols]
    df= pre_thin_data_set_function(df)
    full_summs=[full_summarize_function(df) for full_summarize_function in full_summarize_functions]
    
    all_results=[]
    
    n=len(df)
    for i,r in df.iterrows():
        cont=False
        d_dic={colname:r[k] for k, colname in enumerate(cols)}
        d_dic.update(constant_kwargs)
        if not while_thin_data_set_function(**d_dic):
            continue
        for row_summarize_function in row_summarize_functions:
            #print row_summarize_function
            #print d_dic
            add_dic, skip=row_summarize_function(**d_dic)
            if skip:
                cont=True
                break
            d_dic.update(add_dic)
        if cont:
            continue
        all_results.append(thinned_d_dic(d_dic))
    return all_results, full_summs

def create_treemix_csv_output(tree,add,m_scale, outfile):
    if m_scale is not None:
        tree=scale_tree(tree,1.0/m_scale)
        add=add/m_scale
    with open(outfile, 'w') as f:
        f.write('tree,add'+'\n')
        f.write(unique_identifier_and_branch_lengths(tree)+','+str(add))
        
def create_treemix_sfull_tree_csv_output(tree,m_scale, outfile):
    if m_scale is not None:
        tree=scale_tree(tree,1.0/m_scale)
    with open(outfile, 'w') as f:
        f.write('sfull_tree'+'\n')
        f.write(unique_identifier_and_branch_lengths(tree))

class make_Rtree(object):
    
    def __init__(self, nodes_to_be_sorted, remove_sadtrees=False):
        self.nodes=sorted(nodes_to_be_sorted)
        self.remove_sadtrees=remove_sadtrees
        
    def __call__(self, tree, **not_needed):
        #print tree
        #print not_needed
        Rtree=identifier_to_tree_clean(tree, leaves=generate_predefined_list_string(deepcopy(self.nodes)))
        if self.remove_sadtrees and (not admixes_are_sadmixes(Rtree)):
            return {'Rtree':Rtree}, True
        return {'Rtree':Rtree}, False
    
class make_full_tree(object):
    
    def __init__(self, add_multiplier=1, outgroup_name='out', remove_sadtrees=False):
        self.add_multiplier=add_multiplier
        self.outgroup_name=outgroup_name
        self.remove_sadtrees=remove_sadtrees
        
    def __call__(self, Rtree=None, add=None, **kwargs):
        if Rtree is None:
            assert 'sfull_tree' in kwargs, 'sfull_tree not specified'
            nodes=sorted(kwargs['full_nodes'])
            sfull_tree=kwargs['sfull_tree']
            full_tree=identifier_to_tree_clean(sfull_tree, leaves=generate_predefined_list_string(deepcopy(nodes)))
            if self.remove_sadtrees and (not admixes_are_sadmixes(full_tree)):
                return {'full_tree':full_tree}, True
            return {'full_tree':full_tree}, False
        full_tree= add_outgroup(deepcopy(Rtree),  
                                inner_node_name='new_node', 
                                to_new_root_length=float(add)*self.add_multiplier, 
                                to_outgroup_length=0, 
                                outgroup_name=self.outgroup_name)
        return {'full_tree':full_tree}, False
    
class make_Rcovariance(object):
    
    def __init__(self, nodes, add_multiplier=1):
        self.nodes=nodes
        self.add_multiplier=add_multiplier
        
    def __call__(self, Rtree=None, add=None, **kwargs):
        if Rtree is None:
            full_tree=kwargs['full_tree']
            outgroup_name=list(set(get_leaf_keys(full_tree))-set(self.nodes))[0]
            cov=make_covariance(full_tree, node_keys=[outgroup_name]+self.nodes)
            Rcov=reduce_covariance(cov, 0)
            return {'Rcov':Rcov}, False
        #print get_leaf_keys(Rtree)
        #print self.nodes
        Rcov=make_covariance(Rtree, node_keys=self.nodes)+float(add)*self.add_multiplier
        
        return {'Rcov':Rcov}, False
    
class cov_truecov(object):
    
    def __init__(self, true_covariance):
        self.true_covariance=true_covariance
        
    def __call__(self, Rcov, **not_needed):
        dist=np.linalg.norm(Rcov-self.true_covariance)
        #print 'Rcov', Rcov
        #print 'true_cov', self.true_covariance
        return {'cov_dist':dist}, False
    
def get_subpops(pops, sub_graph_keys):
    ss_subgraph_keys=set(sub_graph_keys)
    new_pops=[]
    for pop in pops:
        new_pop=ss_subgraph_keys.intersection(pop.split('.'))
        new_pops.append('.'.join(new_pop))
    if '' in new_pops:
        new_pops.remove('')
    return '_'.join(sorted(list(set(new_pops))))
        


class topology(object):
    
    def __init__(self, nodes):
        self.nodes=nodes
        
    def __call__(self, Rtree=None, **kwargs):
        if Rtree is None:
            full_tree=kwargs['full_tree']
            outgroup=list(set(get_leaf_keys(full_tree))-set(self.nodes))[0]
            cfull_tree=rearrange_root_foolproof(deepcopy(full_tree), outgroup) #this removes the admixtures between the outgroup and the root.
            Rtree=remove_outgroup(cfull_tree, outgroup)
        top=admixture_sorted_unique_identifier(Rtree, leaf_order=self.nodes, not_opposite=True)
        return {'topology':top}, False


    
class subgraph(object):
    
    def __init__(self, subgraph_keys, identifier='', max_num=10, total_probability=1.0, prefix='',**not_needed):
        self.subgraph_keys=subgraph_keys
        self.identifier=identifier
        self.max_num=max_num
        self.total_probability=total_probability
        self.prefix=prefix
        
    def __call__(self, Rtree=None, **kwargs):
        if Rtree is None:
            Rtree=kwargs['full_tree']
        Rtree=deepcopy(Rtree)
        print 'Rtree',Rtree
        subgraph=get_subtree(Rtree, self.subgraph_keys)
        print 'subgraph', subgraph
        sub_stree=get_unique_plottable_tree(subgraph)
        print 'sub_stree', sub_stree
        return {'subgraph_'+self.identifier:sub_stree}, False
    
    def summarise(self, sub_strees):
        get_and_save_most_likely_substrees(sub_strees, 
                                           self.subgraph_keys,
                                           self.max_num,
                                           self.total_probability,
                                           self.prefix)
        return 'check_accompanying_files'    
    
class subsets(object):
    
    def __init__(self, subgraph_keys, identifier='', prefix='', max_num=10, **not_needed):
        self.subgraph_keys=subgraph_keys
        self.identifier=identifier
        self.prefix=prefix
        self.max_num=max_num
        
    def __call__(self, pops, **kwargs):
        subsets=get_subpops(pops, self.subgraph_keys)
        return {'subsets_'+self.identifier:subsets}, False   
    
    def summarise(self, pops, prefix=''):
        n=len(pops)
        c=Counter(pops)
        tops=c.most_common(self.max_num)
        print 'summarizing subsets..'
        with open(prefix+'subsets_'+self.identifier+'_tops.txt', 'w') as f:
            for i in range(min(len(tops),self.max_num)):    
                f.write(','.join([str(i+1),str(float(tops[i][1])/n),tops[i][0]])+'\n')
        return tops[0][0]
         
    
class topology_identity(object):
    
    def __init__(self, true_Rtree, nodes):
        self.full_scaled_turned_topology=admixture_sorted_unique_identifier(true_Rtree, leaf_order=nodes, not_opposite=True)
        
    def __call__(self, topology, **not_needed):
        ident_top=(topology==self.full_scaled_turned_topology)
        return {'top_identity':ident_top}, False
    
class get_pops(object):
    
    def __init__(self, min_w=0.0, keys_to_include=None):
        self.min_w=min_w
        self.keys_to_include=keys_to_include
            
    def __call__(self, Rtree=None, **kwargs):
        if Rtree is None:
            tree=kwargs['full_tree']
        else:
            tree=Rtree
        pops=get_populations(tree, self.min_w, keys_to_include=self.keys_to_include)
        return {'pops':pops}, False 
    
class compare_pops(object):
    def __init__(self, true_tree, min_w=0.0, keys_to_include=None):
        self.true_pops=set(get_populations(true_tree, min_w, keys_to_include))
        
    def __call__(self, pops, **not_needed):
        diffs=set(pops).symmetric_difference(self.true_pops)
        return {'set_differences':len(diffs)}, False

class set_identity(object):
    def __init__(self):
        pass
    
    def __call__(self, set_differences,**not_needed):
        ident=(set_differences==0)
        return {'set_identity':ident}
    
    
class extract_number_of_sadmixes(object):
    
    def __init__(self, filter_on_sadmixes=None):
        self.filter_on_sadmixes=filter_on_sadmixes
    
    def __call__(self, Rtree=None, **kwargs):
        if Rtree is None:
            Rtree=kwargs['full_tree']
        no_sadmixes=effective_number_of_admixes(Rtree)
        if self.filter_on_sadmixes is not None and no_sadmixes!= self.filter_on_sadmixes:
            return {}, True
        return {'no_sadmixes':no_sadmixes}, False


class thinning(object):
    
    def __init__(self, burn_in_fraction=None, total=None, **values_to_filter_by):
        self.burn_in_fraction=burn_in_fraction
        self.total=total
        self.values_to_filter_by=values_to_filter_by
        
    def __call__(self, df):
        #first_removing burn-in
        n=len(df)
        print 'removing burn in from dataframe with ', n, 'rows.'
        if self.burn_in_fraction is not None:
            df=df[int(n*self.burn_in_fraction):]
        print 'burn_in operation finished. Now ', len(df), 'rows.'
        for column,value in self.values_to_filter_by.items():
            print 'filtering on ', column,'==',value
            df=df.loc[df[column]==value,:]
        print 'after filtering operations there are now', len(df),'rows'
        if self.total is not None:
            n=len(df)
            stepsize=max(n//self.total,1)
            df=df[::stepsize]
            print 'thinning complete. Now', len(df), 'rows'
        return df
    
def summarize_all_results(all_results, summ_names, summ_funcs):
    lists={summ_name:[] for summ_name in summ_names}
    for row_dic in all_results:
        for summ_name, summ_val in row_dic.items():
            lists[summ_name].append(summ_val)  
    res=[]
    for summ_name, summ_func in zip(summ_names, summ_funcs):
        res.append(summ_func(lists[summ_name]))
    return res
    

def read_tree(filename):
    with open(filename, 'r') as f:
        nodes=f.readline().strip().split()
        stree=f.readline().strip()
        
        
        
def read_covariance(filename, nodes):
    cov=[]
    with open(filename, 'r') as f:
        nodes=f.readline().strip().split()
        count=0
        for lin in f.readlines():
            if count==len(nodes):
                break
            cov.append(lin.split()[1:])
            count+=1
        if len(lin)>4:
            multiplier=float(lin.split('=')[1])
        else:
            multiplier=None
    
def read_true_values(true_scaled_tree='', 
                      true_tree='',
                      true_add='',
                      true_covariance_reduced='',
                      true_covariance_and_multiplier='',
                      true_no_admix='',
                      true_m_scale='',
                      true_variance_correction=None,
                      true_df=''):
    scaled_tree,tree,add,covariance_reduced,(Rcovariance,multiplier), no_admix,m_scale,vc,df=None,None,None,None,(None,None),None,None,None,None
    if true_scaled_tree:
        scaled_tree=identifier_file_to_tree_clean(true_scaled_tree)
    if true_tree:
        tree=identifier_file_to_tree_clean(true_tree)
    if true_add:
        add=float(read_one_line(true_add))
    if true_covariance_reduced:
        covariance_reduced=file_to_emp_cov(true_covariance_reduced, sort_nodes_alphabetically=True, return_only_covariance=False)
    if true_covariance_and_multiplier:
        Rcovariance,multiplier,vc=file_to_emp_cov(true_covariance_and_multiplier, sort_nodes_alphabetically=True, vc=true_variance_correction, return_only_covariance=False)
    if true_no_admix:
        no_admix=int(true_no_admix)
    if true_m_scale:
        m_scale=float(read_one_line(true_m_scale))
    if true_df:
        df=float(read_one_line(true_df))
    return scaled_tree,tree,add,covariance_reduced,(Rcovariance,multiplier), no_admix,m_scale,vc,df
            
    
def float_mean(v):
    return np.mean(map(float,v))
def mode(lst):
    data = Counter(lst)
    return data.most_common(1)[0][0]
    
    
          
