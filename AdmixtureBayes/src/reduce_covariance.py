from numpy import insert, identity,ones, ix_

def reduce_covariance(covmat, subtracted_population_index):
    reducer=insert(identity(covmat.shape[0]-1), subtracted_population_index, -1, axis=1)
    #print reducer
    return reducer.dot(covmat).dot(reducer.T)

def get_R(s, subtracted_population_index):
    return insert(identity(s-1), subtracted_population_index, -1, axis=1)

def Areduce(mat):
    A=identity(mat.shape[0])-1.0/mat.shape[0]*ones((mat.shape))
    return A.dot(mat).dot(A)

def thin_covariance(covmat, nodes_order, specified_nodes):
    ni={node:i for i,node in enumerate(nodes_order)}
    take_out_indices=[ni[s] for s in specified_nodes]
    return covmat[ix_(take_out_indices,take_out_indices)]
    
    
    

if __name__=='__main__':
    from generate_prior_covariance import generate_covariance
    a= generate_covariance(5)
    print a
    nodes=['s'+str(i+1) for i in range(5)]
    print thin_covariance(a, nodes, ['s2','s4'])
    
    