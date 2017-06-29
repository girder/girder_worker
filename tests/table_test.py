from girder_worker.tasks import run
from girder_worker.plugins.types import convert
from girder_worker.core import load
import os
import tempfile
import unittest
import collections
import json
import math


class TestTable(unittest.TestCase):

    def setUp(self):
        self.analysis = {
            'name': 'append_tables',
            'inputs': [
                {'name': 'a', 'type': 'table', 'format': 'rows'},
                {'name': 'b', 'type': 'table', 'format': 'rows'}
            ],
            'outputs': [{'name': 'c', 'type': 'table', 'format': 'rows'}],
            'script': ("c = {'fields': a['fields'], 'rows': a['rows'] +"
                       " b['rows']}"),
            'mode': 'python'
        }
        self.analysis_r = {
            'name': 'copy_table',
            'inputs': [
                {'name': 'a', 'type': 'table', 'format': 'r.dataframe'}
            ],
            'outputs': [
                {'name': 'b', 'type': 'table', 'format': 'r.dataframe'}
            ],
            'script': 'b <- a',
            'mode': 'r'
        }
        self.test_input = {
            'a': {
                'format': 'rows.json',
                'data': ('{"fields": ["aa", "bb"], '
                         '"rows": [{"aa": 1, "bb": 2}]}')
            },
            'b': {
                'format': 'rows.json',
                'data': ('{"fields": ["aa", "bb"],'
                         '"rows": [{"aa": 3, "bb": 4}]}')
            }
        }
        import pymongo
        import bson
        self.db = pymongo.MongoClient('mongodb://localhost')['test']
        self.db['a'].drop()
        self.aobj = collections.OrderedDict([
            ('_id', bson.ObjectId('530cdb1add29bc5628984303')),
            ('bar', 2.0), ('foo', 1.0)])
        self.db['a'].insert(self.aobj)
        self.db['b'].drop()
        self.bobj = collections.OrderedDict([
            ('_id', bson.ObjectId('530cdb23dd29bc5628984304')),
            ('bar', 4.0), ('foo', 3.0)])
        self.db['b'].insert(self.bobj)

        # Change dir for loading analyses
        self.prevdir = os.getcwd()
        cur_path = os.path.dirname(os.path.realpath(__file__))
        os.chdir(cur_path)
        self.analysis_path = os.path.join(cur_path, '..', 'analysis')

    def tearDown(self):
        os.chdir(self.prevdir)

    def test_json(self):
        outputs = run(
            self.analysis,
            inputs=self.test_input,
            outputs={
                'c': {'format': 'rows.json'}
            })
        self.assertEqual(outputs['c']['format'], 'rows.json')
        self.assertEqual(
            outputs['c']['data'],
            '{"fields": ["aa", "bb"], '
            '"rows": [{"aa": 1, "bb": 2}, {"aa": 3, "bb": 4}]}')

    def test_bson(self):
        import pymongo
        outputs = run(
            self.analysis,
            inputs={
                'a': {
                    'format': 'objectlist.bson',
                    'mode': 'mongodb',
                    'db': 'test',
                    'collection': 'a'
                },
                'b': {
                    'format': 'objectlist.bson',
                    'mode': 'mongodb',
                    'db': 'test',
                    'collection': 'b'
                }
            },
            outputs={
                'c': {
                    'format': 'objectlist.bson',
                    'mode': 'mongodb',
                    'db': 'test',
                    'collection': 'temp'
                }
            })
        self.assertEqual(outputs['c']['format'], 'objectlist.bson')
        coll = pymongo.MongoClient('mongodb://localhost')['test']['temp']
        self.assertEqual([d for d in coll.find()], [self.aobj, self.bobj])

    def test_file(self):
        tmp = tempfile.mktemp()
        outputs = run(
            self.analysis,
            inputs=self.test_input,
            outputs={
                'c': {'format': 'csv', 'path': tmp, 'mode': 'local'}
            }
        )
        with open(tmp, 'r') as fp:
            output = fp.read()
        os.remove(tmp)
        self.assertEqual(outputs['c']['format'], 'csv')
        self.assertEqual(output.splitlines(), ['aa,bb', '1,2', '3,4'])

    def test_csv(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'csv', 'data': 'a,b,c\n1,2,3'},
                'b': {'format': 'csv', 'data': 'a,b,c\n4,5,6'}
            },
            outputs={
                'c': {'format': 'csv'}
            })
        self.assertEqual(outputs['c']['format'], 'csv')
        self.assertEqual(outputs['c']['data'].splitlines(),
                         ['a,b,c', '1,2,3', '4,5,6'])

    def test_singlecolumn(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'csv', 'data': 'A\none\ntwo'},
                'b': {'format': 'csv', 'data': 'A\nthree\nfour'}
            },
            outputs={
                'c': {'format': 'csv'}
            })
        self.assertEqual(outputs['c']['format'], 'csv')
        self.assertEqual(outputs['c']['data'].splitlines(),
                         ['A', 'one', 'two', 'three', 'four'])

    def test_singlerow(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'csv', 'data': 'A,one,two'},
                'b': {'format': 'csv', 'data': 'A,three,four'}
            },
            outputs={
                'c': {'format': 'csv'}
            })
        self.assertEqual(outputs['c']['format'], 'csv')
        # Only the 'header' of the first input is preserved.
        self.assertEqual(outputs['c']['data'].splitlines(),
                         ['A,one,two'])

    def test_tsv(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {'format': 'csv', 'data': 'a,b,c\n1,2,3'},
                'b': {'format': 'tsv', 'data': 'a\tb\tc\n4\t5\t6'}
            },
            outputs={
                'c': {'format': 'tsv'}
            })
        self.assertEqual(outputs['c']['format'], 'tsv')
        self.assertEqual(outputs['c']['data'].splitlines(),
                         ['a\tb\tc', '1\t2\t3', '4\t5\t6'])

    def test_mongo_to_python(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {
                    'format': 'objectlist.bson',
                    'mode': 'mongodb',
                    'db': 'test',
                    'collection': 'a'
                },
                'b': {
                    'format': 'objectlist.bson',
                    'mode': 'mongodb',
                    'db': 'test',
                    'collection': 'b'
                }
            },
            outputs={
                'c': {'format': 'rows'}
            })
        self.assertEqual(outputs['c']['format'], 'rows')
        self.assertEqual(outputs['c']['data'], {
            'fields': ['_id', 'bar', 'foo'], 'rows': [self.aobj, self.bobj]})

    def test_chaining(self):
        outputs = run(
            self.analysis,
            inputs={
                'a': {
                    'format': 'rows',
                    'data': {
                        'fields': ['a', 'b'], 'rows': [{'a': 1, 'b': 2}]}
                    },
                'b': {
                    'format': 'rows',
                    'data': {
                        'fields': ['a', 'b'], 'rows': [{'a': 3, 'b': 4}]
                    }
                }
            },
            outputs={
                'c': {'format': 'rows'}
            })

        outputs = run(
            self.analysis,
            inputs={
                'a': outputs['c'],
                'b': {
                    'format': 'rows',
                    'data': {'fields': ['a', 'b'], 'rows': [{'a': 5, 'b': 6}]}
                }
            },
            outputs={
                'c': {'format': 'rows'}
            })
        self.assertEqual(outputs['c']['format'], 'rows')
        self.assertEqual(outputs['c']['data'], {
            'fields': ['a', 'b'],
            'rows': [{'a': 1, 'b': 2}, {'a': 3, 'b': 4}, {'a': 5, 'b': 6}]
        })

    def test_objectlist_to_rows(self):
        objlist = [{'a': {'b': 5}}, {'a': {'b': {'c': 3}}}]
        output = convert('table', {
            'format': 'objectlist',
            'data': objlist
        }, {'format': 'rows'})
        self.assertEqual(output['format'], 'rows')
        self.assertEqual(output['data'], {
            'fields': ['a.b', 'a.b.c'],
            'rows': [{'a.b': 5}, {'a.b.c': 3}]})
        output = convert('table', {
            'format': 'rows',
            'data': output['data']
        }, {'format': 'objectlist'})
        self.assertEqual(output['data'], objlist)

    def test_column_names(self):
        output = convert('table', {
            'format': 'rows',
            'data': {'fields': ['a', 'b'], 'rows': [{'a': 6, 'b': 5}]}
        }, {'format': 'column.names'})
        self.assertEqual(output['format'], 'column.names')
        self.assertEqual(output['data'], ['a', 'b'])

    def test_column_names_csv(self):
        output = convert('table', {
            'format': 'csv',
            'data': ',a,b,longer name\n1,1,1,1\n2,2,2,2\n3,3,3,3\n'
        }, {'format': 'column.names'})
        self.assertEqual(output['format'], 'column.names')
        self.assertEqual(output['data'], ['', 'a', 'b', 'longer name'])

    def test_column_names_discrete(self):
        output = convert('table', {
            'format': 'rows',
            'data': {
                'fields': ['a', 'b', 'disc'],
                'rows': [{'a': 6, 'b': 5, 'disc': 'yes'}]
            }
        }, {'format': 'column.names.discrete'})
        self.assertEqual(output['format'], 'column.names.discrete')
        self.assertEqual(output['data'], ['disc'])

    def test_column_names_continuous(self):
        output = convert('table', {
            'format': 'rows',
            'data': {
                'fields': ['a', 'b', 'disc'],
                'rows': [{'a': 6, 'b': 5, 'disc': 'yes'}]
            }
        }, {'format': 'column.names.continuous'})
        self.assertEqual(output['format'], 'column.names.continuous')
        self.assertEqual(output['data'], ['a', 'b'])

    def test_r_dataframe(self):
        outputs = run(
            self.analysis_r,
            inputs={
                'a': {
                    'format': 'rows',
                    'data': {
                        'fields': ['aa', 'bb'], 'rows': [{'aa': 1, 'bb': 2}]
                    }
                }
            },
            outputs={
                'b': {'format': 'rows'}
            })
        self.assertEqual(outputs['b']['format'], 'rows')
        self.assertEqual(outputs['b']['data'], {
            'fields': ['aa', 'bb'], 'rows': [{'aa': 1, 'bb': 2}]})

    def test_flu(self):
        output = convert(
            'table',
            {
                'format': 'csv',
                'url': 'file://' + os.path.join('data', 'flu.csv')
            },
            {'format': 'column.names'}
        )
        self.assertEqual(output['format'], 'column.names')
        self.assertEqual(len(output['data']), 162)
        self.assertEqual(
            output['data'][:3],
            ['Date', 'United States', 'Alabama']
        )

    def test_header_detection(self):
        output = convert(
            'table',
            {'format': 'csv', 'data': 'a,b,c\n7,1,c\n8,2,f\n9,3,i'},
            {'format': 'rows'}
        )
        self.assertEqual(output['data']['fields'], ['a', 'b', 'c'])
        self.assertEqual(len(output['data']['rows']), 3)

        output = convert(
            'table',
            {'format': 'csv', 'data': '1,2,3\n7,10,\n,11,\n,12,'},
            {'format': 'rows'}
        )
        self.assertEqual(
            output['data']['fields'],
            ['1', '2', '3']
        )
        self.assertEqual(len(output['data']['rows']), 3)

    def test_sniffer(self):
        output = convert(
            'table',
            {
                'format': 'csv',
                'url': 'file://' + os.path.join('data', 'test.csv')
            },
            {'format': 'rows'}
        )
        self.assertEqual(len(output['data']['fields']), 32)
        self.assertEqual(output['data']['fields'][:3], [
            'FACILITY', 'ADDRESS', 'DATE OF INSPECTION'
        ])
        self.assertEqual(len(output['data']['rows']), 14)

        flu = load(os.path.join(
            self.analysis_path, 'xdata', 'flu.json'))

        output = run(
            flu,
            inputs={},
            outputs={'data': {'type': 'table', 'format': 'rows'}}
        )
        self.assertEqual(output['data']['data']['fields'][:3], [
            'Date', 'United States', 'Alabama'
        ])

    def test_big_header(self):
        output = convert(
            'table',
            {
                'format': 'csv',
                'url': 'file://' + os.path.join('data', 'RadiomicsData.csv')
            },
            {'format': 'rows'}
        )
        self.assertEqual(len(output['data']['fields']), 454)
        self.assertEqual(output['data']['fields'][:3], [
            'GLCM_autocorr', 'GLCM_clusProm', 'GLCM_clusShade'
        ])
        self.assertEqual(len(output['data']['rows']), 99)

    def test_nan(self):
        output = convert(
            'table',
            {
                'format': 'csv',
                'url': 'file://' + os.path.join('data', 'RadiomicsData.csv')
            },
            {'format': 'rows.json'}
        )
        data = json.loads(output['data'])
        self.assertEqual(len(data['fields']), 454)
        self.assertEqual(data['fields'][:3], [
            'GLCM_autocorr', 'GLCM_clusProm', 'GLCM_clusShade'
        ])
        self.assertEqual(len(data['rows']), 99)
        for row in data['rows']:
            for field in row:
                if isinstance(row[field], float):
                    self.assertFalse(math.isnan(row[field]))
                    self.assertFalse(math.isinf(row[field]))

    def test_objectlist(self):
        rows = {
            'fields': ['a', 'b'],
            'rows': [
                {'a': 1, 'b': 'x'},
                {'a': 4, 'b': 'y'}
            ]
        }
        objectlist = convert(
            'table',
            {'format': 'rows', 'data': rows},
            {'format': 'objectlist'}
        )['data']
        # Should have same row data
        self.assertEqual(objectlist, rows['rows'])

        rows2 = convert(
            'table',
            {'format': 'objectlist', 'data': objectlist},
            {'format': 'rows'}
        )['data']
        # Should have same fields but could be in different order
        self.assertEqual(set(rows['fields']), set(rows2['fields']))
        # Should have same row data
        self.assertEqual(rows['rows'], rows2['rows'])

        # Make sure we can go back and forth to JSON
        objectlist = convert(
            'table',
            convert(
                'table',
                {'format': 'objectlist', 'data': rows['rows']},
                {'format': 'objectlist.json'}
            ),
            {'format': 'objectlist'}
        )['data']
        self.assertEqual(rows['rows'], objectlist)

    def test_jsonlines(self):
        output = convert('table', {
            'format': 'jsonlines',
            'data': '{"a": 1, "b": 2}\n{"a": 3, "b": 4}'
        }, {'format': 'objectlist'})
        self.assertEqual(output['format'], 'objectlist')
        self.assertEqual(output['data'], [{'a': 1, 'b': 2}, {'a': 3, 'b': 4}])


if __name__ == '__main__':
    unittest.main()
