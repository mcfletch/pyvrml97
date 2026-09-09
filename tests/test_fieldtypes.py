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


