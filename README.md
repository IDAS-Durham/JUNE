![Python package](https://github.com/IDAS-Durham/JUNE/workflows/Python%20package/badge.svg?branch=master)
[![codecov](https://codecov.io/gh/idas-durham/june/branch/master/graph/badge.svg?token=6TKUHtWxJZ)](https://codecov.io/gh/idas-durham/june)

# Policy simulation tool based on multi-agent epidemic modelling within settlements

This repo is a fork of the JUNE simulation tool originall designed for modelling the spread of COVID-19 in the UK. The model is named after [June Almeida](https://en.wikipedia.org/wiki/June_Almeida). June was the female Scottish virologist that first identified the coronavirus group of viruses. 

We focus on Cox's Bazar Kutupalong-Batukhali Expansion Site located in Banghladesh. The relevant sections of the camp under analysis can be found in the `camp_data/inputs/geography` folder (see Data section below).

# Contributing

Issues are being created and will serve as initial sources of jobs to be done.

Please create a new brach and, when done, submit a pull request and assign a reviewer. There are also tests which must pass before merging into master. While most of these tests are currently for the original UK cmodelling ode (and so please do not overwrite them), camp specific tests will be placed here: `test_june/camp_tests`.

With new code additions and alterations, please write tests to ensure future consistency.

All contributions to the codebase which are specific to camps should be in the ``camps/`` folder to make it easier to merge with the main repository. Changes that concern general functionality that can be applied to other countries, can be added to the ``june/`` source code folder.

In all possible instances, code should be added to the original codebase and not overwritten. E.g. if the default for the code is a file used for the UK, manually pass the camp file rather than altering the default. If writing a new file, feel free to customise it to the camp setting!

# Tests

Run the tests with

```
cd test_june
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

>>>>>>> original_june/master
[Epidem. Parameters of COVID-19](https://docs.google.com/document/d/1724PeV7bg9V0JRuQE1vpktB08bFWDmjHrd6HKyOG1Ns/edit#heading=h.xiukf7vmhszk)

# Setup


1. Clone the repo and install Python3 header files. In Ubuntu and variants, this is the ``python3-dev`` package.


2. To install the package, install requisites

```
pip install -r requirements.txt
pip install -e .
```

3. Get the data (see section below)

# Quickstart

Refer to ``Notebooks/quickstart camp.ipynb``

# Data

We have a GitLab LFS server for secure data storage. To run the model you will need to have a local version of this. To get access:

1. Sign up for an account on the [GitLab](https://idas-gitlab.dur.scotgrid.ac.uk) (Note: you do **not** need a Durham email as the text says)

2. Inform the repo owner (Joseph Bullock) and access will be granted to the [data repo](https://idas-gitlab.dur.scotgrid.ac.uk/Bullock/cpmodelling)

3. Clone the repo and [set up Git LFS](https://git-lfs.github.com)

4. Move the folder that will be greated to the JUNE home directory and call it: `camp_data` - this will allow the paths to be correctly initialised

5. Follow instructions below for Git LFS usage

**ATTENTION:** Please read the instructions below before doing anything with this repository.

**Note** Often all files in the data directory will be tracked (the line `**` in the `.gitattributes` file does this). This means that all new files in the data folder should be tracked recursively.

## Instructions

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
