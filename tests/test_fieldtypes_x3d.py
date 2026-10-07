"""The field types X3D adds to VRML97's.

Each is read from a program's values and from text, held in the storage its
type names, written back as VRML text, and copied as a value of its own.
"""

import io
import unittest

import numpy as np

from vrml import field, fieldtypes
from vrml.vrml97 import linearise


def vrml(field_object, value):
    return field_object.vrmlstr(value, None)


class TestADouble(unittest.TestCase):
    def field(self):
        return fieldtypes.SFDouble(name='elevation')

    def test_it_is_registered(self):
        self.assertIs(field.baseFieldTypes['SFDouble'], fieldtypes.SFDouble)
        self.assertIs(field.baseEventTypes['SFDouble'], fieldtypes.SFDoubleEvt)

    def test_it_holds_a_python_float(self):
        value = self.field().coerce('6378137.0000001')
        self.assertIsInstance(value, float)
        self.assertEqual(value, 6378137.0000001)

    def test_it_defaults_to_zero(self):
        self.assertEqual(self.field().getDefault(), 0.0)

    def test_it_writes_every_digit(self):
        self.assertEqual(vrml(self.field(), 6378137.0000001), '6378137.0000001')


class TestAListOfDoubles(unittest.TestCase):
    def field(self):
        return fieldtypes.MFDouble(name='heights')

    def test_it_is_registered(self):
        self.assertIs(field.baseFieldTypes['MFDouble'], fieldtypes.MFDouble)
        self.assertIs(field.baseEventTypes['MFDouble'], fieldtypes.MFDoubleEvt)

    def test_it_holds_float64(self):
        value = self.field().coerce([1.0000000001, 2])
        self.assertEqual(value.dtype, np.float64)
        self.assertEqual(value[0], 1.0000000001)

    def test_it_reads_text(self):
        self.assertEqual(list(self.field().coerce('1, 2 3')), [1.0, 2.0, 3.0])

    def test_a_copy_is_its_own(self):
        original = self.field().coerce([1.0, 2.0])
        copy = self.field().copyValue(original)
        copy[0] = 9.0
        self.assertEqual(original[0], 1.0)


class TestAColourWithAlpha(unittest.TestCase):
    def field(self):
        return fieldtypes.SFColorRGBA(name='color')

    def test_it_is_registered(self):
        self.assertIs(field.baseFieldTypes['SFColorRGBA'], fieldtypes.SFColorRGBA)
        self.assertIs(field.baseEventTypes['SFColorRGBA'],
                      fieldtypes.SFColorRGBAEvt)

    def test_it_holds_four_float32_components(self):
        value = self.field().coerce([0.25, 0.5, 0.75, 1.0])
        self.assertEqual(value.dtype, np.float32)
        self.assertEqual(value.shape, (4,))

    def test_components_are_clamped_to_the_unit_range(self):
        self.assertEqual(list(self.field().coerce([-1, 2, 0.5, 3])),
                         [0.0, 1.0, 0.5, 1.0])

    def test_it_defaults_to_transparent_black(self):
        self.assertEqual(list(self.field().getDefault()), [0, 0, 0, 0])

    def test_it_writes_four_numbers(self):
        self.assertEqual(vrml(self.field(), self.field().coerce([0, 0.5, 1, 1])),
                         '0,.5,1,1')

    def test_three_numbers_are_refused(self):
        with self.assertRaises(ValueError):
            self.field().coerce([1, 1, 1])


class TestAListOfColoursWithAlpha(unittest.TestCase):
    def field(self):
        return fieldtypes.MFColorRGBA(name='color')

    def test_it_is_registered(self):
        self.assertIs(field.baseFieldTypes['MFColorRGBA'], fieldtypes.MFColorRGBA)
        self.assertIs(field.baseEventTypes['MFColorRGBA'],
                      fieldtypes.MFColorRGBAEvt)

    def test_it_holds_rows_of_four(self):
        value = self.field().coerce('1 0 0 1, 0 1 0 0.5')
        self.assertEqual(value.dtype, np.float32)
        self.assertEqual(value.shape, (2, 4))

    def test_components_are_clamped_to_the_unit_range(self):
        self.assertEqual(self.field().coerce([[2, -1, 0, 1]]).tolist(),
                         [[1.0, 0.0, 0.0, 1.0]])

    def test_it_is_empty_by_default(self):
        self.assertEqual(len(self.field().coerce(self.field().getDefault())), 0)


