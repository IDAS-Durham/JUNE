# -*- coding: utf-8 -*-
from setuptools import setup, find_packages, Extension
from setuptools.command.install import install
import subprocess
import os
from os.path import abspath, dirname, join
from glob import glob

this_dir = abspath(dirname(__file__))
with open(join(this_dir, "LICENSE")) as f:
    license = f.read()
    
with open(join(this_dir, "README.md"), encoding="utf-8") as file:
    long_description = file.read()

with open(join(this_dir, "requirements.txt")) as f:
    requirements = f.read().split("\n")

scripts = glob("scripts/*.py") + glob("scripts/*.sh")

setup(
        name="june",
        version="1.0",
        description="A framework for high resolution Agent Based Modelling.",
        url="https://github.com/idas-durham/june",
        long_description_content_type='text/markdown',
        long_description=long_description,
        scripts=scripts,
        author="IDAS-Durham",
        author_email='arnauq@protonmail.com',
        license="MIT license",
        install_requires=requirements,
        packages = find_packages(exclude=["docs"]),
        include_package_data=True
)

