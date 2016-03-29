from networkx.readwrite.adjlist import generate_adjlist

# Warning - node/link metadata will be lost when converting to an
# adjacencylist format
output = '\n'.join(generate_adjlist(input))
