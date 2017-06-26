from unittest import TestCase
try:
    from inspect import signature
except ImportError:
    from funcsigs import signature

from girder_worker import types


class BaseTypeTest(TestCase):

    def test_unique_id(self):
        arg1 = types.base.Base('arg')
        arg2 = types.base.Base('arg')
        self.assertNotEqual(arg1, arg2)

    def test_serialize(self):
        arg = types.base.Base('arg')
        self.assertEqual('value', arg.serialize('value'))

    def test_deserialize(self):
        arg = types.base.Base('arg')
        self.assertEqual('value', arg.deserialize('value'))

    def test_default_value(self):
        def func(a, b='default value'):
            pass
        sig = signature(func)

        a = types.base.Base('a')
        a.set_parameter(sig.parameters['a'])

        self.assertFalse(a.has_default())

        b = types.base.Base('b')
        b.set_parameter(sig.parameters['b'])
        self.assertTrue(b.has_default())

    def test_describe_positional_arg(self):
        def func(a, b='default value'):
            pass
        sig = signature(func)

        a = types.base.Base('a')
        a.set_parameter(sig.parameters['a'])
        desc = a.describe()

        self.assertFalse(a.has_default())
        self.assertEqual(desc['id'], a.id)
        self.assertEqual(desc['name'], 'a')
        self.assertNotIn('default', desc)

    def test_describe_keyword_arg(self):
        def func(a, b='default value'):
            pass
        sig = signature(func)

        b = types.base.Base('b')
        b.set_parameter(sig.parameters['b'])
        desc = b.describe()

        self.assertTrue(b.has_default())
        self.assertEqual(desc['id'], b.id)
        self.assertEqual(desc['name'], 'b')
        self.assertIn('default', desc)
        self.assertEqual(desc['default'].get('data'), 'default value')

    def test_abstract_base_methods(self):
        def func(a, b='default value'):
            pass
        sig = signature(func)

        a = types.base.Base('a')
        a.set_parameter(sig.parameters['a'])
        value = {}
        self.assertIs(a.serialize(value), value)
        self.assertIs(a.deserialize(value), value)
        a.validate(value)


class BooleanTypeTest(TestCase):

    def test_describe_boolean(self):
        def func(bool):
            pass
        sig = signature(func)

        b = types.Boolean('bool')
        b.set_parameter(sig.parameters['bool'])
        desc = b.describe()

        self.assertEqual(desc['type'], 'boolean')
        self.assertIs(b.serialize(''), False)
        self.assertIs(b.serialize('a'), True)


class ChoiceTypeTest(TestCase):

    def test_describe_choice(self):
        def func(choice):
            pass
        sig = signature(func)

        choices = ('a', 'b', 'c')
        c = types.choice.Choice('choice', choices=choices)
        c.set_parameter(sig.parameters['choice'])
        desc = c.describe()

        self.assertEqual(desc['type'], None)
        self.assertEqual(desc['values'], choices)
        c.validate('a')
        with self.assertRaises(ValueError):
            c.validate('d')

    def test_describe_multichoice(self):
        def func(choice):
            pass
        sig = signature(func)

        choices = ('a', 'b', 'c')
        c = types.choice.Choice('choice', choices=choices)
        c.multiple = True
        c.set_parameter(sig.parameters['choice'])
        desc = c.describe()

        self.assertEqual(desc['type'], None)
        self.assertEqual(desc['values'], choices)
        c.validate(('a',))
        c.validate(('a', 'b'))
        with self.assertRaises(TypeError):
            c.validate('d')
        with self.assertRaises(ValueError):
            c.validate(('a', 'd'))


class ColorTypeTest(TestCase):

    def test_describe_color(self):
        def func(color):
            pass
        sig = signature(func)

        c = types.Color('color')
        c.set_parameter(sig.parameters['color'])
        desc = c.describe()
        self.assertEqual(desc['type'], 'color')


class IntegerTypeTest(TestCase):

    def test_describe_integer(self):
        def func(integer):
            pass
        sig = signature(func)

        i = types.Integer('integer')
        i.set_parameter(sig.parameters['integer'])
        desc = i.describe()

        self.assertEqual(desc['type'], 'integer')
        self.assertIs(i.serialize(1.0), 1)
        self.assertIs(i.serialize(1.1), 1)
        i.validate(2)


class NumberTypeTest(TestCase):

    def test_describe_number(self):
        def func(number):
            pass
        sig = signature(func)

        i = types.Number('number')
        i.set_parameter(sig.parameters['number'])
        desc = i.describe()

        self.assertEqual(desc['type'], 'number')
        self.assertEqual(i.serialize(1.5), 1.5)
        i.validate(2)

        with self.assertRaises(TypeError):
            i.validate('1')

    def test_describe_number_range(self):
        def func(number):
            pass
        sig = signature(func)

        i = types.Number('number', min=-1, max=1)
        i.set_parameter(sig.parameters['number'])
        desc = i.describe()

        self.assertEqual(desc['type'], 'number')
        i.validate(0.5)

        with self.assertRaises(ValueError):
            i.validate(1.5)


