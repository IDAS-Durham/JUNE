[![Python package](https://github.com/IDAS-Durham/JUNE/actions/workflows/check.yml/badge.svg)](https://github.com/IDAS-Durham/JUNE/actions/workflows/check.yml)
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

## Conda installation (generally optional but required for M1 chip Macs)

As an alternative to the above, you can use conda:


    conda create -n june_env python=3.8 -y # need 3.8 for some deps
    conda activate june_env

    python --version

    conda install -y numba
    conda install -y -c anaconda hdf5

    python3 -m pip install -r JUNE-private/requirements.txt
    python3 -m pip install -r june_runs/requirements.txt

    pushd JUNE-private
    python3 -m pip install -e .
    popd

    pushd june_runs
    python3 -m pip install -e .
    popd


    # Change to fit your environment
    export INSTALL_DIR=$HOME
    # For Hartree
    #export INSTALL_DIR=$HCBASE/miniconda_base

    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    chmod +x Miniconda3-latest-Linux-x86_64.sh
    bash Miniconda3-latest-Linux-x86_64.sh -b -p $INSTALL_DIR/miniconda
    source $INSTALL_DIR/miniconda/bin/activate

### Notes for using Hartree and Cosma clusters

To download and setup conda:

    # Change to fit your environment
    export INSTALL_DIR=$HOME
    # For Hartree
    #export INSTALL_DIR=$HCBASE/miniconda_base

    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    chmod +x Miniconda3-latest-Linux-x86_64.sh
    bash Miniconda3-latest-Linux-x86_64.sh -b -p $INSTALL_DIR/miniconda
    source $INSTALL_DIR/miniconda/bin/activate


Then you will need to load OpenMPI, e.g -


    # Hartree: module load openmpi-gcc/2.1.1
    # Cosma: module load openmpi/3.0.1 gnu_comp/7.3.0

After this follow the instructions above for conda installation.

To activate it, use:

    . $HOME/miniconda/bin/activate
    # For Hartree
    #. $HCBASE/miniconda_base/miniconda/bin/activate
    
    conda activate june_env


## Installation FAQs

**Q:** I get errors with using mpi4y on a Mac<br/>
**A:** Try using homebrew to install the software by running: ``brew install mpi4py``. If working in a conda environment, 
use `pip install mpi4py` instead of `conda install`, as the latter will also install additional MPI-related packages that could prevent
your MPI paths from being correctly found.

**Q:** I get building errors for h5py, mpi4py and tables when trying to ``pip install -e .``<br/>
**A:** Try installing these packages (e.g., with ``conda install`` if working in a conda environment, but see above caveat for mpi4py) 
*before* attempting the full pip install, while enforcing the versions listed in the ``requirements.txt``. 
This may help to avoid incompatibilities with the hdf5 on your system (if any).
  

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

# Contributing
See our contributors guide [here](CONTRIBUTING).

# Docs
We have further documentation [here](docs/index.md).
