#!/usr/bin/env python3
"""
Setup script for DART-Planner with Cython extension support.
"""

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
import numpy as np
import os
import sys

# Try to import Cython
try:
    from Cython.Build import cythonize
    from Cython.Distutils import build_ext as cython_build_ext
    CYTHON_AVAILABLE = True
except ImportError:
    CYTHON_AVAILABLE = False
    print("Warning: Cython not available. C extensions will not be compiled.")

# Define Cython extensions
extensions = []

if CYTHON_AVAILABLE:
    extensions = [
        Extension(
            "dart_planner.control.rt_control_extension",
            sources=["src/dart_planner/control/rt_control_extension.pyx"],
            include_dirs=[np.get_include()],
            extra_compile_args=["-O3", "-march=native"],
            define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
        )
    ]

# Cython compiler directives
compiler_directives = {
    "language_level": "3",
    "boundscheck": False,
    "wraparound": False,
    "initializedcheck": False,
    "cdivision": True,
    "embedsignature": True,
}

# Custom build command
class CustomBuildExt(build_ext):
    def build_extensions(self):
        # Set compiler flags for optimization
        for ext in self.extensions:
            if hasattr(ext, 'extra_compile_args'):
                if sys.platform.startswith('linux'):
                    ext.extra_compile_args.extend(['-O3', '-march=native'])
                elif sys.platform.startswith('darwin'):
                    ext.extra_compile_args.extend(['-O3'])
                elif sys.platform.startswith('win'):
                    ext.extra_compile_args.extend(['/O2'])
        
        super().build_extensions()

# Setup configuration
if __name__ == "__main__":
    setup(
        ext_modules=cythonize(extensions, compiler_directives=compiler_directives) if CYTHON_AVAILABLE else [],
        cmdclass={'build_ext': CustomBuildExt} if CYTHON_AVAILABLE else {},
        zip_safe=False,  # Required for Cython extensions
    ) 