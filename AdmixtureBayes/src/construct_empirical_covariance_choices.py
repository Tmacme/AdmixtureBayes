import subprocess
from numpy import array, mean, zeros, diag, sum, arcsin, sqrt
from reduce_covariance import reduce_covariance
#from optimize_empirical_matrix import full_maximization, transform_allele_freqs
from copy import deepcopy

default_scale_dic={'None':'None',
                   'Jade-o':'outgroup_sum', 
                   'Jade':'average_sum',
                   'outgroup_sum':'outgroup_sum',
                   'outgroup_product':'outgroup_product',
                   'average_sum':'average_sum',
                   'average_product':'average_product'}

def reorder_rows(p, names,nodes):
    mapping={val:key for key, val in enumerate(names)}
    if nodes is None:
        nodes=names
    new_order=[mapping[node] for node in nodes]
    p=p[new_order,:]
    return p

def read_freqs(new_filename):
    with open(new_filename, 'r') as f:
        names=f.readline().split()
        allele_counts=[]
        pop_sizes=[]
        minors=[]
        total_sum=0
        for n,r in enumerate(f.readlines()):
            minor_majors=r.split()
            freqs=[]
            for minor_major in minor_majors:
                minor, major= map(float,minor_major.split(','))
                freqs.append(float(minor)/float(major+minor))
                total_sum+=major+minor
                minors.append(minor)
                if n==0:
                    pop_sizes.append(major+minor)
            allele_counts.append(freqs)
    return allele_counts, names, pop_sizes, minors, total_sum

def make_uncompressed_copy(filename):
    take_copy_args=['cp', filename, filename+".tmp"]
    move_back_args=['mv', filename+'.tmp', filename]
    args=['gunzip', '-f', filename]
    new_filename='.'.join(filename.split('.')[:-1])
    subprocess.call(take_copy_args)
    subprocess.call(args)
    subprocess.call(move_back_args)
    return new_filename

def m_scaler(m, scale_type, allele_freqs, n_outgroup=None):
    if scale_type=='None' or scale_type=='Jade' or scale_type=='Jade-o':
        return 1.0
    if scale_type.startswith('outgroup'):
        s=allele_freqs[n_outgroup,:]
    elif scale_type.startswith('average'):
        s=mean(allele_freqs, axis=0)
    else:
        scaler=1.0
    if scale_type.endswith('product'):
        mu=mean(s)
        scaler=mu*(1.0-mu)
    elif scale_type.endswith('sum'):
        scaler=mean(s*(1.0-s))
    return scaler

def alleles_to_cov_optimizing(p, 
                              names, 
                              pop_sizes=None,
                              nodes=None,
                              cutoff=0.01):
    p=reorder_rows(p, names, nodes)
    print 'p',p
    xs=p
    ns=deepcopy(p)
    
    for n in range(len(pop_sizes)):
        popsize=pop_sizes[n]
        xs[n,:]*=popsize
        print 'xs',xs
        ns[n,:]=popsize
        
    print 'xs',xs
    print 'ns',ns
    
    trans=transform_allele_freqs(cutoff)
    
    return full_maximization(xs,ns, trans=trans)
    
        

def alleles_to_cov(p,
                   names, 
                   pop_sizes=None, 
                   reduce_method=['no', 'average', 'outgroup'], 
                   variance_correction=['None', 'unbiased', 'mle'], 
                   nodes=None, 
                   arcsin_transform=False, 
                   method_of_weighing_alleles=['None', 'Jade','outgroup_sum', 'outgroup_product', 'average_outgroup', 'average_product','Jade-o'], 
                   reducer='',
                   jade_cutoff=1e-5,
                   reduce_also=False,
                   bias_c_weight='default'):
    p=reorder_rows(p, names, nodes)
    
    if not isinstance(variance_correction, basestring):
        type_of_scaling=variance_correction[0]
    else:
        type_of_scaling=variance_correction
    
    if not isinstance(reduce_method, basestring):
        reduce_method=reduce_method[0]
    if not isinstance(method_of_weighing_alleles, basestring):
        method_of_weighing_alleles=method_of_weighing_alleles[0]
    
    if arcsin_transform:
        p2=arcsin(sqrt(p))*2
    else:
        p2=p
        
    if reduce_method=='outgroup':
        n_outgroup=next((n for n, e in enumerate(nodes) if e==reducer))
        #print n_outgroup
        p2=p2-p2[n_outgroup,:]
    elif reduce_method=='average':
        n_outgroup=next((n for n, e in enumerate(nodes) if e==reducer))
        total_mean2=mean(p, axis=0)
        if arcsin_transform:
            total_mean2=arcsin(sqrt(total_mean2))*2
        p2=p2-total_mean2
    else:
        n_outgroup=None
    
    if method_of_weighing_alleles=='Jade':
        mu=mean(p, axis=0)
        
        i=array([v > jade_cutoff and v<1.0-jade_cutoff for v in mu ])
        p2=p2[:,i]/sqrt(mu[i]*(1.0-mu[i]))
        #p=p[:,i]
    if method_of_weighing_alleles=='Jade-o':
        mu=p[n_outgroup,:]
        
        i=array([v > jade_cutoff and v<1.0-jade_cutoff for v in mu ])
        #p=p[:,i]
        p2=p2[:,i]/sqrt(mu[i]*(1.0-mu[i]))
        
    m=p2.dot(p2.T)/p2.shape[1]
    
    if bias_c_weight=='default':
        bias_c_weight=default_scale_dic[method_of_weighing_alleles]
    
    if method_of_weighing_alleles != 'None' and method_of_weighing_alleles!='Jade' and method_of_weighing_alleles != 'Jade-o':
        m=m/m_scaler(m, method_of_weighing_alleles, p, n_outgroup)
    
    if reduce_also:
        #assert False, 'DEPRECATED! due to possible mis calculations'
        m=reduce_covariance(m, n_outgroup)
        if type_of_scaling!='None':
            m=other_bias_correction(m,p, pop_sizes,n_outgroup)
    elif type_of_scaling!='None':
        changer=bias_correction(m,p, pop_sizes,n_outgroup, type_of_scaling=type_of_scaling)/m_scaler(m, bias_c_weight, p, n_outgroup)
        m=m/m_scaler(m, method_of_weighing_alleles, p, n_outgroup)
        print 'm',reduce_covariance(m,n_outgroup)
        print 'changer', reduce_covariance(changer, n_outgroup)
        m-=changer
        
    return m

