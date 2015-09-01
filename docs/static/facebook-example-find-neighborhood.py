from networkx import all_neighbors

node_id = most_popular_person
subgraph = G.subgraph(list(all_neighbors(G, node_id)) + [node_id])
