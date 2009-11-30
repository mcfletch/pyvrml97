"""Module to allow using strings to specify colors"""
def stringToColor( value ):
    """Given a string/unicode value, determine appropriate color"""
    value = value.lower()
    possible = cssColors.get( value )
    if possible:
        return possible
    if value and value[0] == '#':
        # HTML-style #hex encoding
        possible = int( value[1:],16)
        return toFloat(possible,16),toFloat(possible,8), toFloat(possible,0)
    else:
        raise ValueError( """String %(value)r couldn't be recognised as a color name, or #FFFFFF style encoding"""%locals())
def toInt( value ):
    """Take float value and give single-byte integer equivalent"""
    return int(round(value*255,0))
def toFloat( value, shift=0 ):
    """Take single-byte integer value return floating point equivalent"""
    return ((value&(255<<shift))>>shift)/255.0
    

cssColors = {
    'black' : (0.0,0.0,0.0),
    'dimgray' : (0.4118,0.4118,0.4118),
    'gray' : (0.502,0.502,0.502),
    'darkgray' : (0.6627,0.6627,0.6627),
    'silver' : (0.7529,0.7529,0.7529),
    'lightgrey' : (0.8275,0.8275,0.8275),
    'gainsboro' : (0.8627,0.8627,0.8627),
    'whitesmoke' : (0.9608,0.9608,0.9608),
    'white' : (1.0,1.0,1.0),
    'snow' : (1.0,0.9804,0.9804),
    'rosybrown' : (0.7373,0.5608,0.5608),
    'lightcoral' : (0.9412,0.502,0.502),
    'indianred' : (0.8039,0.3608,0.3608),
    'brown' : (0.6471,0.1647,0.1647),
    'firebrick' : (0.698,0.1333,0.1333),
    'maroon' : (0.502,0.0,0.0),
    'darkred' : (0.5451,0.0,0.0),
    'red' : (1.0,0.0,0.0),
    'mistyrose' : (1.0,0.8941,0.8824),
    'salmon' : (0.9804,0.502,0.4471),
    'tomato' : (1.0,0.3882,0.2784),
    'darksalmon' : (0.9137,0.5882,0.4784),
    'coral' : (1.0,0.498,0.3137),
    'orangered' : (1.0,0.2706,0.0),
    'lightsalmon' : (1.0,0.6275,0.4784),
    'sienna' : (0.6275,0.3216,0.1765),
    'seashell' : (1.0,0.9608,0.9333),
    'chocolate' : (0.8235,0.4118,0.1176),
    'saddlebrown' : (0.5451,0.2706,0.0745),
    'sandybrown' : (0.9569,0.6431,0.3765),
    'peachpuff' : (1.0,0.8549,0.7255),
    'peru' : (0.8039,0.5216,0.2471),
    'linen' : (0.9804,0.9412,0.902),
    'bisque' : (1.0,0.8941,0.7686),
    'burlywood' : (0.8706,0.7216,0.5294),
    'darkorange' : (1.0,0.549,0.0),
    'antiquewhite' : (0.9804,0.9216,0.8431),
    'tan' : (0.8235,0.7059,0.549),
    'blanchedalmond' : (1.0,0.9216,0.8039),
    'navajowhite' : (1.0,0.8706,0.6784),
    'papayawhip' : (1.0,0.9373,0.8353),
    'moccasin' : (1.0,0.8941,0.7098),
    'oldlace' : (0.9922,0.9608,0.902),
    'wheat' : (0.9608,0.8706,0.702),
    'orange' : (1.0,0.6471,0.0),
    'floralwhite' : (1.0,0.9804,0.9412),
    'goldenrod' : (0.8549,0.6471,0.1255),
    'cornsilk' : (1.0,0.9725,0.8627),
    'gold' : (1.0,0.8431,0.0),
    'lemonchiffon' : (1.0,0.9804,0.8039),
    'palegoldenrod' : (0.9333,0.9098,0.6667),
    'khaki' : (0.9412,0.902,0.549),
    'darkkhaki' : (0.7412,0.7176,0.4196),
    'ivory' : (1.0,1.0,0.9412),
    'beige' : (0.9608,0.9608,0.8627),
    'lightyellow' : (1.0,1.0,0.8784),
    'lightgoldenrodyellow' : (0.9804,0.9804,0.8235),
    'darkgoldenrod' : (0.7216,0.7137,0.0431),
    'olive' : (0.502,0.502,0.0),
    'yellow' : (1.0,1.0,0.0),
    'yellowgreen' : (0.6627,0.8039,0.1961),
    'olivedrab' : (0.4196,0.5569,0.1373),
    'darkolivegreen' : (0.3333,0.4196,0.1843),
    'greenyellow' : (0.6784,1.0,0.1843),
    'chartreuse' : (0.498,1.0,0.0),
    'lawngreen' : (0.4863,0.9882,0.0),
    'honeydew' : (0.9412,1.0,0.9412),
    'darkseagreen' : (0.5608,0.7373,0.5608),
    'lightgreen' : (0.5647,0.9333,0.5647),
    'palegreen' : (0.5961,0.9843,0.5961),
    'forestgreen' : (0.1333,0.5451,0.1333),
    'limegreen' : (0.1961,0.8039,0.1961),
    'darkgreen' : (0.0,0.3922,0.0),
    'green' : (0.0,0.502,0.0),
    'lime' : (0.0,1.0,0.0),
    'mediumseagreen' : (0.2353,0.702,0.4431),
    'seagreen' : (0.1804,0.5451,0.3412),
    'mintcream' : (0.9608,1.0,0.9804),
    'springgreen' : (0.0,1.0,0.498),
    'mediumspringgreen' : (0.0,0.9804,0.6039),
    'mediumaquamarine' : (0.4,0.8039,0.6667),
    'aquamarine' : (0.498,1.0,0.8314),
    'turquoise' : (0.251,0.8784,0.8157),
    'mediumturquoise' : (0.2824,0.8196,0.8),
    'lightseagreen' : (0.1255,0.698,0.6667),
    'azure' : (0.9412,1.0,1.0),
    'lightcyan' : (0.8784,1.0,1.0),
    'paleturquoise' : (0.6863,0.9333,0.9333),
    'darkslategray' : (0.1843,0.3098,0.3098),
    'teal' : (0.0,0.502,0.502),
    'darkcyan' : (0.0,0.5451,0.5451),
    'aqua' : (0.0,1.0,1.0),
    'cyan' : (0.0,1.0,1.0),
    'cadetblue' : (0.3725,0.6196,0.6275),
    'darkturquoise' : (0.0,0.8078,0.8196),
    'powderblue' : (0.6902,0.8784,0.902),
    'lightblue' : (0.6784,0.8471,0.902),
    'deepskyblue' : (0.0,0.749,1.0),
    'skyblue' : (0.5294,0.8078,0.9294),
    'lightskyblue' : (0.5294,0.8078,0.9804),
    'steelblue' : (0.2745,0.5098,0.7059),
    'aliceblue' : (0.9412,0.9725,1.0),
    'slategray' : (0.4392,0.502,0.5647),
    'lightslategray' : (0.4667,0.5333,0.6),
    'dodgerblue' : (0.1176,0.5647,1.0),
    'lightsteelblue' : (0.6902,0.7686,0.8706),
    'cornflowerblue' : (0.3922,0.5843,0.9294),
    'royalblue' : (0.0157,0.0863,0.5647),
    'ghostwhite' : (0.9725,0.9725,1.0),
    'lavender' : (0.902,0.902,0.9804),
    'midnightblue' : (0.098,0.098,0.4392),
    'navy' : (0.0,0.0,0.502),
    'darkblue' : (0.0,0.0,0.5451),
    'mediumblue' : (0.0,0.0,0.8039),
    'blue' : (0.0,0.0,1.0),
    'darkslateblue' : (0.2824,0.2392,0.5451),
    'slateblue' : (0.4157,0.3529,0.8039),
    'mediumslateblue' : (0.4824,0.4078,0.9333),
    'mediumpurple' : (0.5765,0.4392,0.8588),
    'blueviolet' : (0.5412,0.1686,0.8863),
    'indigo' : (0.2941,0.0,0.5098),
    'darkorchid' : (0.6,0.1961,0.8),
    'darkviolet' : (0.5804,0.0,0.8275),
    'mediumorchid' : (0.7294,0.3333,0.8275),
    'thistle' : (0.8471,0.749,0.8471),
    'plum' : (0.8667,0.6275,0.8667),
    'violet' : (0.9333,0.5098,0.9333),
    'purple' : (0.502,0.0,0.502),
    'darkmagenta' : (0.5451,0.0,0.5451),
    'fuchsia' : (1.0,0.0,1.0),
    'magenta' : (1.0,0.0,1.0),
    'orchid' : (0.8549,0.4392,0.8392),
    'mediumvioletred' : (0.7804,0.0824,0.5216),
    'deeppink' : (1.0,0.0784,0.5765),
    'hotpink' : (1.0,0.4118,0.7059),
    'lavenderblush' : (1.0,0.9412,0.9608),
    'palevioletred' : (0.8588,0.4392,0.5765),
    'pink' : (1.0,0.7529,0.8039),
    'crimson' : (0.8627,0.0784,0.2353),
    'lightpink' : (1.0,0.7137,0.7569),
}

if __name__ == "__main__":
    import unittest
    from vrml import arrays
    class ColorTests(unittest.TestCase):
        def testForwardName (self):
            for name, value in cssColors.items():
                assert stringToColor( name ) == value
        def testForwardHexidecimal (self):
            for name, value in cssColors.items ():
                representation = '#%02x%02x%02x'%tuple(map(toInt,value))
                result = stringToColor( representation )
                assert arrays.allclose( result, value, 0.001), """Expected %r, got %r"""%(value, result)
    unittest.main ()