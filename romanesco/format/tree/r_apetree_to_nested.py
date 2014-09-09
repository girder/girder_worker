
if len(input[1]) == 1:
    leafIndex = 2
    countIndex = 1
else:
    leafIndex = 1
    countIndex = 2

leafCount = len(input[leafIndex])


def nodeNameFromIndex(index):
    if index < leafCount + 1:
        # node is a taxon, return the species name
        return input[leafIndex][index - 1]
    return ""

totalNodes = leafCount + int(input[countIndex][0])

nodes = []
nodeMap = {}

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
edgeCount = len(input[0])/2

for edgeIndex in range(edgeCount):
    startNodeIndex = int(input[0][edgeIndex])
    endNodeIndex = int(input[0][edgeCount + edgeIndex])
    startNode = nodeMap[startNodeIndex]
    endNode = nodeMap[endNodeIndex]
    # add branch length to end node
    try:
        endNode['edge_data'] = {'weight': input[3][edgeIndex]}
    except TypeError:
        print "error on edgeIndex or no branchlength:", edgeIndex
    except IndexError:
        print "error on edgeIndex or no branchlength:", edgeIndex

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
