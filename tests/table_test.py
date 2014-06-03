import romanesco
import os
import tempfile
import unittest
import collections
import vtk


class TestTable(unittest.TestCase):

    def setUp(self):
        self.analysis = {
            "name": "append_tables",
            "inputs": [
                {"name": "a", "type": "table", "format": "rows"},
                {"name": "b", "type": "table", "format": "rows"}
            ],
            "outputs": [{"name": "c", "type": "table", "format": "rows"}],
            "script": ("c = {'fields': a['fields'],"
                       + "'rows': a['rows'] + b['rows']}"),
            "mode": "python"
        }
        self.analysis_r = {
            "name": "copy_table",
            "inputs": [
                {"name": "a", "type": "table", "format": "r.dataframe"}
            ],
            "outputs": [
                {"name": "b", "type": "table", "format": "r.dataframe"}
            ],
            "script": "b <- a",
            "mode": "r"
        }
        self.test_input = {
            "a": {
                "format": "rows.json",
                "data": ('{"fields": ["aa", "bb"],'
                         + '"rows": [{"aa": 1, "bb": 2}]}')
            },
            "b": {
                "format": "rows.json",
                "data": ('{"fields": ["aa", "bb"],'
                         + '"rows": [{"aa": 3, "bb": 4}]}')
            }
        }
        import pymongo
        import bson
        self.db = pymongo.MongoClient("mongodb://localhost")["test"]
        self.db["a"].drop()
        self.aobj = collections.OrderedDict([
            ('_id', bson.ObjectId('530cdb1add29bc5628984303')),
            ('bar', 2.0), ('foo', 1.0)])
        self.db["a"].insert(self.aobj)
        self.db["b"].drop()
        self.bobj = collections.OrderedDict([
            ('_id', bson.ObjectId('530cdb23dd29bc5628984304')),
            ('bar', 4.0), ('foo', 3.0)])
        self.db["b"].insert(self.bobj)

        # Change dir for loading analyses
        self.prevdir = os.getcwd()
        cur_path = os.path.dirname(os.path.realpath(__file__))
        os.chdir(cur_path)
        self.analysis_path = os.path.join(cur_path, "..", "analysis")

    def tearDown(self):
        os.chdir(self.prevdir)

    def test_json(self):
        outputs = romanesco.run(
            self.analysis,
            inputs=self.test_input,
            outputs={
                "c": {"format": "rows.json"}
            })
        self.assertEqual(outputs["c"]["format"], "rows.json")
        self.assertEqual(
            outputs["c"]["data"],
            '{"fields": ["aa", "bb"], '
            + '"rows": [{"aa": 1, "bb": 2}, {"aa": 3, "bb": 4}]}')

    def test_bson(self):
        import pymongo
        outputs = romanesco.run(
            self.analysis,
            inputs={
                "a": {
                    "format": "bson.rows",
                    "uri": "mongodb://localhost/test/a"},
                "b": {
                    "format": "bson.rows",
                    "uri": "mongodb://localhost/test/b"}
            },
            outputs={
                "c": {
                    "format": "bson.rows",
                    "uri": "mongodb://localhost/test/temp"}
            })
        self.assertEqual(outputs["c"]["format"], "bson.rows")
        coll = pymongo.MongoClient("mongodb://localhost")["test"]["temp"]
        self.assertEqual([d for d in coll.find()], [self.aobj, self.bobj])

    def test_file(self):
        tmp = tempfile.mktemp()
        outputs = romanesco.run(
            self.analysis,
            inputs=self.test_input,
            outputs={
                "c": {"format": "csv", "uri": "file://" + tmp}
            }
        )
        with open(tmp, 'r') as fp:
            output = fp.read()
        os.remove(tmp)
        self.assertEqual(outputs["c"]["format"], "csv")
        self.assertEqual(output.splitlines(), ["aa,bb", "1,2", "3,4"])

    def test_csv(self):
        outputs = romanesco.run(
            self.analysis,
            inputs={
                "a": {"format": "csv", "data": 'a,b,c\n1,2,3'},
                "b": {"format": "csv", "data": 'a,b,c\n4,5,6'}
            },
            outputs={
                "c": {"format": "csv"}
            })
        self.assertEqual(outputs["c"]["format"], "csv")
        self.assertEqual(outputs["c"]["data"].splitlines(),
                         ["a,b,c", "1,2,3", "4,5,6"])

    def test_tsv(self):
        outputs = romanesco.run(
            self.analysis,
            inputs={
                "a": {"format": "csv", "data": 'a,b,c\n1,2,3'},
                "b": {"format": "tsv", "data": 'a\tb\tc\n4\t5\t6'}
            },
            outputs={
                "c": {"format": "tsv"}
            })
        self.assertEqual(outputs["c"]["format"], "tsv")
        self.assertEqual(outputs["c"]["data"].splitlines(),
                         ["a\tb\tc", "1\t2\t3", "4\t5\t6"])

    def test_vtktable(self):
        outputs = romanesco.run(
            self.analysis,
            inputs=self.test_input,
            outputs={
                "c": {"format": "vtktable"}
            })
        self.assertEqual(outputs["c"]["format"], "vtktable")
        t = outputs["c"]["data"]
        self.assertEqual(t.GetNumberOfRows(), 2)
        self.assertEqual(t.GetNumberOfColumns(), 2)
        self.assertEqual(t.GetValueByName(0, "aa"), 1)
        self.assertEqual(t.GetValueByName(1, "aa"), 3)
        self.assertEqual(t.GetValueByName(0, "bb"), 2)
        self.assertEqual(t.GetValueByName(1, "bb"), 4)

    def test_mongo_to_python(self):
        outputs = romanesco.run(
            self.analysis,
            inputs={
                "a": {
                    "format": "bson.rows",
                    "uri": "mongodb://localhost/test/a"
                },
                "b": {
                    "format": "bson.rows",
                    "uri": "mongodb://localhost/test/b"
                }
            },
            outputs={
                "c": {"format": "rows"}
            })
        self.assertEqual(outputs["c"]["format"], "rows")
        self.assertEqual(outputs["c"]["data"], {
            'fields': ['_id', 'bar', 'foo'], 'rows': [self.aobj, self.bobj]})

    def test_chaining(self):
        outputs = romanesco.run(
            self.analysis,
            inputs={
                "a": {
                    "format": "rows",
                    "data": {
                        "fields": ["a", "b"], "rows": [{"a": 1, "b": 2}]}
                    },
                "b": {
                    "format": "rows",
                    "data": {
                        "fields": ["a", "b"], "rows": [{"a": 3, "b": 4}]
                    }
                }
            },
            outputs={
                "c": {"format": "rows"}
            })

        outputs = romanesco.run(
            self.analysis,
            inputs={
                "a": outputs["c"],
                "b": {
                    "format": "rows",
                    "data": {"fields": ["a", "b"], "rows": [{"a": 5, "b": 6}]}
                }
            },
            outputs={
                "c": {"format": "rows"}
            })
        self.assertEqual(outputs["c"]["format"], "rows")
        self.assertEqual(outputs["c"]["data"], {
            "fields": ["a", "b"],
            "rows": [{"a": 1, "b": 2}, {"a": 3, "b": 4}, {"a": 5, "b": 6}]
        })

    def test_column_names(self):
        output = romanesco.convert("table", {
            "format": "rows",
            "data": {"fields": ["a", "b"], "rows": [{"a": 6, "b": 5}]}
        }, {"format": "column.names"})
        self.assertEqual(output["format"], "column.names")
        self.assertEqual(output["data"], ["a", "b"])

    def test_column_names_discrete(self):
        output = romanesco.convert("table", {
            "format": "rows",
            "data": {
                "fields": ["a", "b", "disc"],
                "rows": [{"a": 6, "b": 5, "disc": "yes"}]
            }
        }, {"format": "column.names.discrete"})
        self.assertEqual(output["format"], "column.names.discrete")
        self.assertEqual(output["data"], ["disc"])

    def test_column_names_continuous(self):
        output = romanesco.convert("table", {
            "format": "rows",
            "data": {
                "fields": ["a", "b", "disc"],
                "rows": [{"a": 6, "b": 5, "disc": "yes"}]
            }
        }, {"format": "column.names.continuous"})
        self.assertEqual(output["format"], "column.names.continuous")
        self.assertEqual(output["data"], ["a", "b"])

    def test_r_dataframe(self):
        outputs = romanesco.run(
            self.analysis_r,
            inputs={
                "a": {
                    "format": "rows",
                    "data": {
                        "fields": ["aa", "bb"], "rows": [{"aa": 1, "bb": 2}]
                    }
                }
            },
            outputs={
                "b": {"format": "rows"}
            })
        self.assertEqual(outputs["b"]["format"], "rows")
        self.assertEqual(outputs["b"]["data"], {
            "fields": ["aa", "bb"], "rows": [{"aa": 1, "bb": 2}]})

    def test_header_detection(self):
        output = romanesco.convert(
            "table",
            {"format": "csv", "data": "a,b,c\n7,1,c\n8,2,f\n9,3,i"},
            {"format": "rows"}
        )
        self.assertEqual(output["data"]["fields"], ["a", "b", "c"])
        self.assertEqual(len(output["data"]["rows"]), 3)

        output = romanesco.convert(
            "table",
            {"format": "csv", "data": "1,2,3\n7,10,\n,11,\n,12,"},
            {"format": "rows"}
        )
        self.assertEqual(
            output["data"]["fields"],
            ["Column 1", "Column 2", "Column 3"]
        )
        self.assertEqual(len(output["data"]["rows"]), 4)

    def test_sniffer(self):
        output = romanesco.convert(
            "table",
            {
                "format": "csv",
                "uri": "file://" + os.path.join("data", "test.csv")
            },
            {"format": "rows"}
        )
        self.assertEqual(len(output["data"]["fields"]), 32)
        self.assertEqual(output["data"]["fields"][:3], [
            "FACILITY", "ADDRESS", "DATE OF INSPECTION"
        ])
        self.assertEqual(len(output["data"]["rows"]), 14)

        flu = romanesco.load(os.path.join(
            self.analysis_path, "xdata", "flu.json"))

        output = romanesco.run(
            flu,
            inputs={},
            outputs={"data": {"type": "table", "format": "rows"}}
        )
        self.assertEqual(len(output["data"]["data"]["fields"]), 162)
        self.assertEqual(output["data"]["data"]["fields"][:3], [
            "Date", "United States", "Alabama"
        ])

    def test_vector(self):
        rows = {
            "fields": ["a", "b"],
            "rows": [
                {"a": [1, 2, 3], "b": ['1', '2']},
                {"a": [4, 5, 6], "b": ['3', '4']}
            ]
        }

        # Conversion to vtkTable
        vtktable = romanesco.convert(
            "table",
            {"format": "rows", "data": rows},
            {"format": "vtktable"}
        )["data"]
        self.assertEqual(vtktable.GetNumberOfRows(), 2)
        self.assertEqual(vtktable.GetNumberOfColumns(), 2)
        a = vtktable.GetColumnByName("a")
        b = vtktable.GetColumnByName("b")
        self.assertEqual(a.GetNumberOfComponents(), 3)
        self.assertEqual(b.GetNumberOfComponents(), 2)
        self.assertTrue(isinstance(a, vtk.vtkDoubleArray))
        self.assertTrue(isinstance(b, vtk.vtkStringArray))
        for i in range(6):
            self.assertEqual(a.GetValue(i), i + 1)
        for i in range(4):
            self.assertEqual(b.GetValue(i), str(i + 1))

        # Conversion back to rows
        rows2 = romanesco.convert(
            "table",
            {"format": "vtktable", "data": vtktable},
            {"format": "rows"}
        )["data"]
        self.assertEqual(rows2, rows)

if __name__ == '__main__':
    unittest.main()
