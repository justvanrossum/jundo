#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
    use_scm_version={"write_to": "Lib/jundo/_version.py"},
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
    setup_requires=["setuptools_scm"],
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