def avg_var(ps):
    return sum((p*(1-p) for p in ps))/float(len(ps))

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
    
    

def treemix_to_cov(filename='treemix_in.txt.gz', 
                   reduce_method=['no', 'average', 'outgroup'], 
                   reducer='', 
                   variance_correction=False, 
                   nodes=None,
                   arcsin_transform=False,
                   method_of_weighing_alleles='None',
                   jade_cutoff=1e-5
                   ):
#unzip
    new_filename=make_uncompressed_copy(filename)
#     print 'FILENAME', filename
#     print 'NEW FILENAME', new_filename
    
    allele_counts, names, pop_sizes, minors, total_sum= read_freqs(new_filename)
    
    p=array(allele_counts)
    p=p.T
    
    return alleles_to_cov(p, 
                          names, 
                          pop_sizes, 
                          reduce_method, 
                          variance_correction, 
                          nodes, 
                          arcsin_transform, 
                          method_of_weighing_alleles, 
                          reducer,
                          jade_cutoff)

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
    

def bias_correction(m, p, pop_sizes, n_outgroup=None, type_of_scaling='unbiased'):
    #pop sizes are the number of chromosome for each SNP. It is also called the haploid population size
    Bs=[B(prow, pop_size, type_of_scaling=type_of_scaling) for prow, pop_size in zip(p, pop_sizes)]
    print 'Bs',Bs
    adjusting_matrix=adjuster(Bs)
    print 'adjusting matrix',adjusting_matrix
    print 'm',m
    #if n_outgroup is not None:
    #    adjusting_matrix[n_outgroup,:]=0
    #    adjusting_matrix[:,n_outgroup]=0
    print 'adjusting matrix',adjusting_matrix
    res=m-adjusting_matrix
    print 'm-adjusting', res
    from reduce_covariance import reduce_covariance
    print 'mreduced', reduce_covariance(m, n_outgroup)
    print 'adjustingreduced', reduce_covariance(adjusting_matrix, n_outgroup)
    print 'mreduced -adjusting reduced', reduce_covariance(m, n_outgroup)-reduce_covariance(adjusting_matrix, n_outgroup)
    print '(m -adjusting) reduced', reduce_covariance(res, n_outgroup)
    return adjusting_matrix

if __name__=='__main__':
    
    if False:
        m=adjuster([0.1,0.2])
        assert sum(m-array([[0.075,-0.075],[-0.075,0.075]]), axis=None)==0, 'adjusting wrong'
        from numpy import set_printoptions
        set_printoptions(precision=5)
        filename='sletmig/_treemix_in.txt.gz'
        nodes=['s'+str(i) for i in range(1,10)]+['out']
        print treemix_to_cov(filename, reduce_method='outgroup', reducer='out', variance_correction=False, nodes=nodes, arcsin_transform=False, method_of_weighing_alleles='outgroup_product')
        
        from load_data import read_data
        
        print read_data(filename, blocksize=1, nodes=nodes, variance_correction=True, normalize=False, reduce_also=True, reducer='out', return_muhat=False)
    
    
    
    if True:
        import numpy as np

        from scipy.stats import uniform
        def is_pos_def(x):
            print np.linalg.eigvals(x)
            return np.all(np.linalg.eigvals(x) > 0)
        p=array([uniform.rvs(size=1000) for _ in xrange(5)])
        a=-other_bias_correction(np.zeros((4,4)), p, [5,5,5,5,5],0)
        print a
        print is_pos_def(a)