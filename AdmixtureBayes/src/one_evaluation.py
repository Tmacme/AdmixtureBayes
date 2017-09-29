
def one_evaluation(starting_tree, 
                   posterior_function,
                   result_file):
    likelihood_val, prior_val= posterior_function(starting_tree, verbose=True)
    posterior_val = likelihood_val+prior_val
    likelihood_val2=posterior_function.get_max_likelihood(verbose=True)
    
    with open(result_file, 'w') as f:
        f.write(' '.join(['starting_tree']+map(str,[likelihood_val, prior_val, posterior_val]))+'\n')
        f.write(' '.join(['max_likelihood']+map(str,[likelihood_val2, '.', '.'])))
        
    