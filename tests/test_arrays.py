"""The array abstraction the scenegraph reaches numpy through.

`vrml.arrays` is what let the package move from Numeric to numpy without every
node changing, and OpenGLContext and the projects built on it reach numpy
through it in turn. So what it exports is what a great deal of code sees under
those names, and a name that shadows a builtin with something that is not a
drop-in for it is a trap laid across all of that.

The reductions -- `sum`, `min`, `max`, `any`, `abs` -- shadow builtins
deliberately: taking the numpy one is the point, and each answers what the
builtin does for a scalar. `bool` is the exception, and the reason this file
names them one at a time rather than asserting a rule about the whole set.
"""

import builtins
import math

import unittest

from vrml import arrays


class TestWhatItShadows(unittest.TestCase):
    def test_bool_is_the_builtin(self):
        """`numpy.bool` is a scalar type, not a drop-in for the builtin.

        `isinstance(True, numpy.bool)` is False and `numpy.bool(1) is not
        True`, so a module reading `bool` out of here got a name that fails
        both of the things `bool` is used for.
        """
        self.assertIs(getattr(arrays, 'bool', builtins.bool), builtins.bool)
        self.assertNotIn('bool', arrays.__all__)

    def test_it_exports_no_other_type_that_shadows_a_builtin(self):
        """A shadowing *function* is the abstraction; a shadowing *type* is not.

        `sum` and the rest answer for a scalar what the builtin does. A type
        does not: it is what `isinstance` is asked about and what an
        annotation names.
        """
        shadowing_types = [
            name for name in arrays.__all__
            if isinstance(getattr(arrays, name, None), type)
            and hasattr(builtins, name)
            and getattr(arrays, name) is not getattr(builtins, name)
        ]
        self.assertEqual(shadowing_types, [])

    def test_the_reductions_are_still_numpy(self):
        """Removing one shadow must not take the abstraction with it."""
        for name in ('sum', 'min', 'max', 'any', 'abs'):
            self.assertIn(name, arrays.__all__)
            self.assertIsNot(getattr(arrays, name), getattr(builtins, name), name)

    def test_log_is_still_not_exported(self):
        """`math.log` and `numpy.log` differ, so neither is offered here."""
        self.assertNotIn('log', arrays.__all__)


class TestSafeCompare(unittest.TestCase):
    """Comparing two field values, either of which may be an array."""

    def test_two_equal_arrays_compare_equal(self):
        first = arrays.array([1.0, 2.0, 3.0], 'f')
        second = arrays.array([1.0, 2.0, 3.0], 'f')
        self.assertTrue(arrays.safeCompare(first, second))

    def test_two_different_arrays_do_not(self):
        first = arrays.array([1.0, 2.0, 3.0], 'f')
        second = arrays.array([9.0, 9.0, 9.0], 'f')
        self.assertFalse(arrays.safeCompare(first, second))

    def test_it_answers_a_real_bool(self):
        """A caller writing `if x is True` or storing the answer wants one."""
        first = arrays.array([1.0], 'f')
        answer = arrays.safeCompare(first, arrays.array([1.0], 'f'))
        self.assertIs(type(answer), builtins.bool)

    def test_none_compares_equal_to_none(self):
        self.assertTrue(arrays.safeCompare(None, None))

    def test_none_and_a_value_do_not_compare_equal(self):
        self.assertFalse(arrays.safeCompare(None, 3))
        self.assertFalse(arrays.safeCompare(3, None))

    def test_two_equal_scalars_compare_equal(self):
        self.assertTrue(arrays.safeCompare(3, 3))
        self.assertTrue(arrays.safeCompare(3.5, 3.5))
        self.assertTrue(arrays.safeCompare('a', 'a'))

    def test_values_of_different_types_do_not(self):
        self.assertFalse(arrays.safeCompare(arrays.array([1.0], 'f'), 'a'))


class TestTypeCode(unittest.TestCase):
    def test_it_answers_the_arrays_own_code(self):
        self.assertEqual(arrays.typeCode(arrays.array([1.0], 'f')), 'f')
        self.assertEqual(arrays.typeCode(arrays.array([1.0], 'd')), 'd')

    def test_it_wants_an_array_rather_than_a_sequence(self):
        """It reads the code off the value; a list carries none."""
        with self.assertRaises(AttributeError):
            arrays.typeCode([1.0, 2.0])


class TestContiguous(unittest.TestCase):
    def test_a_contiguous_array_is_answered_as_it_is(self):
        original = arrays.array([1.0, 2.0, 3.0], 'f')
        self.assertTrue(arrays.contiguous(original).flags['C_CONTIGUOUS'])

    def test_a_sliced_array_is_made_contiguous(self):
        sliced = arrays.array([[1.0, 2.0], [3.0, 4.0]], 'f')[:, 0]
        self.assertTrue(arrays.contiguous(sliced).flags['C_CONTIGUOUS'])


class TestWhichImplementation(unittest.TestCase):
    def test_it_names_the_one_it_is_using(self):
        self.assertEqual(arrays.implementation_name, 'numpy')

    def test_the_trig_is_the_array_kind(self):
        """`math.sin` keeps a float32 float32; the array one widens it."""
        self.assertIsNot(arrays.sin, math.sin)


if __name__ == '__main__':
    unittest.main()
