![Python package](https://github.com/IDAS-Durham/JUNE/workflows/Python%20package/badge.svg?branch=master)
[![codecov](https://codecov.io/gh/idas-durham/june/branch/master/graph/badge.svg?token=6TKUHtWxJZ)](https://codecov.io/gh/idas-durham/june)

# JUNE a COVID-19 modelling code

Repository for data and models built, named after [June Almeida](https://en.wikipedia.org/wiki/June_Almeida). June was the female Scottish virologist that first identified the coronavirus group of viruses. 


# Setup

The easiest way to get JUNE up and running is to install the latest stable version,

```
pip install june
```

and download the data with

```
get_june_data.sh
```

This will require a working installation of Openmpi or Intelmpi to compile ``mpi4py``. 

If you want to get the most up-to-date version of the code, then you can clone this repository, and install it using

```
pip install -e .
```

This should automatically install any requirements as well. You can then get the data using the same command above.

# How to use the code

Have a look at ``Notebooks/quickstart.ipynb`` for a gentle introduction to how JUNE works. You can also checkout the scripts in ``example_scripts``

# Tests

Run the tests with

```
cd tests
pytest
```

# Ongoing documentation sources

## ``docs`` directory: API reference & diagrams

The ``docs`` directory contains the source files and HTML outputs to
display all information auto-generated from the `june` codebase docstrings,
including auto-generated class and module diagrams. It is configured and
built using the
[Sphinx documentation tool](https://www.sphinx-doc.org/en/master/) which
uses the
[reStructuredText format](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html) for writing the source files.

**To view** the documentation as-is, open ``docs/built_docs/html/index.html``
to display the index page (effective homepage) in a browser, for example
by running from the root repository directory:

```
firefox docs/built_docs/html/index.html &
```

**To rebuild** the documentation to pick up on any local changes to the
codebase, change into the `docs` directory and run these `make` commands:

```
cd docs
make clean
make html
```

which will wipe the built HTML pages under ``built_docs/`` and then
re-build them based on the local repository state. Note that a working
environment for running `june` is required (for parsing the codebase)
and some dependencies are also needed, namely:

* [Sphinx](https://www.sphinx-doc.org/en/master/usage/installation.html);
* a Sphinx extension:
  * [``sphinx-pyreverse``](https://pypi.org/project/sphinx-pyreverse/) (for
    the auto-generation of the class and module diagrams).

Once the build is complete (it will provide a lot of feedback to STDOUT to
indicate progress) the pages can be viewed in the same way as above.

Feel free to add content via new sections and pages!


## Other resources

[Working Google Doc with meeting notes](https://docs.google.com/document/d/1EwwHZ0s3uVWmkEdhiw94cqrhfoLsTu_Pay2H11LjVOw/edit)

[MVP Google Doc with testing strategy](https://docs.google.com/document/d/1O0v6O3rOlCDKFD66Y9KbZTfKLQPgmP1ScuwrFv4sspo/edit?usp=sharing)

[Epidem. Parameters of COVID-19](https://docs.google.com/document/d/1724PeV7bg9V0JRuQE1vpktB08bFWDmjHrd6HKyOG1Ns/edit#heading=h.xiukf7vmhszk)



# Setup

Install Python3 header files. In Ubuntu and variants, this is the ``python3-dev`` package.

To install the package, install requisites

``pip install -r requirements.txt``

and

``pip install -e .``

# Quickstart

Refer to ``Notebooks/quickstart.ipynb``

# Data

The [IDAS gitlab](https://idas-gitlab.dur.scotgrid.ac.uk) [data repo](https://idas-gitlab.dur.scotgrid.ac.uk/JUNE/data) is used for storing all data files associated with JUNE covid modelling project. The repo makes use of git-lfs which works in a very similar way to regular git versioning but requires a few more steps.

**ATTENTION:** Please read the instructions below before doing anything with this repository.

**Note** Currently all files in the data directory will be tracked (the line `**` in the `.gitattributes` file does this). This means that all new files in the data folder should be tracked recursively, but this needs testing.

## Instructions

**Important**: If you only need to get the data, and do not want to add anything new

```
bash get_data.sh
```

will get you the data folder.

**Important** This is only for people who want to add new data. The data folder has to be a clone of the git lab repo. Make sure you do not initialize git lfs in this repo, but in the git-lab data one.

Before going any further, make a clean `JUNE/data/` folder to ensure nothing is overwritten.

To make data changes you must be in the `JUNE/data` foler which will have it's own git history separate from this one.

Large files are handled by git-lfs. First, git-lfs must be set up locally on your computer, please download it [here](https://git-lfs.github.com)

Once downloaded and installed, set up Git LFS for your user account by running:
```
git lfs install
```

To **pull**:

1. Pull `.gitattributes` file using: `git pull` - this defines what lfs data to pull later

2. Pull data according to `.gitattributes`: `git lfs pull`

To **add** data files:

1. Run: `git lfs track "[file]"` and remember the quotation marks

2. As normal: `git add "[file]"`

3. As normal:
```
git commit -m "[commit message]"
git push origin master
```

To **remove** files:

1. Open `.gitattributes`

2. Find and remove the associated Git LFS tracking rule within the .gitattributes file

3. Save and exit the .gitattributes file

4. Commit and push as normal the changes to the file


This procedure will stop the file from being tracked but will not remove it permanently. This is not an issue at the moment and should be left to admin to do.
