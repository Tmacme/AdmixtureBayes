import matplotlib.pyplot as plt
from Rtree_operations import get_number_of_admixes, get_all_branch_lengths
from tree_statistics import unique_identifier
from data_wrangling_functions import values_to_numbers, count_strings, count_strings2



class Summary(object):
       
    def __init__(self, name, pandable=True):
        self.name=name
        self.pandable=pandable
    
    def __call__(self, **kwargs):
        pass
    
    def pretty_print(self, output):
        return str(output)
    
    def make_trajectory(self, x, **kwargs):
        return plt.plot(x,**kwargs)
    
    def make_histogram(self, x,a=None, **kwargs):
        plt.hist(x, fc=(1, 0, 0, 0.5), normed=True, **kwargs)
        if a is not None:
            plt.hist(a,fc=(0, 1, 0, 0.5), normed=True, **kwargs)
    
class s_no_admixes(Summary):
    
    def __init__(self):
        super(s_no_admixes,self).__init__('no_admixes')

    def __call__(self, **kwargs):
        old_tree=kwargs['old_tree']
        return get_number_of_admixes(old_tree)
    
    def summary_of_phylogeny(self, tree):
        return get_number_of_admixes(tree)
    
    def make_histogram(self, x,a):
        maxval=max(x)
        if a is not None:
            maxval=max(maxval, max(a))
        return Summary.make_histogram(self, x, a, bins=range(maxval+1))
    

class s_branch_length(Summary):

    def __init__(self):
        super(s_branch_length,self).__init__('branch_length')

    def __call__(self, **kwargs):
        old_tree=kwargs['old_tree']
        return sum(get_all_branch_lengths(old_tree))
    
    def summary_of_phylogeny(self, tree):
        return sum(get_all_branch_lengths(tree))
    
class s_variable(Summary):
    
    def __init__(self, variable, pandable=True):
        super(s_variable, self).__init__(variable, pandable)

    def __call__(self, **kwargs):
        return kwargs[self.name]
    
class s_tree_identifier(Summary):
    
    def __init__(self):
        super(s_tree_identifier,self).__init__('tree_identifier')
        
    def __call__(self, **kwargs):
        old_tree=kwargs['old_tree']
        return unique_identifier(old_tree)
    
    def summary_of_phylogeny(self, tree):
        return unique_identifier(tree)
    
    def make_trajectory(self, x, **kwargs):
        numbers=values_to_numbers(x)
        print 'numbers', numbers
        plt.plot(numbers)
    
    def make_histogram(self, x,a=None,**kwargs):
        if a is None:
            labels, counts1 = count_strings(x)
            counts2=None
        else:
            labels, counts1, counts2 = count_strings2(x,a)
        print 'labels', labels
        plt.bar(range(len(labels)), counts1, width=1.0, alpha=0.5, color='r', label='MCMC')
        if counts2 is not None:
            plt.bar(range(len(labels)), counts2, width=1.0, alpha=0.5, color='g', label='MCMC')

 