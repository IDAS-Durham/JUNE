[![Python package](https://github.com/IDAS-Durham/JUNE/actions/workflows/python-publish.yml/badge.svg)](https://github.com/IDAS-Durham/JUNE/actions/workflows/python-publish.yml)
[![codecov](https://codecov.io/gh/IDAS-Durham/JUNE/branch/master/graph/badge.svg?token=6TKUHtWxJZ)](https://codecov.io/gh/IDAS-Durham/JUNE)

# JUNE: open-source individual-based epidemiology simulation

This is the offical repository of JUNE, named after [June Almeida](https://en.wikipedia.org/wiki/June_Almeida), who was the female Scottish virologist that first identified the coronavirus group of viruses. A paper introducing our modelling framework in the case of modelling the spread of COVID-19 in England has been published in [Royal Society Open Science](https://royalsocietypublishing.org/doi/full/10.1098/rsos.210506).

Please cite our paper as follows:

```
@article{doi:10.1098/rsos.210506,
  author = {Aylett-Bullock, Joseph  and Cuesta-Lazaro, Carolina  and Quera-Bofarull, Arnau  and Icaza-Lizaola, Miguel  and Sedgewick, Aidan  and Truong, Henry  and Curran, Aoife  and Elliott, Edward  and Caulfield, Tristan  and Fong, Kevin  and Vernon, Ian  and Williams, Julian  and Bower, Richard  and Krauss, Frank },
  title = {June: open-source individual-based epidemiology simulation},
  journal = {Royal Society Open Science},
  volume = {8},
  number = {7},
  pages = {210506},
  year = {2021},
  doi = {10.1098/rsos.210506},
  URL = {https://royalsocietypublishing.org/doi/abs/10.1098/rsos.210506},
  eprint = {https://royalsocietypublishing.org/doi/pdf/10.1098/rsos.210506},
}

```

To reproduce the plots to that paper vist our [paper plots repository](https://github.com/IDAS-Durham/june_paper_plots).

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
