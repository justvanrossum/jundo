#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
    version="0.1",  # see also jundo.__version__
    name="jundo",
    description="A general purpose library to help implement undo.",
    author="Just van Rossum",
    author_email="justvanrossum@gmail.com",
    url="https://github.com/justvanrossum/jundo",
    license="MIT",
    package_dir={"": "Lib"},
    packages=find_packages("Lib"),
    install_requires=[
        'dataclasses;python_version<"3.7"',
    ],
    extras_require={
        "testing": [
            "pytest",
        ],
    },
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Intended Audience :: Developers",
        "Topic :: Text Processing :: Fonts",
        "License :: OSI Approved :: MIT License",
    ],
)
