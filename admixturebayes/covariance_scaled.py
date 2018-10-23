from covariance_estimator import Estimator, initor
from numpy import array, mean, zeros, diag, sum, arcsin, sqrt, savetxt,nan, isnan, nanmean
from numpy import sum as npsum
from reduce_covariance import reduce_covariance
import warnings

default_scale_dic={'None':'None',
                   'Jade-o':'outgroup_sum', 
                   'Jade':'average_sum',
                   'outgroup_sum':'outgroup_sum',
                   'outgroup_product':'outgroup_product',
                   'average_sum':'average_sum',
                   'average_product':'average_product'}

def nan_divide(dividend, divisor):
    res=zeros(dividend.shape)
    for i in range(dividend.shape[0]):
        for j in range(dividend.shape[1]):
            if divisor[i,j]==0:
                res[i,j]=nan
            else:
                res[i,j]=dividend[i,j]/divisor[i,j]
    return res

def nan_inner_product(a,b):
    N=len(a)
    nans=0
    res=0
    for ai,bi in zip(a,b): 
        if isnan(ai) or isnan(bi):
            nans+=1
        else:
            res+=ai*bi
    if N==nans:
        warnings.warn('There is an entry in the covariance matrix that is set to 0 because all the relevant data was nan.', UserWarning)
        return 0
        
    return res/(N-nans)

def nan_product(A,B):
    res=zeros((A.shape[0], B.shape[1]))
    for i in range(A.shape[0]):
        for j in range(B.shape[1]):
            res[i,j]=nan_inner_product(A[i,:], B[:,j])
    return res 

def m_scaler(scale_type, allele_freqs, n_outgroup=None):
    if scale_type=='None' or scale_type=='Jade' or scale_type=='Jade-o':
        return 1.0
    if scale_type.startswith('outgroup'):
        s=allele_freqs[n_outgroup,:]
    elif scale_type.startswith('average'):
        s=nanmean(allele_freqs, axis=0)
    else:
        scaler=1.0
    if scale_type.endswith('product'):
        mu=nanmean(s)
        scaler=mu*(1.0-mu)
    elif scale_type.endswith('sum'):
        scaler=nanmean(s*(1.0-s))
    #print 'm_scale', scaler
    return scaler

def avg_var(ps):
    return sum((p*(1-p) for p in ps))/float(len(ps))

def heterogeneity(allele_frequency, pop_size, type_of_scaling='unbiased'):
    if type_of_scaling=='mle':
        mult=2.0/float(len(allele_frequency))#*float(pop_size)/float(pop_size-1)
    else:
        mult=2.0/float(len(allele_frequency))*float(pop_size)/float(pop_size-1)
    return sum([p*(1-p) for p in allele_frequency])*mult

def B(allele_frequency, pop_size, type_of_scaling='unbiased'):
    return heterogeneity(allele_frequency, pop_size, type_of_scaling)/2.0/float(pop_size)

def adjuster(Bs):
    m=len(Bs)
    res=diag(array(Bs))
    res=res-array(Bs)/m
    res=(res.T-array(Bs)/m).T
    res=res+sum(Bs)/m**2
    return res

def var(p,n, type_of_scaling='unbiased'):
    if type_of_scaling=='mle':
        subtract=0
    else:
        subtract=1
    entries=array([pi*(1-pi)/(ni-subtract) for pi,ni in zip(p,n) if ni>subtract])
    return mean(entries)

def reduced_covariance_bias_correction(p,n,n_outgroup=0, type_of_scaling='unbiased'):
    Bs=[]
    for pi,ni in zip(p,n):
        Bs.append(var(pi,ni, type_of_scaling))
    outgroup_b=Bs.pop(n_outgroup)
    return diag(array(Bs))+outgroup_b
    
    
    

