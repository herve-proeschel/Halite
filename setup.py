from distutils.core import setup
from Cython.Build import cythonize

setup(
    name = "RVX",
    ext_modules = cythonize('hlt/*.pyx'),
)