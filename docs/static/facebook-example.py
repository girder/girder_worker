most_popular_task = {
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
}

find_neighborhood_task = {
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
}

workflow = {
    'mode': 'workflow',
    'inputs': [
        {'name': 'G',
         'type': 'graph',
         'format': 'adjacencylist'}
    ],
    'outputs': [
        {'name': 'result_graph',
         'type': 'graph',
         'format': 'networkx'}
    ]
}

workflow['steps'] = [{'name': 'most_popular',
                      'task': most_popular_task},
                     {'name': 'find_neighborhood',
                      'task': find_neighborhood_task}]

workflow['connections'] = [
    {'name': 'G',
     'input_step': 'most_popular',
     'input': 'G'},
    {'output_step': 'most_popular',
     'output': 'G',
     'input_step': 'find_neighborhood',
     'input': 'G'},
    {'output_step': 'most_popular',
     'output': 'most_popular_person',
     'input_step': 'find_neighborhood',
     'input': 'most_popular_person'},
    {'name': 'result_graph',
     'output': 'subgraph',
     'output_step': 'find_neighborhood'}
]

import romanesco

with open('facebook-sample-data.txt') as infile:
    output = romanesco.run(workflow,
                           inputs={'G': {'format': 'adjacencylist',
                                         'data': infile.read()}},
                           outputs={'result_graph': {'format': 'networkx.json'}})

with open('data.json', 'wb') as outfile:
    outfile.write(output['result_graph']['data'])
