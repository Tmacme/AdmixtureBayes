from tree_statistics import identifier_to_tree_clean, unique_identifier_and_branch_lengths
from post_analysis import read_tree_file
from Rtree_operations import change_admixture, get_categories, get_leaf_keys
from copy import deepcopy


def make_possible_files(true_tree_file, res_file):
    tree, nodes=read_tree_file(true_tree_file)
    possible_strees=get_possible_strees(tree, nodes)
    with open(res_file, 'w') as f:
        f.write(' '.join(nodes)+'\n')
        for stree in possible_strees:
            f.write(stree+'\n')
            
def get_unique_plottable_tree(tree, nodes=None):
    if nodes is None:
        nodes=sorted(get_leaf_keys(tree))
    possible_strees=sorted(get_possible_strees(tree, nodes))
    return possible_strees[0]
    
def get_possible_strees(tree, nodes):
    
    leaves,_,admixture_keys=get_categories(tree)
    k=len(admixture_keys)
    format_code='{0:0'+str(k)+'b}'
    
    
    n_trees=[]
    for i in range(2**k):
        pruned_tree = deepcopy(tree)
        bina= format_code.format(i)
        prop=1.0
        for adm_key,str_bin in zip(admixture_keys, list(bina)):
            int_bin=int(str_bin)
            if int_bin==1:
                pruned_tree[adm_key]=change_admixture(pruned_tree[adm_key])
        n_tree= unique_identifier_and_branch_lengths(pruned_tree, leaf_order=nodes)
        n_trees.append(n_tree)
    return n_trees

if __name__=='__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser(usage='pipeline for Admixturebayes', version='1.0.0')

    #overall options
    parser.add_argument('--i', type=str, default='_true_tree.txt', help='')
    parser.add_argument('--o', type=str, default='tree.txt')
    
    options=parser.parse_args()
    make_possible_files(options.i, options.o)