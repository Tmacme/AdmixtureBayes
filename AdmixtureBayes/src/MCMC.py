from Proposal_Function import prop
from scipy.stats import poisson
from likelihood import likelihood
from numpy.random import random

def initialize_posterior(emp_cov):
    def posterior(x):
        tot_length=sum(map(len, x))
        no_admixs=(tot_length-len(x)*3)/4
#         tot_branch_length=0
        for branch in x:
            times=branch[2::2]
            less_than_zero=[1 for t in times if t<0]
            if sum(less_than_zero)>0:
                return 0
#         #print tot_branch_length
        return poisson.pmf(no_admixs,0.01)*likelihood(x, emp_cov)
    return posterior
     

def one_jump(x, post, temperature, posterior_function):
    
    newx,g1,g2,Jh,j1,j2=prop(x)
    
#     print "x",x
#     print "newx",newx
#     print "g1", g1
#     print "g2",g2
#     print "Jh", Jh
#     print "j1",j1
#     print "j2", j2
    
    print "newx",newx
    post_new=posterior_function(newx)
    
#     print "post_ratio", (post_new/post)
    
    mhr=(post_new/post)**temperature*g2*j2/j1/g1*Jh
    
#     print "mhr",mhr
    
    if random()<mhr:
        return newx,post_new
    return x,post
    

if __name__=="__main__":
    tree_flatter_list=[["r","s1",0.3,[">","s3",None,32123], 0.1], 
                   ["s2s3","s2",0.2],
                   ["s2s3","s3",0.15, ["<","s1",0.44,32123],0.05],
                   ["r","s2s3",0.2]]
    
    from numpy import diag
    N=3
    nodes=["s"+str(i) for i in range(1,N+1)]
    emp_cov=diag([0.5]*N)

    sigma=1
    x=tree_flatter_list
    posterior=initialize_posterior(emp_cov)
    post=posterior(x)
    
    

    admixes=[]
    posteriors=[]
    for i in range(1000):
        x,post=one_jump(x,post, 1.0,posterior)
        posteriors.append(post)
        tot_length=sum(map(len, x))
        no_admixs=(tot_length-len(x)*3)/4
        admixes.append(no_admixs)
        if i%1000==0:
            print i
    from collections import Counter
    print Counter(admixes)
    print posteriors
    
        

    