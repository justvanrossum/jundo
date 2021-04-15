#!/usr/bin/env python
from setuptools import setup, find_packages


with open("README.md", encoding="utf-8") as f:
    long_description = f.read()


setup(
    name="jundo",
    description="A general purpose library to help implement undo.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    use_scm_version={"write_to": "Lib/jundo/_version.py"},
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
