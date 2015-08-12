import json
import networkx as nx

output = []

# There is no clearly defined notion of undirected graphs in clique.json
# It simply checks for edges going in either direction, so we ignore
# whether it is an nx.DiGraph or just nx.Graph

for (node, data) in input.nodes(data=True):
    clique_node = {
        '_id': {
            '$oid': node
        },
        'type': 'node'
    }

    if data:
        clique_node['data'] = data

    output.append(clique_node)

for (u, v, edge_data) in input.edges(data=True):
    clique_edge = {
        '_id': {
            '$oid': edge_data['$oid']
        },
        'source': {
            '$oid': u
        },
        'target': {
            '$oid': v
        },
        'type': 'link'
    }

    if 'data' in edge_data:
        clique_edge['data'] = edge_data['data']

    output.append(clique_edge)

output = json.dumps(output)
