import json
from networkx.readwrite.json_graph import node_link_graph

output = node_link_graph(json.loads(input))
