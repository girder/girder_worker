import bson
import os
from girder_worker.tasks import run
from girder_worker.plugins.types import convert
import unittest


class TestTree(unittest.TestCase):

    def setUp(self):
        self.analysis = {
            'name': 'tree_copy',
            'inputs': [{'name': 'a', 'type': 'tree', 'format': 'nested'}],
            'outputs': [{'name': 'b', 'type': 'tree', 'format': 'nested'}],
            'script': 'b = a'
        }
        self.analysis_r = {
            'name': 'tree_copy_r',
            'inputs': [{'name': 'a', 'type': 'tree', 'format': 'r.apetree'}],
            'outputs': [{'name': 'b', 'type': 'tree', 'format': 'r.apetree'}],
            'script': 'b <- a',
            'mode': 'r'
        }
        self.newick = '((ahli:0,allogus:1):2,rubribarbus:3);'
        self.nexus = """#NEXUS


BEGIN TAXA;
    DIMENSIONS NTAX = 4;
    TAXLABELS
        A
        B
        C
        D
    ;
END;
BEGIN TREES;
    TRANSLATE
        1   A,
        2   B,
        3   C,
        4   D
    ;
    TREE * UNTITLED = [&R] ((1:1,2:1):1,(3:1,4:1):1);
END;"""
        # Change dir for loading analyses
        self.prevdir = os.getcwd()
        cur_path = os.path.dirname(os.path.realpath(__file__))
        os.chdir(cur_path)

    def tearDown(self):
        os.chdir(self.prevdir)

    def test_newick(self):
        outputs = run(
            self.analysis,
            inputs={'a': {'format': 'newick', 'data': self.newick}},
            outputs={'b': {'format': 'newick'}}
        )
        self.assertEqual(outputs['b']['format'], 'newick')
        self.assertEqual(outputs['b']['data'], self.newick)

    def test_json(self):
        outputs = run(
            self.analysis,
            inputs={'a': {'format': 'newick', 'data': self.newick}},
            outputs={'b': {'format': 'nested'}}
        )
        self.assertEqual(outputs['b']['format'], 'nested')

        expected = {
            'edge_fields': ['weight'],
            'node_fields': ['node name', 'node weight'],
            'node_data': {'node name': '', 'node weight': 0.0},
            'children': [
                {
                    'node_data': {'node name': '', 'node weight': 2.0},
                    'edge_data': {'weight': 2.0},
                    'children': [
                        {
                            'node_data': {
                                'node name': 'ahli',
                                'node weight': 2.0
                            },
                            'edge_data': {'weight': 0.0}
                        },
                        {
                            'node_data': {
                                'node name': 'allogus',
                                'node weight': 3.0
                            },
                            'edge_data': {'weight': 1.0}
                        }
                    ]
                },
                {
                    'node_data': {
                        'node name': 'rubribarbus',
                        'node weight': 3.0
                    },
                    'edge_data': {'weight': 3.0}
                }
            ]
        }

        self.assertEqual(
            outputs['b']['data'], expected)

    def test_r_apetree(self):
        outputs = run(
            self.analysis,
            inputs={'a': {'format': 'newick', 'data': self.newick}},
            outputs={'b': {'format': 'r.apetree'}}
        )
        self.assertEqual(outputs['b']['format'], 'r.apetree')
        self.assertEqual(
            str(outputs['b']['data'])[:52],
            '\nPhylogenetic tree with 3 tips and 2 internal nodes.')

    def test_r(self):
        outputs = run(
            self.analysis_r,
            inputs={'a': {'format': 'newick', 'data': self.newick}},
            outputs={'b': {'format': 'newick'}}
        )
        self.assertEqual(outputs['b']['format'], 'newick')
        self.assertEqual(outputs['b']['data'], self.newick)

        outputs = run(
            self.analysis_r,
            inputs={'a': {'format': 'nexus', 'data': self.nexus}},
            outputs={'b': {'format': 'nexus'}}
        )
        self.assertEqual(outputs['b']['format'], 'nexus')

        # Ignore spaces vs. tabs, and skip timestamp comment on line 2
        out = '\n'.join(outputs['b']['data'].splitlines()[2:])
        out = ' '.join(out.split())
        expected = '\n'.join(self.nexus.splitlines()[2:])
        expected = ' '.join(expected.split())
        self.assertEqual(out, expected)

    def test_non_binary_tree(self):
        convert(
            'tree',
            {
                'format': 'newick',
                'url': 'file://' +
                       os.path.join('data', 'geospiza_from_otl.phy')
            },
            {'format': 'nested'})

    def test_treestore(self):
        output = convert(
            'tree',
            {'format': 'newick', 'data': self.newick},
            {'format': 'r.apetree'})
        output = convert('tree', output, {'format': 'treestore'})
        self.assertEqual(output['format'], 'treestore')
        rows = bson.decode_all(output['data'])
        for d in rows:
            if 'rooted' in d:
                root = d
        self.assertNotEqual(root, None)
        self.assertEqual(len(root['clades']), 1)

        def findId(id):
            for d in rows:
                if d['_id'] == id:
                    return d

        top = findId(root['clades'][0])
        self.assertEqual(len(top['clades']), 2)
        internal = findId(top['clades'][0])
        rubribarbus = findId(top['clades'][1])
        ahli = findId(internal['clades'][0])
        allogus = findId(internal['clades'][1])
        self.assertEqual(internal['branch_length'], 2)
        self.assertEqual(ahli['name'], 'ahli')
        self.assertEqual(ahli['branch_length'], 0)
        self.assertEqual(allogus['name'], 'allogus')
        self.assertEqual(allogus['branch_length'], 1)
        self.assertEqual(rubribarbus['name'], 'rubribarbus')
        self.assertEqual(rubribarbus['branch_length'], 3)
