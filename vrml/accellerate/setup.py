from distutils.core import setup, Extension
setup(
	name="vrml.accellerate",
	version="1.0a1",
	ext_modules=[
		Extension("fieldaccel", ["fieldaccel.c"]),
		Extension("tmatrixaccel", ["tmatrixaccel.c"]),
		Extension("frustcullaccel", ["frustcullaccel.c"]),
	]
)