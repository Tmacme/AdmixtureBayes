from multiprocessing import Queue, Process
from MCMC import basic_chain

class basic_chain_class_as_process(object):
    
    def __init__(self, basic_chain_class):
        self.chain=basic_chain_class
        self.process= Process(target=self.chain)
        self.process.start()
    
    def start(self, p):
        self.chain.task_queue.put(p)
    
    def terminate(self):
        self.process.terminate()
        
    def complete(self):
        return self.chain.response_queue.get()
    
class basic_chain_class(object):
    
    def __init__(self, summaries, posterior_function, proposal):
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
        start_tree, post, N, sample_verbose_scheme, overall_thinning, i_start_from, temperature, proposal_update = p
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
                           proposal_update)
        
        
class basic_chain_pool(object):
    
    def __init__(self, summaries, posterior_function, proposals):
        self.group=[basic_chain_class_as_process(
            basic_chain_class(summaries, posterior_function, proposal)) for proposal in proposals]
    
    
    def order_calculation(self, list_of_lists_of_arguments):
        '''
        The list of arguments should math that of p in basic_chain_class.run_chain()
        '''
        #assert len(list_of_lists_of_arguments)==len(self.group)
        counter=0
        for chain, list_of_arguments in zip(self.group, list_of_lists_of_arguments):
            chain.start(list_of_arguments)
            counter+=1
        assert counter==len(self.group)
        return [chain.complete() for chain in self.group]
    
    def terminate(self):
        for chain in self.group:
            chain.terminate()
    