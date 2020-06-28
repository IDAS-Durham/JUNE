# -*- coding: utf-8 -*-
from setuptools import setup, find_packages, Extension
from setuptools.command.install import install
import subprocess
import os
from os.path import abspath, dirname, join

this_dir = abspath(dirname(__file__))
with open(join(this_dir, "LICENSE")) as f:
    license = f.read()
    
with open(join(this_dir, "README.md"), encoding="utf-8") as file:
    long_description = file.read()

with open(join(this_dir, "requirements.txt")) as f:
    requirements = f.read().split("\n")

setup(
        name="june",
        version="0.1.0",
        description="The most amazing covid simulation",
        url="https://github.com/idas-durham/june",
        long_description=long_description,
        author="IDAS-Durham",
        author_email='arnauq@protonmail.com',
        license="MIT license",
        install_requires=requirements,
        packages=['june',
                  'june.infection',
                  'june.infection_seed',
                  'june.demography',
                  'june.distributors',
                  'june.groups',
                  'june.groups.group',
                  'june.groups.leisure',
                  'june.groups.commute',
                  'june.groups.travel',
                  'june.interaction',
                  'june.logger',
                  'june.box',
                  'june.hdf5_savers',
                  'june.visualization']
)

