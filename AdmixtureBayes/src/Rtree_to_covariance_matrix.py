
from copy import deepcopy
from numpy import zeros, diag, ix_, outer

from tree_operations import get_number_of_admixes_on_branch
from itertools import izip

from Rtree_operations import node_is_non_admixture, node_is_coalescence

class Population:
    
    def __init__(self, weights,members):
        self.weights=weights
        self.members=members
        
    def remove_partition(self, weight):
        #print "weight",weight
        #print "self.weight",self.weights
        n_w=[w*weight for w in self.weights]
        self.weights=[w*(1-weight) for w in self.weights]
        #print "weight",weight
        #print "self.weight",self.weights
        return Population(n_w, deepcopy(self.members))
    
    def merge_with_other(self, other):
        #print "self",self.members, self.weights
        #print "other", other.members, other.weights
     
        self.weights=[w+other.weights[other.members.index(m)] if m in other.members else w for m,w in izip(self.members,self.weights) ]
        tmpl=[(w,m) for w,m in izip(other.weights, other.members) if m not in self.members]
        if tmpl:
            x_w,x_m=zip(*tmpl)
            self.weights.extend(x_w)
            self.members.extend(x_m)
        return self
        
        #elf.pop={member:(self.pop.get(member,0.0)+other.pop.get(member,0.0)) for member in set(self.pop.keys()+other.pop.keys())}
        #print self.pop
        
    def get_contributions_as_iterable(self, branch_length):
        #print "calculating for the piece:"
        #print self.pop
        #print branch_length
        #list_of_res=[]
        for s1,w1 in self.pop.iteritems():
            for s2,w2 in self.pop.iteritems():
                #list_of_res.append(((s1,s2),w1*w2*branch_length))
                yield ((s1,s2),w1*w2*branch_length)
                #yield ((s1,s2),w1*w2*branch_length)
        #return list_of_res

class Covariance_Matrix():
    
    def __init__(self, nodes_to_index):
        self.ni=nodes_to_index
        self.covmat=zeros((len(nodes_to_index), len(nodes_to_index)))
    
    def get_indices(self, nodes):
        return [self.ni[n] for n in nodes]
    
    def get_addon(self, branch_length, weights):
        return branch_length*outer(weights, weights)
    
    def update(self, branch_length, population):
        indices=self.get_indices(population.members)
        self.covmat[ix_(indices,indices)]+=self.get_addon(branch_length, population.weights)
        #self.covmat[ix_(indices,indices)]+=branch_length*outer(weights, weights)


#node is p1key, p2key, adm_prop, p1length, p2length, 


    
def leave_node(key, node, population, covmat):
    if node_is_non_admixture(node): #if the node is coalescence it is not admixture
        return [follow_branch(parent_key=node[0],branch_length=node[3], population=population, covmat=covmat)]
    else:
        new_pop=population.remove_partition(1.0-node[2])
        return [follow_branch(parent_key=node[0],branch_length=node[3], population=population, covmat=covmat, dependent=node[1]),
                follow_branch(parent_key=node[1],branch_length=node[4], population=new_pop, covmat=covmat, dependent='none')]

def follow_branch(parent_key, branch_length, population, covmat, dependent="none"):
    covmat.update(branch_length, population)
    return parent_key, population, dependent

def _add_to_waiting(dic,add,tree):
    key,pop,dep=add
    if key in dic:#this means that the node is a coalescence node
        dic[key][0][1]=pop
        dic[key][1][1]=dep
    else:
        if key=='r' or node_is_non_admixture(tree[key]):
            dic[key]=[[pop,None],[dep,"empty"]]
        else:
            dic[key]=[[pop],[dep]]
    return dic

def _full_node(key,dic):
    if key in dic:
        for dep in dic[key][1]:
            if dep=="empty":
                return False
        return True
    return False

def _merge_pops(pops):
    if len(pops)==1:
        return pops[0]
    else:
        #print pops
        return pops[0].merge_with_other(pops[1])

def _thin_out_dic(dic, taken):
    ready_nodes=[]
    #print dic
    for key,[pops, deps] in dic.items():
        #print pops, deps
        full_node=True
        for dep in deps:
            if dep is None or not (dep=="none" or _full_node(dep,dic) or dep in taken):
                full_node=False
            else:
                pass
        if full_node:
            taken.append(key)
            ready_nodes.append((key,_merge_pops(pops)))
            del dic[key]
    return dic,ready_nodes
                
def make_covariance(tree, node_keys):
    pops=[Population([1.0],[node]) for node in node_keys]
    ready_nodes=zip(node_keys,pops)
    covmat=Covariance_Matrix({node_key:n for n,node_key in enumerate(node_keys)})
    waiting_nodes={}
    taken_nodes=[]
    while True:
        for key,pop in ready_nodes:
            upds=leave_node(key, tree[key], pop, covmat)
            for upd in upds:
                waiting_nodes=_add_to_waiting(waiting_nodes, upd,tree)
            taken_nodes.append(key)
        waiting_nodes,ready_nodes=_thin_out_dic(waiting_nodes, taken_nodes[:])
        print 'waiting_nodes', waiting_nodes
        print 'ready_nodes', ready_nodes
        print 'taken_nodes', taken_nodes
        if len(ready_nodes)==0:
            return None
        if len(ready_nodes)==1 and ready_nodes[0][0]=="r":
            break

    return covmat.covmat
                
            
            
            
    


