# -*- coding: utf-8 -*-
from setuptools import setup, find_packages, Extension
from setuptools.command.install import install
import subprocess
import os

with open("README.md") as f:
    readme = f.read()

with open("LICENSE") as f:
    license = f.read()

setup(
        name="covid",
        version="0.1.0",
        description="The most amazing covid simulation",
        author="Durham Data Miners",
        long_description=readme,
        license=license,
        packages=find_packages(exclude=("tests", "docs")),
)

