from prior import prior
from likelihood import likelihood, n_mark
from scipy.stats import norm, multivariate_normal
from math import log
from generate_prior_trees import generate_phylogeny
from tree_statistics import identifier_to_tree_clean
from Rtree_operations import get_number_of_leaves, get_number_of_admixes, remove_outgroup, simple_reorder_the_leaves_after_removal_of_s1
from tree_to_data import reduce_covariance
from Rtree_to_covariance_matrix import make_covariance


def initialize_posterior2(emp_cov=None, 
                         true_tree=None, 
                         M=None, 
                         use_skewed_distr=False, 
                         p=0.5, 
                         rescale=False, 
                         model_choice=['empirical covariance',
                                       'true tree covariance',
                                       'wishart on true tree covariance',
                                       'empirical covariance on true tree',
                                       'no likelihood'],
                         simulate_true_tree=False,
                         true_tree_no_leaves=None,
                         true_tree_no_admixes=None,
                         nodes=None,
                         simulate_true_tree_with_skewed_prior=False,
                         reduce_cov=None,
                         add_outgroup_to_true_tree=False,
                         reduce_true_tree=False):
    
    if not isinstance(model_choice, basestring):
        model_choice=model_choice[0]
        
    if model_choice == 'no likelihood':
        return initialize_prior_as_posterior(), {}
        
    if (model_choice == 'true tree covariance' or 
        model_choice == 'wishart on true tree covariance' or
        model_choice == 'empirical covariance on true tree'):
        
        if simulate_true_tree:
            true_tree= generate_phylogeny(true_tree_no_leaves,
                               true_tree_no_admixes,
                               nodes,
                               simulate_true_tree_with_skewed_prior)
            
        elif isinstance(true_tree, basestring):
            if ';' in true_tree: #this means that the true tree is a s_tree
                true_tree_s=true_tree
                true_tree=identifier_to_tree_clean(true_tree_s)
            else:
                with open(true_tree, 'r') as f:
                    true_tree_s=f.readline().rstrip()
                true_tree=identifier_to_tree_clean(true_tree_s)
        
        
        
                
        true_tree=Rtree_operations.simple_reorder_the_leaves_after_removal_of_s1(true_tree)
                
        
        no_leaves = get_number_of_leaves(true_tree)
        no_admixes = get_number_of_admixes(true_tree)
        
        
        
        cov=make_covariance(true_tree)
        
        if reduce_cov is not None:
            pass 
        if reduce_true_tree is not None:
            true_tree=Rtree_operations.remove_outgroup(true_tree, reduce_true_tree)
            if reduce_true_tree=='s1' or reduce_true_tree==0:
                pass
        if emp_cov is not None:
            if isinstance(emp_cov, basestring):
                pass
    
    if M is None:
        M=n_mark(emp_cov)
    if rescale:
        emp_cov, multiplier = rescale_empirical_covariance(emp_cov)
        print 'multiplier is', multiplier
    def posterior(x,pks={}):
        #print tot_branch_length
        prior_value=prior(x,p=p, use_skewed_distr=use_skewed_distr,pks=pks)
        if prior_value==-float('inf'):
            return -float('inf'), prior_value
        likelihood_value=likelihood(x, emp_cov,M=M)
        pks['prior']=prior_value
        pks['likelihood']=likelihood_value
        #pks['posterior']=prior_value+likelihood_value
        return likelihood_value, prior_value
    if rescale:
        return posterior, multiplier
    return posterior

def initialize_posterior(emp_cov, M=10, p=0.5, use_skewed_distr=False, multiplier=None, nodes=None):
    def posterior(x,pks={}):
        #print tot_branch_length
        #print get_number_of_leaves(x[0]), emp_cov.shape[0]
        prior_value=prior(x,p=p, use_skewed_distr=use_skewed_distr,pks=pks)
        if prior_value==-float('inf'):
            return -float('inf'), prior_value
        likelihood_value=likelihood(x, emp_cov,M=M, nodes=nodes)
        pks['prior']=prior_value
        pks['likelihood']=likelihood_value
        #pks['posterior']=prior_value+likelihood_value
        return likelihood_value, prior_value
    if multiplier is not None:
        return posterior, multiplier
    return posterior

