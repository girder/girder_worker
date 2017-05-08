# The R phylo tree format is a list where the elements
# are not guaranteed to be in any particular order.
# Here we determine which element is which.
element_names_sexp = input.do_slot('names')
element_names = [x for x in element_names_sexp]

# required elements
tipLabelIndex = -1
if 'tip.label' in element_names:
    tipLabelIndex = element_names.index('tip.label')
else:
    print 'Error: tip.label not found in input ape tree'

nNodeIndex = -1
if 'Nnode' in element_names:
    nNodeIndex = element_names.index('Nnode')
else:
    print 'Error: Nnode not found in input ape tree'

edgeIndex = -1
if 'edge' in element_names:
    edgeIndex = element_names.index('edge')
else:
    print 'Error: edge not found in input ape tree'

# optional elements
edgeLengthIndex = -1
if 'edge.length' in element_names:
    edgeLengthIndex = element_names.index('edge.length')

nodeLabelIndex = -1
if 'node.label' in element_names:
    nodeLabelIndex = element_names.index('node.label')

leafCount = len(input[tipLabelIndex])
totalNodes = leafCount + int(input[nNodeIndex][0])

nodes = []
nodeMap = {}


def nodeNameFromIndex(index):
    if index < leafCount + 1:
        # node is a taxon, return the species name
        return input[tipLabelIndex][index - 1]
    elif nodeLabelIndex != -1:
        return input[nodeLabelIndex][index - 1 - leafCount]
    return ''


# loop through the nodes and create a dict for each one
for index in range(1, totalNodes + 1):
    node = {'node_data': {}}
    node['node_data']['node name'] = nodeNameFromIndex(index)
    if index > leafCount:
        # node is not a taxon, so add an empty children array
        node['children'] = []
    nodes.append(node)
    nodeMap[index] = node

# go through the edge table and add fields to the nodes in the collection
edgeCount = len(input[edgeIndex])/2

for edge in range(edgeCount):
    startNodeIndex = int(input[edgeIndex][edge])
    endNodeIndex = int(input[edgeIndex][edgeCount + edge])
    startNode = nodeMap[startNodeIndex]
    endNode = nodeMap[endNodeIndex]
    if edgeLengthIndex != -1:
        # add branch length to end node
        try:
            endNode['edge_data'] = {'weight': input[edgeLengthIndex][edge]}
        except TypeError:
            print 'error on edge or no branchlength:', edge
        except IndexError:
            print 'error on edge or no branchlength:', edge

    # add edge leaving start node and going to endnode
    startNode['children'].append(endNode)

output = nodeMap[leafCount + 1]
output['node_fields'] = ['node name', 'node weight']
output['edge_fields'] = ['weight']


def nodeWeights(node, cur):
    weight = node.get('edge_data', {'weight': 0.0})['weight']
    if isinstance(weight, (int, float)):
        cur += weight
    node['node_data']['node weight'] = cur
    for c in node.get('children', []):
        nodeWeights(c, cur)


nodeWeights(output, 0.0)
