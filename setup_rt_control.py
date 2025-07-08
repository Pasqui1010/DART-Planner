#!/usr/bin/env python3
"""
Setup script for DART-Planner Real-Time Control Extension

Builds the Cython extension for high-performance real-time control loops.
"""

from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np
import os

# Compiler flags for optimization
extra_compile_args = [
    '-O3',                    # Maximum optimization
    '-march=native',          # Use native CPU instructions
    '-ffast-math',            # Fast math operations
    '-fomit-frame-pointer',   # Omit frame pointer for speed
    '-Wall',                  # Enable all warnings
    '-Wextra',                # Extra warnings
]

# Linker flags
extra_link_args = [
    '-O3',
]

# Platform-specific flags
if os.name == 'nt':  # Windows
    extra_compile_args.extend([
        '/O2',                 # Optimize for speed
        '/arch:AVX2',          # Use AVX2 instructions
    ])
    extra_link_args.extend([
        '/O2',
    ])
else:  # Unix-like systems
    extra_compile_args.extend([
        '-fPIC',               # Position independent code
        '-pthread',            # Thread support
    ])

# Define the extension
rt_control_extension = Extension(
    "dart_planner.control.rt_control_extension",
    sources=["src/dart_planner/control/rt_control_extension.pyx"],
    include_dirs=[np.get_include()],
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args,
    language="c++",
)

# Setup configuration
setup(
    name="dart_planner_rt_control",
    version="1.0.0",
    description="Real-time control extension for DART-Planner",
    author="DART-Planner Team",
    author_email="team@dart-planner.org",
    ext_modules=cythonize([rt_control_extension], compiler_directives={
        'language_level': 3,
        'boundscheck': False,
        'wraparound': False,
        'initializedcheck': False,
        'nonecheck': False,
        'cdivision': True,
    }),
    install_requires=[
        'numpy>=1.21.0',
        'cython>=3.0.0',
    ],
    python_requires='>=3.8',
    zip_safe=False,
) 