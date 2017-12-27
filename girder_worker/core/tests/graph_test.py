import json
import os
from girder_worker.plugins.types import convert
import networkx as nx
from networkx.algorithms.isomorphism import is_isomorphic, numerical_edge_match
import unittest
from lxml import etree


class TestGraph(unittest.TestCase):
    def setUp(self):
        self.GRAPHML_NS = '{http://graphml.graphdrawing.org/xmlns}'
        self.test_input = {
            'distances': {
                'format': 'networkx',
                'data': nx.Graph([
                    ('US', 'UK', {'distance': 4242}),
                    ('US', 'Australia', {'distance': 9429}),
                    ('UK', 'Australia', {'distance': 9443}),
                    ('US', 'Japan', {'distance': 6303})
                ])
            },
            'alphabetGraph': {
                'format': 'clique.json'
            }
        }

        with open(os.path.join('girder_worker', 'core', 'tests',
                               'data', 'clique.json'), 'rb') as fixture:
            self.test_input['alphabetGraph']['data'] = fixture.read()

    def test_clique(self):
        # clique.json -> NetworkX
        output = convert(
            'graph', self.test_input['alphabetGraph'], {'format': 'networkx'})

        self.assertEqual(
            set([n[1]['name'] for n in output['data'].nodes(data=True)]),
            set(['a', 'b', 'c', 'd']))
        self.assertEqual(len(output['data'].edges()), 3)
        self.assertEqual(output['data'].degree('55ba5019f8883b5bf35f3e30'), 0)

        # NetworkX -> clique.json
        output = convert(
            'graph', output, {'format': 'clique.json'})

        # Since the id of the nodes are lost, only test the structure
        # Check nodes with names a, b, c, and d
        # Check the following edges
        # a -> b
        # a -> c
        # b -> c
        output['data'] = json.loads(output['data'])
        nodes = [item for item in output['data'] if item['type'] == 'node']
        edges = [(item['source']['$oid'], item['target']['$oid'])
                 for item in output['data'] if item['type'] == 'link']
        oid_by_name = {}

        for node in nodes:
            oid_by_name[node['data']['name']] = node['_id']['$oid']

        # Check nodes
        self.assertEqual(sorted(oid_by_name.keys()),
                         ['a', 'b', 'c', 'd'])

        # Check edges
        self.assertEqual(len(edges), 3)
        self.assertIn((oid_by_name['a'], oid_by_name['b']), edges)
        self.assertIn((oid_by_name['a'], oid_by_name['c']), edges)
        self.assertIn((oid_by_name['b'], oid_by_name['c']), edges)

    def test_adjacencylist(self):
        output = convert(
            'graph', self.test_input['distances'], {'format': 'adjacencylist'})

        expected_edges = set(self.test_input['distances']['data'].edges())
        actual_edges = set()

        for line in output['data'].splitlines():
            parts = line.split(' ', 1)

            if len(parts) > 1:
                source, targets = parts

                for target in targets.split(' '):
                    edge = (source, target)
                    self.assertNotIn(edge, actual_edges)
                    actual_edges.add(edge)

        self.assertEqual(expected_edges, actual_edges)

        output = convert(
            'graph', output, {'format': 'networkx'})

        # Don't take edges into consideration, because they were lost in the
        # original conversion
        self.assertTrue(
            is_isomorphic(output['data'],
                          self.test_input['distances']['data'],
                          edge_match=None))

    def test_graphml(self):
        output = convert(
            'graph', self.test_input['distances'], {'format': 'graphml'})
        expected_edges = set(self.test_input['distances']['data'].edges(
            data='distance'))
        actual_edges = set()

        self.assertIsInstance(output['data'], (str, unicode))
        tree = etree.fromstring(output['data'])
        self.assertEqual(len(tree), 2)
        self.assertEqual(tree[0].tag, self.GRAPHML_NS + 'key')
        self.assertEqual(tree[1].tag, self.GRAPHML_NS + 'graph')

        for edge in tree[1].findall(self.GRAPHML_NS + 'edge'):
            edge = (edge.attrib['source'],
                    edge.attrib['target'],
                    int(edge.find(self.GRAPHML_NS + 'data').text))

            self.assertNotIn(edge, actual_edges)
            actual_edges.add(edge)

        self.assertEqual(expected_edges, actual_edges)

        output = convert(
            'graph', output, {'format': 'networkx'})

        self.assertTrue(
            is_isomorphic(output['data'],
                          self.test_input['distances']['data'],
                          edge_match=numerical_edge_match('distance', 1)))


if __name__ == '__main__':
    unittest.main()