def bias_correction(m, p, pop_sizes, n_outgroup=None, type_of_scaling='unbiased'):
    #pop sizes are the number of chromosome for each SNP. It is also called the haploid population size
    Bs=[B(prow, pop_size, type_of_scaling=type_of_scaling) for prow, pop_size in zip(p, pop_sizes)]
    #print 'Bs',Bs
    adjusting_matrix=adjuster(Bs)
    #print 'adjusting matrix',adjusting_matrix
    #print 'm',m
    #if n_outgroup is not None:
    #    adjusting_matrix[n_outgroup,:]=0
    #    adjusting_matrix[:,n_outgroup]=0
    #print 'adjusting matrix',adjusting_matrix
    res=m-adjusting_matrix
    #print 'm-adjusting', res
    from reduce_covariance import reduce_covariance
    #print 'mreduced', reduce_covariance(m, n_outgroup)
    #print 'adjustingreduced', reduce_covariance(adjusting_matrix, n_outgroup)
    #print 'mreduced -adjusting reduced', reduce_covariance(m, n_outgroup)-reduce_covariance(adjusting_matrix, n_outgroup)
    #print '(m -adjusting) reduced', reduce_covariance(res, n_outgroup)
    return adjusting_matrix

def other_bias_correction(m,p,pop_sizes,n_outgroup):
    counter=0
    p_vars=[]
    for i in range(len(pop_sizes)):
        if i==n_outgroup:
            p0_var=avg_var(p[n_outgroup,:])/(pop_sizes[n_outgroup])
        else:
            p_vars.append(avg_var(p[i,:])/(pop_sizes[i]))
    adjusting_matrix=diag(array(p_vars))+p0_var
    print 'adjusting_matrix', adjusting_matrix
    print 'm', m
    res=m-adjusting_matrix
    print 'm-adjusting_matrix', res
    return res

