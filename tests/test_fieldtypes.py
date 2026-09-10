import unittest
from vrml import fieldtypes
xrange = range

class TestFieldTypes( unittest.TestCase ):
    def test_mfvec3f(self):
        should_work = [
            zip([1,2,3],[2,3,4],[5,6,7]),
            map(int,[1,2,3]),
            xrange(3),
        ]
        field = fieldtypes.MFVec3f(name="moo")
        for value in should_work:
            field.coerce(value),value



class TestCoercingAString(unittest.TestCase):
    """A field value written as text, which is how VRML97 spells one.

    ``[`` and ``]`` group an MFVec's rows in the file format, and commas
    separate them, so the array types strip all three before reading numbers.
    """

    def test_an_array_reads_a_plain_list_of_numbers(self):
        field = fieldtypes.SFArray(name="points")
        self.assertEqual(list(field.coerce('1 2 3 4 5 6')),
                         [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    def test_an_array_reads_bracketed_rows(self):
        field = fieldtypes.SFArray(name="points")
        self.assertEqual(list(field.coerce('[1 2 3] [4 5 6]')),
                         [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    def test_an_array_reads_comma_separated_values(self):
        field = fieldtypes.SFArray(name="points")
        self.assertEqual(list(field.coerce('1, 2, 3')), [1.0, 2.0, 3.0])

    def test_a_vector_field_reads_text_and_keeps_its_shape(self):
        field = fieldtypes.MFVec3f(name="points")
        coerced = field.coerce('[1 2 3] [4 5 6]')
        self.assertEqual(coerced.shape, (2, 3))
        self.assertEqual([list(row) for row in coerced],
                         [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])


class TestTheProductOfADimension(unittest.TestCase):
    """`length` is how many numbers one value of a vector field holds.

    An SFVec3f holds three, an SFVec2f two, and an MFVec divides its printed
    output into rows of them -- so writing a scene out reads this.
    """

    def test_a_three_vector_holds_three(self):
        self.assertEqual(fieldtypes.SFVec3f(name="v").length, 3)

    def test_a_two_vector_holds_two(self):
        self.assertEqual(fieldtypes.SFVec2f(name="v").length, 2)

    def test_a_rotation_holds_four(self):
        self.assertEqual(fieldtypes.SFRotation(name="r").length, 4)

    def test_asking_twice_answers_the_same(self):
        field = fieldtypes.SFVec3f(name="v")
        self.assertEqual(field.length, field.length)

    def test_a_vector_field_writes_itself_out(self):
        """What `length` is read for."""
        from vrml.vrml97 import linearise
        field = fieldtypes.MFVec3f(name="points")
        text = field.vrmlstr(field.coerce('[1 2 3] [4 5 6]'), linearise.Lineariser())
        self.assertIn('1', text)
        self.assertTrue(text.startswith('[') or text.startswith('\n'), text[:20])


class TestCoercingALazyIterable(unittest.TestCase):
    """`map`, `zip` and `range`, which a field declares it accepts.

    `field.SEQUENCE_TYPES` names them, so a caller building a value with
    `map(str, ...)` is doing what the field type says it may. They have no
    length, so a coercion that measures one has to draw the values out first.
    """

    def test_a_single_string_field_takes_a_map(self):
        field = fieldtypes.SFString(name="s")
        self.assertEqual(field.coerce(map(str, [7])), '7')

    def test_a_single_string_field_takes_a_zip(self):
        field = fieldtypes.SFString(name="s")
        self.assertEqual(field.coerce(zip('a', 'b')), "('a', 'b')")

    def test_a_single_string_field_takes_a_range(self):
        field = fieldtypes.SFString(name="s")
        self.assertEqual(field.coerce(range(1)), '0')

    def test_a_longer_map_joins(self):
        field = fieldtypes.SFString(name="s")
        self.assertEqual(field.coerce(map(str, [1, 2])), '12')
