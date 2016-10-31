from bson.json_util import dumps
from bson.objectid import ObjectId

output = []
node_oids = {}

# There is no clearly defined notion of undirected graphs in clique.json
# It simply checks for edges going in either direction, so we ignore
# whether it is an nx.DiGraph or just nx.Graph

for (node, data) in input.nodes(data=True):
    node_oids[node] = ObjectId()

    clique_node = {
        '_id': node_oids[node],
        'type': 'node'
    }

    if data:
        clique_node['data'] = data

    output.append(clique_node)

for (u, v, edge_data) in input.edges(data=True):
    clique_edge = {
        '_id': ObjectId(),
        'source': node_oids[u],
        'target': node_oids[v],
        'type': 'link'
    }

    if 'data' in edge_data:
        clique_edge['data'] = edge_data['data']

    output.append(clique_edge)

output = dumps(output)
