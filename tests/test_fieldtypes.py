import unittest,sys
from vrml import fieldtypes
from vrml.arrays import allclose,dot,array
try:
    xrange 
except NameError:
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
            result = field.coerce(value),value 
            
        