class ScaledEstimator(Estimator):
    
    def __init__(self,
                 reduce_method=['outgroup','average','None'],
                 scaling=['None','outgroup_sum', 'outgroup_product', 'average_outgroup', 'average_product','Jade','Jade-o'],
                 reduce_also=True,
                 variance_correction=['None','unbiased','mle'],
                 jade_cutoff=1e-5,
                 bias_c_weight='default',
                 add_variance_correction_to_graph=False,
                 prefix_for_saving_variance_correction='',
                 save_variance_correction=True,
                 nodes=None):
        super(ScaledEstimator, self).__init__(reduce_also=reduce_also)
        self.scaling=initor(scaling)
        self.variance_correction=initor(variance_correction)
        self.jade_cutoff=jade_cutoff
        self.add_variance_correction_to_graph=add_variance_correction_to_graph
        self.prefix_for_saving_variance_correction=prefix_for_saving_variance_correction
        self.nodes=nodes
        self.save_variance_correction=save_variance_correction
        if bias_c_weight=='default':
            self.bias_c_weight=default_scale_dic[scaling]
        else:
            self.bias_c_weight=bias_c_weight
        self.reduce_method=reduce_method
        
    def subtract_ancestral_and_get_outgroup(self,p):
        if self.reduce_method=='outgroup':
            n_outgroup=self.get_reduce_index()
            #print n_outgroup
            return p-p[n_outgroup,:], n_outgroup
        elif self.reduce_method=='average':
            n_outgroup=self.get_reduce_index()
            total_mean2=nanmean(p, axis=0)
            return p-total_mean2, n_outgroup
        else:
            return p, None
        
    def __call__(self, xs, ns, extra_info={}):
        if 0 in ns:
            warnings.warn('There were 0s in the allele-totals, inducing nans and slower estimation.', UserWarning)
            ps=nan_divide(xs, ns)
        else:
            ps=xs/ns 
        return self.estimate_from_p(ps, ns=ns, extra_info=extra_info)
    
        
    def estimate_from_p(self, p, ns=None, extra_info={}):
        #p=reorder_rows(p, self.names, self.full_nodes)
        
        p2,n_outgroup = self.subtract_ancestral_and_get_outgroup(p)
        
        
    
        if self.scaling=='Jade':
            mu=mean(p, axis=0)
            
            i=array([v > self.jade_cutoff and v<1.0-self.jade_cutoff for v in mu ])
            p2=p2[:,i]/sqrt(mu[i]*(1.0-mu[i]))
        elif self.scaling=='Jade-o':
            mu=p[n_outgroup,:]
            
            i=array([v > self.jade_cutoff and v<1.0-self.jade_cutoff for v in mu ])
            #p=p[:,i]
            p2=p2[:,i]/sqrt(mu[i]*(1.0-mu[i]))
        if npsum(isnan(p2))>0:
            warnings.warn('Nans found in the allele frequency differences matrix => slower execution', UserWarning)
            m=nan_product(p2, p2.T)
        else:
            m=p2.dot(p2.T)/p2.shape[1]
        assert m.shape[0]<1000, 'sanity check failed, because of wrongly transposed matrices'
        
        
        scaling_factor=m_scaler(self.scaling, p, n_outgroup)
        extra_info['m_scale']=scaling_factor
        m=m/scaling_factor
        if self.reduce_also:
            m=reduce_covariance(m, n_outgroup)
            if self.variance_correction!='None':
                assert ns is not None, 'Variance correction needs a ns-matrix specified'
                b=reduced_covariance_bias_correction(p, ns, n_outgroup, type_of_scaling=self.variance_correction)/scaling_factor
                if self.add_variance_correction_to_graph:
                    if self.save_variance_correction:
                        savetxt(self.prefix_for_saving_variance_correction+'variance_correction.txt', b)
                else:
                    m=m-b     
        elif self.variance_correction!='None':
            m=m/m_scaler(self.scaling, p, n_outgroup)    
            extra_info['m_scale']=m_scaler(self.scaling, p, n_outgroup)     
            if ns is None:
                warnings.warn('No variance reduction performed due to no specified sample sizes', UserWarning)
            elif isinstance(ns, int):
                pop_sizes=[ns]*p2.shape[0]
                changer=bias_correction(m,p, pop_sizes,n_outgroup, type_of_scaling=self.variance_correction)/m_scaler(self.bias_c_weight, p, n_outgroup)
                #print 'm',reduce_covariance(m,n_outgroup)
                #print 'changer', reduce_covariance(changer, n_outgroup)
                if self.add_variance_correction_to_graph:
                    m-=changer
                if self.save_variance_correction:
                    savetxt(self.prefix_for_saving_variance_correction+'variance_correction.txt', changer)
            else:
                warnings.warn('assuming the same population size for all SNPs', UserWarning)
                pop_sizes=mean(ns, axis=1)
                changer=bias_correction(m,p, pop_sizes,n_outgroup, type_of_scaling=self.variance_correction)/m_scaler(self.bias_c_weight, p, n_outgroup)
                #print 'm',reduce_covariance(m,n_outgroup)
                #print 'changer', reduce_covariance(changer, n_outgroup)
                if self.add_variance_correction_to_graph:
                    if self.save_variance_correction:
                        savetxt(self.prefix_for_saving_variance_correction+'variance_correction.txt', changer)
                else:
                    m-=changer
            
        
        return m
    
if __name__=='__main__':
    from brownian_motion_generation import simulate_xs_and_ns
    import numpy as np
    n=3
    triv_nodes=map(str, range(n+1))
    est= ScaledEstimator(reduce_method='outgroup',
                         scaling='average_sum',
                         reduce_also=True,
                         variance_correction='None',
                         jade_cutoff=1e-5,
                         bias_c_weight='default',
                         save_variance_correction=False)
    Sigma = np.identity(n)*0.03+0.02
    Sigma[2,1] = 0
    Sigma[1,2] = 0
    N = 10000
    ns = np.ones((n+1,N))*2
    print 'simulating xs...'
    xs, p0s_temp, true_pijs = simulate_xs_and_ns(n, N, Sigma, ns, normal_xval=False)
    print 'simulated'
    print est(xs,ns)
    xs[2,2]=ns[2,2]=0
    print est(xs,ns)
    from scipy.stats import binom
    import numpy as np
    from reduce_covariance import reduce_covariance
    ns=np.ones((5,100))*10
    xs=binom.rvs(p=0.5, n=ns.astype(int))
    p=xs/ns
    
    print reduce_covariance(bias_correction(1, p, [10]*5),0)
    print reduced_covariance_bias_correction(p, ns, 0, type_of_scaling='unbiased')
    
    
    
    