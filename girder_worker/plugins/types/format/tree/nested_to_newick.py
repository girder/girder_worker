from ete3 import Tree


def populate_tree(node, children):
    for c in children:
        name = c.get('node_data', {}).get('node name', '')
        dist = c.get('edge_data', {}).get('weight')
        n = node.add_child(name=name, dist=dist)
        populate_tree(n, c.get('children', []))


t = Tree()
populate_tree(t, input.get('children', []))
output = t.write(format=1)
