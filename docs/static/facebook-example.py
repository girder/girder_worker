import romanesco
from romanesco.specs import Task

most_popular_task = Task({
    'inputs': [
        {'name': 'G',
         'type': 'graph',
         'format': 'networkx'}
    ],
    'outputs': [
        {'name': 'most_popular_person',
         'type': 'string',
         'format': 'text'},
        {'name': 'G',
         'type': 'graph',
         'format': 'networkx'}
    ],
    'script':
'''
from networkx import degree

degrees = degree(G)
most_popular_person = max(degrees, key=degrees.get)
'''
})

find_neighborhood_task = Task({
    'inputs': [
        {'name': 'G',
         'type': 'graph',
         'format': 'networkx'},
        {'name': 'most_popular_person',
         'type': 'string',
         'format': 'text'}
    ],
    'outputs': [
        {'name': 'subgraph',
         'type': 'graph',
         'format': 'networkx'}
    ],
    'script':
'''
from networkx import ego_graph

subgraph = ego_graph(G, most_popular_person)
'''
})


# Set our adjacency list as our tasks input
with open('facebook-sample-data.txt') as infile:
    most_popular_task.set_input(G={'format': 'adjacencylist',
                                   'data': infile.read()})

# Run the task to find the most popular person
most_popular_task.run()

# Use the most popular tasks output to set the next tasks input
find_neighborhood_task.set_input(G={'format': 'networkx',
                                    'data': most_popular_task.get_output('G')},
                                 most_popular_person={'format': 'text',
                                                      'data': most_popular_task.get_output('most_popular_person')})

# Run the task to find the neighborhood we want to visualize
find_neighborhood_task.run()


# Retrieve the subgraph output from our task
subgraph = find_neighborhood_task.get_output('subgraph')

# Convert it to a JSON format we can use with d3.js
with open('data.json', 'wb') as outfile:
    outfile.write(romanesco.convert('graph', {'format': 'networkx',
                                              'data': subgraph},
                                    {'format': 'networkx.json'})['data'])
