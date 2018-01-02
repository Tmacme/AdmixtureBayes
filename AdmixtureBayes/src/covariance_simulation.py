from scipy.stats import norm, uniform, binom, multivariate_normal
import numpy as np
from construct_empirical_covariance_choices import alleles_to_cov

class Simulator(object):
    
    def __init__(self, ns,fixed_seed=True,  load_from_file='', estimator=None):
        self.ns=ns
        self.n=ns.shape[0]-1
        self.N=ns.shape[1]
        self.fixed_seed=fixed_seed
        self.initialize_sims(load_from_file)
        self.initialize_nvals()
        self.estimator=estimator
        
    def initialize_nvals(self):
        self.nvals=np.unique(self.ns)
        self.ids=[]
        for val in self.nvals:
            self.ids.append(np.where(self.ns==val))
            
        
        
    def get_xs(self, Sigma):
        if not self.fixed_seed:
            self.initialize_sims()
        #print Sigma
        #pijs=np.zeros((self.n+1,self.N))
        #for s,p0 in enumerate(self.p0s):
        #    pijs[1:,s]=multivariate_normal.rvs(mean=[p0]*self.n, cov=Sigma*p0*(1-p0))
        #    pijs[0,s]=p0
        L=np.linalg.cholesky(Sigma)
        pijs=np.dot(L, self.Us)+self.p0s
        trunc_pijs=np.clip(pijs,0,1)
        trunc_pijs=np.insert(trunc_pijs,0,self.p0s,axis=0)
        x_ijs=self.qbinom(trunc_pijs)
        x_ijs=adjust_scipy_error(trunc_pijs, self.ns, x_ijs)
        return x_ijs
    
    def get_implied_Sigma(self, Sigma):
        x_ij=self.get_xs(Sigma)
        cov=self.estimator(x_ij, self.ns) #if this line fails, it could be because estimator has default value None
        return cov
            
    def initialize_sims(self, load_from_file):
        if load_from_file:
            self.initialize_from_file(filename_prefix=load_from_file)
            return
        self.p0s=uniform.rvs(size=self.N)
        #self.x0s=self.qbinom(self.p0s)
        self.Us=norm.rvs(size=(self.n,self.N))
        self.Us*=np.sqrt(self.p0s*(1.0-self.p0s))
        self.Vs=uniform.rvs(size=(self.n+1,self.N))
        
    def initialize_from_file(self, filename_prefix):
        self.ns= np.loadtxt(filename_prefix+'ns.txt')
        self.p0s= np.loadtxt(filename_prefix+'p0s.txt')
        self.Us= np.loadtxt(filename_prefix+'Us.txt')
        self.Vs= np.loadtxt(filename_prefix+'Vs.txt')
        self.n=self.ns.shape[0]-1
        self.N=self.ns.shape[1]
        
    def qbinom(self, trunc_pijs):
        res=np.zeros(trunc_pijs.shape)
        for i,n in enumerate(self.nvals):
                res[self.ids[i]]=binom.ppf(self.Vs[self.ids[i]], n=n, p=trunc_pijs[self.ids[i]])
        return res
        #return binom.ppf(self.Vs, n=self.ns, p=trunc_pijs)
    
    def save_to_file(self, filename_prefix):
        np.savetxt(filename_prefix+'ns.txt', self.ns)
        np.savetxt(filename_prefix+'p0s.txt', self.p0s)
        np.savetxt(filename_prefix+'Us.txt',self.Us)
        np.savetxt(filename_prefix+'Vs.txt',self.Vs)        
    
def adjust_scipy_error(pijs, ns, xs):
    xs[np.where(pijs<1e-10)]=0
    ids=np.where(pijs>1-1e-10)
    xs[ids]=ns[ids]
    return xs
    
def estimate_Sigma_wrapper(e_pij, reduce_method, method_of_weighing_alleles):
    n=e_pij.shape[0]-1
    triv_nodes=map(str, range(n+1))
    return alleles_to_cov(e_pij, 
                          names=triv_nodes,
                          nodes=triv_nodes, 
                          reducer='0', 
                          reduce_also=True, 
                          reduce_method=reduce_method, 
                          method_of_weighing_alleles=method_of_weighing_alleles)
    

def pure_sim_get_implied_Sigma(Sigma, ns):
    no,N=ns.shape
    n=no-1
    p0s=uniform.rvs(size=N)
    pij=np.zeros((n+1,N))
    for s,p0 in enumerate(p0s):
        pij[1:,s]=multivariate_normal.rvs(mean=[p0]*n, cov=Sigma*p0*(1-p0))
        pij[0,s]=p0
    pij2=np.clip(pij,0,1)

    xs=binom.rvs(ns.astype(int), p=pij2)
    #xs=np.clip(xs, 0,ns)
    return estimate_Sigma_wrapper(xs/ns, reduce_method='outgroup', method_of_weighing_alleles='outgroup_product')
    
if __name__=='__main__':


    Sigma=np.identity(3)*0.03+0.02
    Sigma[2,1]=0
    Sigma[1,2]=0
    N=10000
    ns=np.ones((4,N))*2
    sim=Simulator(ns)
    Sim=sim
    print type(Sim.ns)
    print type(Sim.Vs)
    print type(Sim.Us)
    print type(Sim.N)
    print type(Sim.n)
    print type(Sim.p0s)
    print Sim.ns.shape
    print Sim.Vs.shape
    print Sim.Us.shape
    print Sim.p0s.shape
    print sim.get_implied_Sigma(Sigma)
    print pure_sim_get_implied_Sigma(Sigma, ns)
        