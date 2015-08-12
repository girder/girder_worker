import json
import networkx as nx

input = json.loads(input)

nodes = [data for data in input if data['type'] == 'node']
edges = [data for data in input if data['type'] == 'link']
edge_tuples = [(e['source']['$oid'], e['target']['$oid']) for e in edges]

# If there is more than one edge with the same src/target, it's a multigraph
is_multigraph = len(edge_tuples) > len(set(edge_tuples))

if is_multigraph:
    output = nx.MultiDiGraph()
else:
    output = nx.DiGraph()

for node in nodes:
    output.add_node(node['_id']['$oid'], node['data'] if 'data' in node else {})

for edge in edges:
    nx_edge_data = {
        '$oid': edge['_id']['$oid']
    }

    if 'data' in edge:
        nx_edge_data['data'] = edge['data']

    output.add_edge(edge['source']['$oid'],
                    edge['target']['$oid'],
                    nx_edge_data)
