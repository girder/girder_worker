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
    output.add_edge(edge['source']['$oid'],
                    edge['target']['$oid'],
                    attr_dict=edge['data'] if 'data' in edge else {})