def initialize_big_posterior(emp_cov, M=None, use_skewed_distr=False, p=0.5):
    if M is None:
        M=n_mark(emp_cov)
    def posterior(x,pks={}):
        #print tot_branch_length
        prior_value=prior(x,p=p, use_skewed_distr=use_skewed_distr,pks=pks)
        if prior_value==-float('inf'):
            return -float('inf'), prior_value
        likelihood_value=likelihood(x, emp_cov,M=M, pks=pks)
        pks['prior']=prior_value
        pks['likelihood']=likelihood_value
        prior_values=(pks['branch_prior'], pks['no_admix_prior'], pks['admix_prop_prior'], pks['top_prior'])
        covariance=pks['covariance']
        #pks['posterior']=prior_value+likelihood_value
        return likelihood_value, prior_value, prior_values, covariance
    return posterior
        

def initialize_prior_as_posterior(p=0.5):
    def posterior(x,pks={}):
        #print tot_branch_length
        prior_value=prior(x,p=p,pks=pks)
        if prior_value==-float('inf'):
            return prior_value
        pks['prior']=prior_value
        pks['likelihood']=0
        return 0,prior_value
    return posterior

def initialize_trivial_posterior():
    def posterior(x, pks={}):
        if isinstance(x, float):
            res= norm.logpdf(x)
            pks['prior']= res
            return res
#         elif isinstance(x, list) and isinstance(x[0], float):
#             res= multivariate_normal.logpdf(x)
#             pks['prior']= res
#             return res
        else:
            assert False, 'input in posterior was not recognizable.'
    return posterior

def print_pks(pks):
    for key, value in pks.items():
        print '\t',key,':',value

def call_post(posterior_function,tree, posterior_function_name='posterior', tree_name='tree'):
    pks={}
    print posterior_function_name+'('+tree_name+')=', posterior_function(tree, pks=pks)
    print_pks(pks)
    
def rescale_empirical_covariance(m):
    '''
    It is allowed to rescale the empirical covariance matrix such that the inferred covariance matrix takes values that are closer to the mean of the prior.
    '''
    
    n=m.shape[0]
    actual_trace=m.trace()
    expected_trace=log(n)/log(2)*n
    multiplier= expected_trace/actual_trace
    return m*multiplier, multiplier


if __name__=='__main__':
    import Rcatalogue_of_trees
    import Rtree_operations
    import Rtree_to_covariance_matrix
    
    true_tree=Rcatalogue_of_trees.tree_good
    ref_tree=Rtree_operations.create_trivial_tree(4, 0.2)
    nodes=Rtree_operations.get_trivial_nodes(4)
    
    true_cov=Rtree_to_covariance_matrix.make_covariance(true_tree, nodes)
    ref_cov=Rtree_to_covariance_matrix.make_covariance(ref_tree,nodes)
    
    true_posterior=initialize_posterior(true_cov)
    ref_posterior=initialize_posterior(ref_cov)

        
    
    call_post(true_posterior, ref_tree, 'true_posterior', 'ref_tree')
    call_post(true_posterior, true_tree, 'true_posterior', 'true_tree')
    call_post(ref_posterior, ref_tree, 'ref_posterior', 'ref_tree')
    call_post(ref_posterior, true_tree, 'ref_posterior', 'true_tree')
    
    print '''----fixed n'----- '''
    
    true_posterior=initialize_posterior(true_cov,M=10)
    ref_posterior=initialize_posterior(ref_cov,M=10)
    
    call_post(true_posterior, ref_tree, 'true_posterior', 'ref_tree')
    call_post(true_posterior, true_tree, 'true_posterior', 'true_tree')
    call_post(ref_posterior, ref_tree, 'ref_posterior', 'ref_tree')
    call_post(ref_posterior, true_tree, 'ref_posterior', 'true_tree')