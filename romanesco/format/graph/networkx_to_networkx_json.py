import json
from networkx.readwrite.json_graph import node_link_data

output = json.dumps(node_link_data(input))
