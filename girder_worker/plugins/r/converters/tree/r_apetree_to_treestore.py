import bson

#  *********************************************
#  **** converting from APE to Arbor below *****
#  *********************************************


def printApeTree(apeTree):
    print 'print overall apeTree:'
    print apeTree
    print '[0]:', apeTree[0]
    print '[1]:', apeTree[1]
    print '[2]:', apeTree[2]
    print '[3]:', apeTree[3]


# lookup taxa by name so we don't get the nodes scrambled in the APE tree
def returnNodeNameFromIndex(apeTree, index):
    if (len(apeTree[1]) == 1):
        leafIndex = 2
    else:
        # print 'alternative ape tree compondent order case'
        leafIndex = 1
    leafCount = len(apeTree[leafIndex])
    # print 'lookup for index:',index
    if index < leafCount+1:
        # node is a taxon, return the species name
        nodeName = apeTree[leafIndex][index-1]
    else:
        nodeName = 'node'+str(index)
    return nodeName

    # sometimes the tuples in phylo class instance are re-orderered.
    # the transformed tree seems to have the order:
    # [0]=edges, [1]=tiplabels, [2]=internalNodeCount, [3]= branchlengths,
    # which has [1] and [2] switched
    # from the definition.  We will look and switch them if necessary


def addApeTreeNodesIntoTreeStore(apeTree, data_coll):
    if (len(apeTree[1]) == 1):
        leafIndex = 2
        countIndex = 1
    else:
        # print 'alternative ape tree compondent order case'
        leafIndex = 1
        countIndex = 2
    # calculate how many nodes are here
    leafCount = len(apeTree[leafIndex])
    # printApeTree(apeTree)
    # print 'apeTree[countIndex]:',apeTree[countIndex]
    # print 'apeTree[countIndex][0]:',apeTree[countIndex][0]
    totalNodes = leafCount + int(apeTree[countIndex][0])
    # loop through the nodes and create a document for each one
    for index in range(1, totalNodes+1):
        node = dict()
        node['name'] = returnNodeNameFromIndex(apeTree, index)
        if index > leafCount:
            # node is not a taxon, so add an empty clade array
            node['clades'] = []
        data_coll.insert(node)


# traverse the edges of an apeTree and add the connectivity from the apeTree
# into the mongo collection representing the tree.  This method assumes the
# nodes have  been added previously.
def addApeTreeEdgesIntoTreeStore(apeTree, data_coll):
    # go through the edge table and add fields to the nodes in the collection
    edgeCount = len(apeTree[0])/2
    # print 'found edge count to be: ',edgeCount
    # print 'edges:',apeTree[3]
    for edgeIndex in range(0, edgeCount):
        startNodeIndex = int(apeTree[0][edgeIndex])
        endNodeIndex = int(apeTree[0][edgeCount+edgeIndex])
        startNodeQuery = {
            'name': returnNodeNameFromIndex(apeTree, startNodeIndex)}
        endNodeQuery = {'name': returnNodeNameFromIndex(apeTree, endNodeIndex)}
        startNode = data_coll.find_one(startNodeQuery)
        endNode = data_coll.find_one(endNodeQuery)
        # print 'edgeIndex: ',edgeIndex,'endnode:  ', endNode
        # add branch length to end node
        try:
            endNode['branch_length'] = apeTree[3][edgeIndex]
        except TypeError:
            print 'error on edgeIndex or no branchlength:', edgeIndex

        # print 'edgeIndex: ',edgeIndex,'endnode:  ', endNode
        data_coll.update(endNodeQuery, endNode)
        # add edge leaving start node and going to endnode
        startNode['clades'].append(endNode['_id'])
        data_coll.update(startNodeQuery, startNode)


# The Arbor treestore already has all its tree nodes, find the root of the tree
# and add a handle node into the collection pointing to the root node.
def addHandleNodeIntoTreeStore(apeTree, data_coll):
    if (len(apeTree[1]) == 1):
        leafIndex = 2
    else:
        # print 'alternative ape tree compondent order case'
        leafIndex = 1
    leafCount = len(apeTree[leafIndex])
    # add the 'handle node' to the collection.  Find the root of the dataset by
    # getting the node immediately after the last leaf
    rootNodeQuery = {'name': returnNodeNameFromIndex(apeTree, leafCount+1)}
    rootNode = data_coll.find_one(rootNodeQuery)
    handlenode = dict()
    # handlenode['name'] = ''
    handlenode['rooted'] = True
    handlenode['clades'] = []
    handlenode['clades'].append(rootNode['_id'])
    data_coll.insert(handlenode)


# this erases the name attributes on internal nodes of the tree.  Names for
# taxon nodes are not affected
def clearInternalNodeNames(apeTree, data_coll):
    if (len(apeTree[1]) == 1):
        leafIndex = 2
        countIndex = 1
    else:
        print 'alternative ape tree compondent order case'
        leafIndex = 1
        countIndex = 2
    leafCount = len(apeTree[leafIndex])
    totalNodes = leafCount + int(apeTree[countIndex][0])
    for index in range(1, totalNodes+1):
        if index > leafCount:
            # node is not a taxon, so remove its name entry
            nodeQuery = {'name': returnNodeNameFromIndex(apeTree, index)}
            internalNode = data_coll.find_one(nodeQuery)
            if 'name' in internalNode:
                del internalNode['name']
            data_coll.update(nodeQuery, internalNode)


# perform the steps that transform an apeTree (passed through the parameter
# variable) into a document collection stored in the Arbor TreeStore.
# The steps are: (1)Nodes are created, (2) edges added, (3) handled node is
# created in the collection, and (4) names are erased for hierarchical nodes
def importApeTreeToArbor(apeTree, data_coll):
    data_coll.drop()
    global global_next_node
    global global_next_edge
    global global_leafname_list
    global_next_node = 0
    global_next_edge = 0
    global_leafname_list = []
    addApeTreeNodesIntoTreeStore(apeTree, data_coll)
    addApeTreeEdgesIntoTreeStore(apeTree, data_coll)
    addHandleNodeIntoTreeStore(apeTree, data_coll)
    clearInternalNodeNames(apeTree, data_coll)


# Adapting treestore conversion to girder_worker
class InMemoryCollection:
    items = []
    nameMap = {}
    currentId = 0

    def drop(self):
        self.items = []
        self.nameMap = {}
        self.currentId = 0

    def insert(self, item):
        item['_id'] = self.currentId
        self.currentId += 1
        self.items.append(item)
        if 'name' in item:
            self.nameMap[item['name']] = item

    def update(self, query, item):
        pass

    def find_one(self, query):
        return self.nameMap[query['name']]


c = InMemoryCollection()
importApeTreeToArbor(input, c)

output = ''.join([bson.BSON.encode(d) for d in c.items])
