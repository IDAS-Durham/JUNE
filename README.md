![Python package](https://github.com/IDAS-Durham/JUNE/workflows/Python%20package/badge.svg?branch=master)
[![codecov](https://codecov.io/gh/IDAS-Durham/JUNE-private/branch/master/graph/badge.svg?token=SYUJR5DPSZ)](https://codecov.io/gh/IDAS-Durham/JUNE-private)

# JUNE: open-source individual-based epidemiology simulation

This is the offical repository of JUNE, named after [June Almeida](https://en.wikipedia.org/wiki/June_Almeida), who was the female Scottish virologist that first identified the coronavirus group of viruses. checkout the [release paper](https://www.medrxiv.org/content/10.1101/2020.12.15.20248246v1) for a physical description of the model.


# Setup

The easiest way to get JUNE up and running is to install the latest stable version,

```
pip install june
```

and download the data by running the command

```
get_june_data.sh
```

if the above command fails, then manually clone the repo and use the script ```scripts/get_june_data.sh```.


Disclaimer: All the data is constructed by mixing different datasets from the Office for National Statistics (ONS), thus it may contain modifications. Please refere to the original source (cited in the [release paper](https://www.medrxiv.org/content/10.1101/2020.12.15.20248246v1)) for the raw dataset.

This will require a working installation of Openmpi or Intelmpi to compile ``mpi4py``. 

If you want to get the most up-to-date version of the code, then you can clone this repository, and install it using

```
pip install -e .
```

This should automatically install any requirements as well. You can then get the data using the same command as the pip version.

# How to use the code

Have a look at ``Notebooks/quickstart.ipynb`` for a gentle introduction to how JUNE works. You can also checkout some scripts in ``example_scripts``.

The ``docs`` directory contains the source files and HTML outputs to
display all information auto-generated from the `june` codebase docstrings,
including auto-generated class and module diagrams.

# Tests

Run the tests with

```
cd test_june
pytest
```
