---
permalink: /
title: JUNE Documentation
layout: splash

header:
  overlay_image: /assets/images/tools-bg2.jpg
  overlay_filter: 0.4 # same as adding an opacity of 0.5 to a black background
  caption: "Photo credit: [**Louis Hansel on Unsplash**](https://unsplash.com/photos/Rf9eElW3Qxo) (modified)"
  actions:
    - label: "Getting started"
      url: /getting-started
    - label: "About"
      url: "/about/"
---

# JUNE: open-source individual-based epidemiology simulation

# Setup

The easiest way to get JUNE up and running is to install the latest stable version,

```
pip install june
```

and download the data by running the script:

```
get_june_data.sh
```

If the above fails, then manually clone the repo and run the script ```scripts/get_june_data.sh```.


Disclaimer: All the data is constructed by mixing different datasets from the Office for National Statistics (ONS), thus it may contain modifications. Please refer to the original source (cited in the [release paper](https://www.medrxiv.org/content/10.1101/2020.12.15.20248246v1)) for the raw dataset.

This will require a working installation of Open MPI or Intel MPI to compile ``mpi4py``. 

If you want to get the most up-to-date version of the code, then you can clone this repository, and install it using

```
pip install -e .
```

This should automatically install any requirements as well. You can then get the data using the same command as the pip version.

# How to use the code

Have a look at ``Notebooks/quickstart.ipynb`` for a gentle introduction to how JUNE works. You can also check out some scripts in ``example_scripts``.

The ``docs`` directory contains the source files and HTML outputs to
display all information auto-generated from the `june` codebase docstrings,
including auto-generated class and module diagrams.

# Tests

Run the tests with:

```
cd test_june
pytest
```