if __name__=="__main__":
    
    tree_clean={'s1':['s1s2',None, None, 0.1,None],
          's2':['s1s2', None, None, 0.1,None],
          's1s2':['r',None, None, 0.2,None],
          's3':['r',None, None, 0.2, None]}
    
    tree_one_admixture={'s1':['s1b',None, None, 0.1,None],
          's1b':['s1s2','s3b',0.2, 0.1,0.2],
          's2':['s1s2', None, None, 0.1,None],
          's1s2':['r',None, None, 0.2,None],
          's3b':['r',None, None, 0.2, None],
          's3':['s3b',None,None,0.2,None]}
    
    tree_two_admixture={'s1':['s1b',None, None, 0.1,None],
          's1c':['s1s2','s3b', 0.4,0.05,0.1],
          's1b':['s1c','s3a',0.2, 0.05,0.2],
          's2':['s1s2', None, None, 0.1,None],
          's1s2':['r',None, None, 0.2,None],
          's3b':['r',None, None, 0.2, None],
          's3':['s3a',None,None,0.1,None],
          's3a':['s3b', None,None,0.1,None]
          }
    
    tree_two_admixture_cross={'s1':['s1b',None, None, 0.1,None],
          's1c':['s1s2','s3a', 0.4,0.05,0.1],
          's1b':['s1c',None,None, 0.05,None],
          's2':['s1s2', None, None, 0.1,None],
          's1s2':['r',None, None, 0.2,None],
          's3b':['r','s1b', 0.4, 0.2, 0.2],
          's3':['s3a',None,None,0.1,None],
          's3a':['s3b', None,None,0.1,None]
          }
    
    tree_illegal={'s1':['s1b',None, None, 0.1,None],
          's1c':['s1s2','s3a', 0.4,0.05,0.1],
          's1b':['s1c','s3b',0.2, 0.05,0.2],
          's2':['s1s2', None, None, 0.1,None],
          's1s2':['r',None, None, 0.2,None],
          's3b':['r',None, None, 0.2, None],
          's3':['s3a',None,None,0.1,None],
          's3a':['s3b', None,None,0.1,None]
          }
    
    tree_on_the_border={'s1':['c',None, None, 0.1,None],
          's2':['a',None, None,0.05,None],
          's3':['b',None,None, 0.3,None],
          'a':['b','d', 0.5,0.2,0.1],
          'c':['r','d',0.5,0.1,0.1],
          'd':['e',None,None,0.05,None],
          'b':['e',None,None,0.02,None],
          'e':['r',None,None,0.05,None]}
    
    tree_on_the_border2={'s1':['d',None, None, 0.1,None],
          's2':['a',None, None,0.05,None],
          's3':['e',None,None, 0.3,None],
          's4':['b',None,None, 0.3,None],
          'a':['b','c', 0.5,0.2,0.1],
          'c':['e','d',0.5,0.1,0.1],
          'b':['f',None,None,0.05,None],
          'f':['r',None,None,0.02,None],
          'e':['f',None,None,0.05,None],
          'd':['r',None,None,0.05,None]}
    
    tree_admix_to_child={
        's1':['r',None,None, 0.1,None],
        's2':['s2a',None,None,0.1,None],
        's3':['s3s2',None,None,0.1,None],
        's2a':['s3s2','s3s2a', 0.5,0.1,0.13],
        's3s2':['s3s2a',None,None,0.1,None],
        's3s2a':['r',None,None,0.01]
        }
    
    #print make_covariance(tree_clean,['s1','s2','s3'])
    #print make_covariance(tree_one_admixture,['s1','s2','s3'])
    print 'two admixtures same direction consistent'
    print make_covariance(tree_two_admixture,['s1','s2','s3'])
    print 'two admixtures cross same direction'
    print make_covariance(tree_illegal,['s1','s2','s3'])
    print 'admixture-admixture coalescent'
    print make_covariance(tree_on_the_border,['s1','s2','s3'])
    print 'admixture on admixture'
    print make_covariance(tree_on_the_border2,['s1','s2','s3','s4'])
    print 'admixture to higher in tree'
    print make_covariance(tree_admix_to_child,['s1','s2','s3'])
    print 'two admixtures cross different directions'
    print make_covariance(tree_two_admixture_cross,['s1','s2','s3'])
    

    
    
    def som():
        for i in range(100):
            make_covariance(tree_two_admixture,['s1','s2','s3'])
    import cProfile
     
    #print cProfile.run('som()')
    
    #print cProfile.run("likewise()")
    
    
    #print make_covariance(tree_flatter_list2,["s1","s2","s3","s4"])


#         