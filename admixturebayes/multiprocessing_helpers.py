from multiprocessing import Queue, Process
from MCMC import basic_chain
from numpy import random

class basic_chain_class_as_process(object):
    
    def __init__(self, basic_chain_class):
        self.chain=basic_chain_class
        self.process= Process(target=self.chain)
        self.process.start()
        
    def set_seed(self, new_seed):
        self.chain.set_seed(new_seed)
    
    def start(self, p):
        self.chain.task_queue.put(p)
    
    def terminate(self):
        self.process.terminate()
        
    def complete(self):
        return self.chain.response_queue.get()
    
class basic_chain_class(object):
    
    def __init__(self, summaries, posterior_function, proposal, reseed=None):
        if reseed is None: #if not applied the different chains will run with the same seed, putting the assumptions of the model in danger.
            random.seed()
        elif isinstance(reseed, int):
            random.seed(reseed)
        self.summaries=summaries
        self.posterior_function=posterior_function
        self.proposal=proposal
        self.task_queue= Queue()
        self.response_queue = Queue()

    def __call__(self):
        while True:
            input = self.task_queue.get()
            self.response_queue.put(self.run_chain(input))
            
            
    def run_chain(self, p):
        start_tree, post, N, sample_verbose_scheme, overall_thinning, i_start_from, temperature, proposal_update, multiplier = p
        #print 'run_chain proposal.node_naming.n', self.proposal.node_naming.n
        return basic_chain(start_tree,
                           self.summaries, 
                           self.posterior_function, 
                           self.proposal, 
                           post, 
                           N, 
                           sample_verbose_scheme, 
                           overall_thinning, 
                           i_start_from, 
                           temperature, 
                           proposal_update,
                           multiplier)
        
        
class basic_chain_pool(object):
    
    def __init__(self, summaries, posterior_function, proposals, seeds=None):
        if seeds is None:
            seeds=[None]*len(proposals)
        self.group=[basic_chain_class_as_process(
            basic_chain_class(summaries, posterior_function, proposal,seed)) for proposal,seed in zip(proposals,seeds)]

    
    def order_calculation(self, list_of_lists_of_arguments):
        '''
        The list of arguments should math that of p in basic_chain_class.run_chain()
        '''
        #assert len(list_of_lists_of_arguments)==len(self.group)
        #for processs in self.group:
            #print 'order_calculation proposal.node_naming.n', processs.chain.proposal.node_naming.n
        counter=0
        for chain, list_of_arguments in zip(self.group, list_of_lists_of_arguments):
            chain.start(list_of_arguments)
            counter+=1
        assert counter==len(self.group)
        return [chain.complete() for chain in self.group]
    
    def terminate(self):
        for chain in self.group:
            chain.terminate()
    