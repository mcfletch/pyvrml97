import unittest,sys
from vrml.arrays import pi,array
from vrml.vrml97 import transformmatrix
from vrml.arrays import allclose,dot
DEGTORAD = transformmatrix.DEGTORAD
try:
    from vrml.vrml97 import _transformmatrix_accel
except ImportError:
    _transformmatrix_accel = None
from vrml.vrml97 import _transformmatrix

class TestTransformMatrix( unittest.TestCase ):
    def test_calculations( self ):
        for (matrix,point, expected, name) in self._create_test_matrix(
            transformmatrix.transMatrix,
            transformmatrix.rotMatrix,
            transformmatrix.scaleMatrix,
        ):
            try:
                result = dot( point,matrix)
            except TypeError as err:
                sys.stderr.write("""\nF (TypeError):\n\tpoint=%(point)s\n\t%(matrix)s\n"""%(locals()))
            else:
                assert allclose( result, expected, 0, 0.000001 ),(name,matrix,point,expected,result)
    
    def _create_test_matrix( self, transMatrix,rotMatrix,scaleMatrix ):
        return [
            (transMatrix( (1,0,0) )[0], (0, 0,0,1), (1,0,0,1), "Simple translation"),
            (transMatrix( (-1,-1,-1) )[0], (1, 1,1,1), (0,0,0,1), "Simple translation"),
            (transMatrix( (0,0,1) )[0], (0, 0,0,1), (0,0,1,1), "Simple translation"),
            (rotMatrix( (0,1,0,pi) )[0], (1, 0,0,1), (-1,0,0,1), "Simple rotation"),
            (rotMatrix( (0,1,0,pi/2) )[0], (1, 0,0,1), (0,0,-1,1), "Simple rotation"),
            (rotMatrix( (0,0,1,pi/2) )[0], (1, 0,0,1), (0,1,0,1), "Simple rotation"),
            (rotMatrix( (0,0,1,-(pi/2)) )[0], (1, 0,0,1), (0,-1,0,1), "Simple rotation"),
            (rotMatrix( (0,0,-1,-(pi/2)) )[0], (1, 0,0,1), (0,1,0,1), "Simple rotation"),
            (rotMatrix( (0,0,-2,-(pi/2)) )[0], (1, 0,0,1), (0,1,0,1), "Simple rotation (w/normalize)"),
            (rotMatrix( (1,0,0,-(pi/2)) )[0], (1, 0,0,1), (1,0,0,1), "Simple rotation"),
            (rotMatrix( (0,0,1,pi/2) )[0], (0,1,0,1), (-1,0,0,1), "Simple rotation"),
            (rotMatrix( (1,0,0,pi/2) )[0], (0,0,1,1), (0,-1,0,1), "Simple rotation"),
            (scaleMatrix( (1,1,2) )[0], (1, 1,1,1), (1,1,2,1), "Simple scale"),
            (scaleMatrix( (-1,1,2) )[0], (1, 1,1,1), (-1,1,2,1), "Simple scale"),
            (scaleMatrix( (-1,0,2) )[0], (1, 1,1,1), (-1,0,2,1), "Simple scale"),
            (scaleMatrix( (-1,0,0) )[0], (1, 1,1,1), (-1,0,0,1), "Simple scale"),
            (scaleMatrix( (0,0,0) )[0], (1, 1,1,1), (0,0,0,1), "Simple scale"),
            (rotMatrix([ 0.,0.,1., -0.515])[0], (1,0,0,1), (0.87029272,-0.49253485,0.,1.), "Make sure rotation uses float check for abs value" ),
        ]
        
    def test_perspectiveMatrix( self ):
        """Test that perspective matrix calculation matches expected values"""
        result = transformmatrix.perspectiveMatrix(
            59.999999999999993*DEGTORAD, 1.0, 0.29999999999999999, 50000
        )
        inverse = transformmatrix.perspectiveMatrix(
            59.999999999999993*DEGTORAD, 1.0, 0.29999999999999999, 50000, inverse=True,
        )
        
        expected = array([
            [ 1.73205081,  0.,          0.,          0.,        ],
            [ 0.,          1.73205081,  0.,          0.,        ],
            [ 0.,          0.,         -1.000012, -1.,        ],
            [ 0.,          0.,         -0.6000036,   0.,        ],],'f')
        assert allclose(result,expected), result
        
        test = array([ 20,8,5,1.0 ],'f')
        projected = dot( result, test )
        print(projected)
        unprojected = dot( inverse, projected )
        assert allclose( unprojected, test ), (unprojected, test)
    
    if _transformmatrix_accel:
        def test_cross_check( self ):
            first = self._create_test_matrix(
                _transformmatrix_accel.transMatrix,
                _transformmatrix_accel.rotMatrix,
                _transformmatrix_accel.scaleMatrix,
            )
            second = self._create_test_matrix(
                _transformmatrix.transMatrix,
                _transformmatrix.rotMatrix,
                _transformmatrix.scaleMatrix,
            )
            for (firstmatrix,_,_,_),(secondmatrix,point, _, name) in zip(first,second):
                assert allclose(firstmatrix,secondmatrix, atol=0.000001), (firstmatrix,secondmatrix,name)