class TestAListOfBooleans(unittest.TestCase):
    def field(self):
        return fieldtypes.MFBool(name='flags')

    def test_it_is_registered(self):
        self.assertIs(field.baseFieldTypes['MFBool'], fieldtypes.MFBool)
        self.assertIs(field.baseEventTypes['MFBool'], fieldtypes.MFBoolEvt)

    def test_it_holds_a_bool_array(self):
        value = self.field().coerce([1, 0, True])
        self.assertEqual(value.dtype, np.bool_)
        self.assertEqual(value.tolist(), [True, False, True])

    def test_it_reads_either_spelling_of_the_words(self):
        self.assertEqual(self.field().coerce('true FALSE, TRUE false').tolist(),
                         [True, False, True, False])

    def test_a_word_that_is_not_a_boolean_is_refused(self):
        with self.assertRaises(ValueError):
            self.field().coerce('true maybe')

    def test_it_writes_the_vrml_words(self):
        self.assertEqual(vrml(self.field(), self.field().coerce([1, 0])),
                         '[ TRUE FALSE ]')

    def test_a_copy_is_its_own(self):
        original = self.field().coerce([True])
        copy = self.field().copyValue(original)
        copy[0] = False
        self.assertTrue(original[0])

    def test_it_checks_for_a_bool_array(self):
        self.assertTrue(self.field().check(np.array([True])))
        self.assertFalse(self.field().check([True]))


class TestAListOfImages(unittest.TestCase):
    def field(self):
        return fieldtypes.MFImage(name='images')

    def test_it_is_registered(self):
        self.assertIs(field.baseFieldTypes['MFImage'], fieldtypes.MFImage)
        self.assertIs(field.baseEventTypes['MFImage'], fieldtypes.MFImageEvt)

    def test_each_image_is_an_sfimage(self):
        images = self.field().coerce([[1, 1, 1, 0xFF], [2, 1, 3, 0xFF0000, 0x00FF00]])
        self.assertEqual(len(images), 2)
        self.assertEqual(list(images[1]), [2, 1, 3, 0xFF0000, 0x00FF00])
        self.assertEqual(images[0].dtype, np.uint32)

    def test_text_is_split_at_each_image_by_its_header(self):
        images = self.field().coerce('1 1 1 0xFF 2 1 3 0xFF0000 0x00FF00')
        self.assertEqual([list(image) for image in images],
                         [[1, 1, 1, 0xFF], [2, 1, 3, 0xFF0000, 0x00FF00]])

    def test_text_that_stops_inside_an_image_is_refused(self):
        with self.assertRaises(ValueError):
            self.field().coerce('2 2 1 0 0 0')

    def test_it_writes_each_image(self):
        images = self.field().coerce([[1, 1, 1, 255], [1, 1, 1, 0]])
        self.assertEqual(vrml(self.field(), images), '[ 1 1 1 255, 1 1 1 0 ]')

    def test_a_copy_is_its_own(self):
        original = self.field().coerce([[1, 1, 1, 255]])
        copy = self.field().copyValue(original)
        copy[0][3] = 0
        self.assertEqual(original[0][3], 255)


class TestAQuaternion(unittest.TestCase):
    def test_it_holds_four_numbers(self):
        value = fieldtypes.SFQuaternion(name='q').coerce('0 0 0 1')
        self.assertEqual(value.shape, (4,))
        self.assertIs(field.baseFieldTypes['SFQuaternion'], fieldtypes.SFQuaternion)

    def test_a_list_holds_rows_of_four(self):
        value = fieldtypes.MFQuaternion(name='q').coerce([0, 0, 0, 1, 0, 1, 0, 0])
        self.assertEqual(value.shape, (2, 4))
        self.assertIs(field.baseEventTypes['MFQuaternion'],
                      fieldtypes.MFQuaternionEvt)


class TestTheyWriteInAScene(unittest.TestCase):
    """The lineariser writes each through the field's own `vrmlstr`."""

    def test_a_prototype_field_of_each_type_is_written(self):
        for name in ('SFDouble', 'MFDouble', 'SFColorRGBA', 'MFColorRGBA',
                     'MFBool', 'MFImage', 'SFQuaternion', 'MFQuaternion'):
            declared = field.newField('value', name, 1)
            lineariser = linearise.Lineariser()
            lineariser.buffer = io.StringIO()
            declared.fieldVrmlstr(lineariser)
            self.assertIn('exposedField %s value' % name,
                          lineariser.buffer.getvalue())


if __name__ == '__main__':
    unittest.main()