class NumberChoiceTypeTest(TestCase):

    def test_describe_number_choice(self):
        def func(choice):
            pass
        sig = signature(func)

        choices = (1, 3, 6)
        c = types.NumberChoice('choice', choices=choices)
        c.set_parameter(sig.parameters['choice'])
        desc = c.describe()

        self.assertEqual(desc['type'], 'number-enumeration')
        self.assertEqual(desc['values'], choices)
        c.validate(3)
        with self.assertRaises(ValueError):
            c.validate(2)


class NumberMultichoiceTypeTest(TestCase):

    def test_describe_number_multichoice(self):
        def func(choice):
            pass
        sig = signature(func)

        choices = (1, 3, 6)
        c = types.NumberMultichoice('choice', choices=choices)
        c.set_parameter(sig.parameters['choice'])
        desc = c.describe()

        self.assertEqual(desc['type'], 'number-enumeration-multiple')
        self.assertEqual(desc['values'], choices)
        c.validate((3,))
        c.validate(())
        with self.assertRaises(ValueError):
            c.validate((0, 1))


class NumberVectorTypeTest(TestCase):

    def test_describe_number_vector(self):
        def func(vector):
            pass
        sig = signature(func)

        v = types.NumberVector('vector')
        v.set_parameter(sig.parameters['vector'])
        desc = v.describe()

        self.assertEqual(desc['type'], 'number-vector')
        self.assertEqual(v.deserialize('1,2'), [1, 2])
        v.validate((1, 2))

        with self.assertRaises(TypeError):
            v.validate(1)

        with self.assertRaises(TypeError):
            v.validate(('1',))

    def test_describe_number_vector_range(self):
        def func(vector):
            pass
        sig = signature(func)

        v = types.NumberVector('vector', min=-10, max=10)
        v.set_parameter(sig.parameters['vector'])
        desc = v.describe()

        self.assertEqual(desc['type'], 'number-vector')
        v.validate((1, 2))

        with self.assertRaises(ValueError):
            v.validate((1, 11))


class RangeTypeTest(TestCase):

    def test_describe_range(self):
        def func(range):
            pass
        sig = signature(func)

        r = types.Range('range', min=0, max=10, step=0.1)
        r.set_parameter(sig.parameters['range'])
        desc = r.describe()

        self.assertEqual(desc['type'], 'range')
        r.validate(5.1)

        with self.assertRaises(ValueError):
            r.validate(-1)
        with self.assertRaises(ValueError):
            r.validate(11)

        self.assertEqual(r.serialize(5.51), 5.5)


class StringTypeTest(TestCase):

    def test_describe_string(self):
        def func(string):
            pass
        sig = signature(func)

        s = types.String('string')
        s.set_parameter(sig.parameters['string'])
        desc = s.describe()

        self.assertEqual(desc['type'], 'string')
        s.validate('test')
        with self.assertRaises(TypeError):
            s.validate(0)


class StringChoiceTypeTest(TestCase):

    def test_describe_string_choice(self):
        def func(string):
            pass
        sig = signature(func)

        choices = ('a', 'b', 'foo')
        s = types.StringChoice('string', choices=choices)
        s.set_parameter(sig.parameters['string'])
        desc = s.describe()

        self.assertEqual(desc['type'], 'string-enumeration')
        s.validate('foo')

        with self.assertRaises(ValueError):
            s.validate('f')


class StringMultichoiceTypeTest(TestCase):

    def test_describe_string_multichoice(self):
        def func(string):
            pass
        sig = signature(func)

        choices = ('a', 'b', 'foo')
        s = types.StringMultichoice('string', choices=choices)
        s.set_parameter(sig.parameters['string'])
        desc = s.describe()

        self.assertEqual(desc['type'], 'string-enumeration-multiple')
        s.validate(('foo', 'a'))

        with self.assertRaises(TypeError):
            s.validate('foo')
        with self.assertRaises(ValueError):
            s.validate(('foo', 'e'))


class StringVectorTypeTest(TestCase):

    def test_describe_string_vector(self):
        def func(vector):
            pass
        sig = signature(func)

        v = types.StringVector('vector')
        v.set_parameter(sig.parameters['vector'])
        desc = v.describe()

        self.assertEqual(desc['type'], 'string-vector')
        self.assertEqual(v.deserialize('1,2'), ['1', '2'])
        v.validate(('1', '2'))

        with self.assertRaises(TypeError):
            v.validate(1)

        with self.assertRaises(TypeError):
            v.validate((1,))
