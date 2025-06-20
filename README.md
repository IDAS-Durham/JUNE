# JUNE Environment Setup Guide

This guide will help you set up the JUNE environment, which includes Python 3.12 and various scientific computing packages necessary for running JUNE.

## Prerequisites

- Administrative privileges (might be required for some package installations)
- Approximately 5-7 GB of free disk space (Anaconda requires more space than Miniconda)
- Git installed on your system

## Installation Steps

### 1. Clone the JUNE Repository

First, clone the JUNE repository to your local machine:

```bash
git clone https://github.com/mtcorread/june_merge.git
cd june_merge
```

### 2. Install Anaconda

If you don't already have Anaconda installed:

#### Windows
- Download [Anaconda](https://www.anaconda.com/download) for Windows
- Run the installer and follow the installation prompts
- It's recommended to add Anaconda to your PATH during installation (though this is not selected by default)

#### macOS
- Download [Anaconda](https://www.anaconda.com/download) for macOS
- Run the installer and follow the installation prompts
- Alternatively, install via Homebrew: `brew install --cask anaconda`
  - If using Homebrew, you'll need to add Anaconda to your path: `echo 'export PATH=/usr/local/anaconda3/bin:$PATH' >> ~/.zshrc` (or ~/.bash_profile)

#### Linux
- Download the [Anaconda](https://www.anaconda.com/download) installer for Linux
- Run: `bash Anaconda-latest-Linux-x86_64.sh`
- Follow the prompts and say "yes" when asked about initialising Anaconda

### 3. Create the JUNE Environment

Create a new Conda environment with Python 3.12:

```bash
conda create -n JUNE python=3.12
conda activate JUNE
```

### 4. Install Requirements

Install the required packages using pip and the requirements.txt file:

```bash
pip install -r requirements.txt
```

Note: The requirements.txt file does not include mpi4py as it can cause conflicts depending on your system setup. If you need MPI support, please refer to the "Optional MPI Installation" section below.

### 5. Install JUNE in Development Mode

Install the JUNE package in development mode:

```bash
pip install -e .
```

This command installs the package in "editable" or "development" mode, which means:
- Changes you make to the JUNE source code will immediately affect the installed package without requiring reinstallation
- The package is installed by creating a link to your source code rather than copying files
- Helpful for development as you can modify code and test changes immediately

### 6. Verify the Installation

Confirm the environment was installed correctly:

```bash
python -c "import numpy, pandas, h5py; print('NumPy:', numpy.__version__, '\nPandas:', pandas.__version__, '\nH5py:', h5py.__version__)"
```

This should display the versions of key packages without any errors.

## Environment Contents

The JUNE environment includes:
- Python 3.12 - The core programming language
- NumPy & SciPy - Fundamental packages for scientific computing
- Pandas - Data analysis and manipulation library
- Matplotlib & Plotly - Data visualisation libraries
- H5py - Interface to the HDF5 binary data format
- Numba - JIT compiler for accelerating Python code
- scikit-learn - Machine learning library
- PyTables - Package for managing hierarchical datasets
- NetworkX - Library for studying graphs and networks
- GeoSpatial libraries - GeoPandas, Shapely, Rasterio
- Various testing tools - pytest and coverage packages

## Optional MPI Installation

If you need MPI support for parallel computing:

### Ubuntu/Debian
```bash
sudo apt-get install build-essential openmpi-bin libopenmpi-dev
pip install mpi4py
```

### macOS with Homebrew
```bash
brew install open-mpi
pip install mpi4py
```

### Windows
MPI support on Windows can be challenging. Consider using Windows Subsystem for Linux (WSL) for better MPI support, or:
1. Install Microsoft MPI: https://www.microsoft.com/en-us/download/details.aspx?id=57467
2. Then: `pip install mpi4py`

## Troubleshooting

### HDF5/H5py Issues
If you encounter problems with H5py installation:
- Make sure you have the correct compilers installed
- You might need to reinstall h5py using: `pip install --no-binary=h5py h5py`

### Python Version Conflicts
If you see errors about Python version incompatibility:
- Ensure you're using a clean conda environment (no active environments when creating JUNE)
- Check that your Conda installation is up to date: `conda update conda`

### Package Installation Errors
If pip fails to install some packages:
- Try installing problematic packages individually
- Some may require system libraries; check the error messages for hints
- For Windows users, some scientific packages work best with Anaconda's distributions

### Updating the Environment
To update packages in the future:
```bash
conda activate JUNE
pip install --upgrade -r requirements.txt
```

### Removing the Environment
If you need to remove the environment:
```bash
conda deactivate
conda env remove -n JUNE
```

For more information or support, please refer to the official documentation or open an issue in the project repository.

## Creating a JUNE World

A key step in using JUNE is creating a "world" - a simulation environment with geographic locations, buildings, and populations. Here's how to create a basic world:

### Getting the Data

Before creating a world, you need to download the required data files:

1. Download the data from: [https://drive.google.com/drive/folders/1jShep54ZKsOknprO8uK4dgbjDI8gI660?usp=share_link](https://drive.google.com/drive/folders/1jShep54ZKsOknprO8uK4dgbjDI8gI660?usp=share_link)

2. The download contains a folder called "data" with a subfolder called "input". 

3. Place this data folder in the root of the JUNE folder (at the same level as the example_scripts and june directories).

### Understanding World Creation

A JUNE world consists of:
- Geographic areas (super areas, areas, and locations)
- Buildings (households, schools, hospitals, etc.)
- Population (people with demographic attributes)
- Leisure venues (pubs, cinemas, etc.)
- Travel networks (commuting patterns)

### Example: Creating a Basic World

The example script `example_scripts/create_world.py` allows you to select one of 5 different geographic areas to simulate:

1. **Original Example**: London + Bath + Cambridge
2. **Northumberland**: (Run without hospitals or stations)
3. **England**: Full country simulation
4. **Northumberland + Tyne and Wear**: Combined region
5. **Merseyside**: Liverpool and surrounding area

You can select which area to use by modifying the `choice` variable in the script.

Here's a step-by-step guide to create a world based on the example script:

1. **Activate your JUNE environment**:
   ```bash
   conda activate JUNE
   ```

2. **Create a script** or modify the example script at `example_scripts/create_world.py`

3. **Define geographic location**:
   ```python
   import os
   import numpy as np
   from june.geography import Geography
   
   # Define which MSOAs (Middle Layer Super Output Areas) to load
   # These are UK geographic units
   file_path = os.path.join(os.path.dirname(__file__), "london_areas.txt")
   msoas_to_load = np.loadtxt(file_path, dtype=np.str_)
   
   # Load geography for these areas
   geography = Geography.from_file({"super_area": msoas_to_load})
   ```

4. **Add buildings to the geography**:
   ```python
   from june.groups import Hospitals, Schools, Companies, CareHomes, Universities
   
   # Add different types of buildings
   geography.hospitals = Hospitals.for_geography(geography)
   geography.companies = Companies.for_geography(geography)
   geography.schools = Schools.for_geography(geography)
   geography.universities = Universities.for_geography(geography)
   geography.care_homes = CareHomes.for_geography(geography)
   ```

5. **Generate the world**:
   ```python
   from june.world import generate_world_from_geography
   
   # Generate world including households
   world = generate_world_from_geography(geography, include_households=True)
   ```

6. **Add leisure activities**:
   ```python
   from june.groups.leisure import (
       Pubs, Cinemas, Groceries, Gyms, generate_leisure_for_config
   )
   
   # Add different types of leisure venues
   world.pubs = Pubs.for_geography(geography)
   world.cinemas = Cinemas.for_geography(geography)
   world.groceries = Groceries.for_geography(geography)
   world.gyms = Gyms.for_geography(geography)
   
   # Generate leisure activities
   leisure = generate_leisure_for_config(world)
   leisure.distribute_social_venues_to_areas(
       areas=world.areas, super_areas=world.super_areas
   )  # Assigns possible social venues to people
   ```

7. **Add travel networks**:
   ```python
   from june.groups.travel import Travel
   
   # Initialise commuting patterns
   travel = Travel()
   travel.initialise_commute(world)
   ```

8. **Save the world**:
   ```python
   # Save the world to an HDF5 file to load it later
   world.to_hdf5("my_world.hdf5")
   print("World created and saved!")
   ```

9. **Run your script**:
   ```bash
   python create_world.py
   ```

This will create a world file (`my_world.hdf5`) that can be loaded in subsequent simulations.

### Common Issues with World Creation

- **Memory usage**: Creating large worlds can require significant RAM. Start with a small number of areas first.
- **Missing data**: Ensure all necessary data files are available in the expected locations.
- **HDF5 errors**: If you encounter errors saving or loading the world, check that h5py is properly installed.
- **Performance**: World creation can be time-consuming. The script includes profiling to help identify bottlenecks.

### Loading a Saved World

To use your saved world in a simulation:

```python
from june.world import World

# Load the world from the HDF5 file
world = World.from_hdf5("my_world.hdf5")
```

## Running a JUNE Simulation

After creating a world, the next step is to run an epidemiological simulation. Here's how to set up and run a basic simulation:

### Rat Population Dynamics

JUNE supports simulating rat populations as disease vectors. This can be activated or deactivated in the `example_scripts/run_simulation.py` file by modifying the following variables:

```python
# Enable rat population dynamics as disease vectors
# Set to True if modelling diseases with animal reservoirs
ratty_dynamics = True

# Generate visualisations of rat movement patterns
# Only relevant if ratty_dynamics is True
produce_rat_animations = True
```

**Note**: If you want to use the rat animation features, you will need to install FFmpeg on your system:

#### Ubuntu/Debian
```bash
sudo apt-get install ffmpeg
```

#### macOS with Homebrew
```bash
brew install ffmpeg
```

#### Windows
Download and install from: https://ffmpeg.org/download.html

### Understanding JUNE Simulations

A JUNE simulation involves:
- Loading a previously created world
- Setting up disease parameters and infection dynamics
- Configuring policies (interventions, restrictions, etc.)
- Defining interaction patterns
- Running the simulation over a time period
- Recording and analysing results

### Example: Running a Basic Simulation

Here's a step-by-step guide to running a simulation:

1. **Activate your JUNE environment**:
   ```bash
   conda activate JUNE
   ```

2. **Create a simulation script** or use the example at `example_scripts/run_simulation.py`

3. **Set simulation parameters**:
   ```python
   import os
   from june.epidemiology.infection.disease_config import DiseaseConfig
   from june.global_context import GlobalContext
   
   # Choose a disease model
   disease = "covid19"  # Options: "covid19", "measles", "ev-d68-v"
   
   # Initial infection rate (proportion of population)
   cpc = 0.01  # Cases per capita (e.g., 0.01 = 1% of population)
   
   # Set the starting date of the simulation
   seeding_date = "2020-03-01 8:00"
   
   # Configure the disease model
   disease_config = DiseaseConfig(disease)
   GlobalContext.set_disease_config(disease_config)
   ```

4. **Load the world and set up the simulator**:
   ```python
   from june.simulator import Simulator
   from june.interaction import Interaction
   from june.epidemiology.epidemiology import Epidemiology
   from june.epidemiology.infection_seed import InfectionSeed, InfectionSeeds
   from june.epidemiology.infection import InfectionSelector, InfectionSelectors
   from june.records import Record
   from june.policy import Policies
   from june.event import Events
   from june.groups.travel import Travel
   from june.groups.leisure import generate_leisure_for_config
   
   # Create a directory for results
   results_folder = "results"
   if not os.path.exists(results_folder):
       os.makedirs(results_folder)
   
   # Load the world (assuming you're using a Domain for better performance)
   from june.domains import Domain
   
   # For a simple setup without MPI:
   with h5py.File("my_world.hdf5", "r") as f:
       super_area_ids = f["geography"]["super_area_id"]
       # Map all super areas to domain 0
       super_area_ids_to_domain_dict = {int(id): 0 for id in super_area_ids}
           
   domain = Domain.from_hdf5(
       domain_id=0,
       super_areas_to_domain_dict=super_area_ids_to_domain_dict,
       hdf5_file_path="my_world.hdf5",
       interaction_config="config/interaction.yaml"
   )
   
   # Set up recording
   record = Record(record_path=results_folder, record_static_data=True)
   
   # Configure leisure activities
   leisure = generate_leisure_for_config(domain, "config/config.yaml")
   
   # Set up disease and infection parameters
   selector = InfectionSelector.from_disease_config(disease_config)
   selectors = InfectionSelectors([selector])
   
   # Seed initial infections
   infection_seed = InfectionSeed.from_uniform_cases(
       world=domain,
       infection_selector=selector,
       cases_per_capita=cpc,
       date=seeding_date,
       seed_past_infections=True,
   )
   infection_seeds = InfectionSeeds([infection_seed])
   
   # Create epidemiology module
   epidemiology = Epidemiology(
       infection_selectors=selectors,
       infection_seeds=infection_seeds
   )
   
   # Set up other simulation components
   interaction = Interaction.from_file()
   policies = Policies.from_file(disease_config=disease_config)
   events = Events.from_file()
   travel = Travel()
   
   # Create the simulator
   simulator = Simulator.from_file(
       world=domain,
       policies=policies,
       events=events,
       interaction=interaction,
       leisure=leisure,
       travel=travel,
       epidemiology=epidemiology,
       config_filename="config/config.yaml",
       record=record
   )
   ```

5. **Run the simulation**:
   ```python
   # Run the simulation
   simulator.run()
   ```

6. **Run your script**:
   ```bash
   python run_simulation.py
   ```

7. **Command-line Arguments**:
   The simulation script supports various command-line arguments to customise behaviour:
   
   ```bash
   python run_simulation.py --world_path my_world.hdf5 --save_path results
   ```
   
   Common arguments include:
   - `--world_path`: Path to the saved world HDF5 file
   - `--save_path`: Directory to save results
   - `--household_beta`: Transmission rate in households
   - `--n_seeding_days`: Number of days to seed infections
   - `--mask_wearing`: Enable mask wearing policies
   - `--vaccine`: Enable vaccination policies

### Using MPI for Large-Scale Simulations

For large simulations, JUNE supports MPI (Message Passing Interface) to run in parallel:

```bash
mpirun -n 4 python run_simulation.py --world_path my_world.hdf5
```

This distributes the simulation across 4 processes, which can significantly speed up large simulations.

### Simulation Results

After running a simulation, results are saved in the specified output directory (default: "results"):


### Common Issues with Simulations

- **Memory usage**: Simulations can require significant memory, especially for large worlds
- **Runtime**: Complex simulations can take hours or days to run
- **Convergence**: Results may vary depending on random seeding; consider running multiple simulations
- **MPI configuration**: When using MPI, ensure all processes can access the necessary files
- **Data output size**: Large simulations can generate gigabytes of data; plan storage accordingly

## Visualising Simulation Results

JUNE includes a basic visualisation tool for analysing simulation results located at `plot_maker/epidemic_visualiser.py`. This tool can generate various plots, maps, and animations showing the spread of disease over time.

### Using the Epidemic Visualiser

The visualiser can create:
- Time series graphs of infections, hospitalisations, ICU admissions, and deaths
- Demographic breakdowns by age and gender
- Geographic heatmaps at specific timepoints
- Animated maps showing disease spread over time
- Current status visualisations showing active infections/hospitalisations

Basic usage:

```python
from plot_maker.epidemic_visualiser import EpidemicVisualiser

# Initialize the visualiser
visualiser = EpidemicVisualiser(
    data_path="results/detailed_demographic_summary.csv",
    shapefile_path="data/input/geography/MSOA_2011_EW_BFC_V3.shp",
    current_status_path="results/current_status_by_msoa.csv"  # Optional
)

# Generate specific visualisations
visualiser.time_series_by_gender(metric="infections", output_path="infections_by_gender.png")
visualiser.heatmap_by_geography(metric="infections", output_path="infections_map.png")

# Or generate a complete set of visualisations
from plot_maker.epidemic_visualiser import generate_complete_report
generate_complete_report(
    data_path="results/detailed_demographic_summary.csv",
    shapefile_path="data/input/geography/MSOA_2011_EW_BFC_V3.shp", 
    output_folder="output_graphs/visualisations",
    current_status_path="results/current_status_by_msoa.csv"  # Optional
)
```

**Note**: Creating animated maps requires FFmpeg to be installed on your system (see the Rat Population Dynamics section for installation instructions).

### Running the Visualiser Directly

The easiest way to generate a complete set of visualisations from your simulation results is to run the script directly:

```bash
python plot_maker/epidemic_visualiser.py
```

This will automatically:
1. Look for data files in the default locations:
   - `results/detailed_demographic_summary.csv` (main demographics data)
   - `data/input/geography/MSOA_2011_EW_BFC_V3.shp` (shapefile for maps)
   - `results/current_status_by_msoa.csv` (current status data)
2. Generate all visualisations (time series, maps, animations, etc.)
3. Save the output to `output_graphs/visualisations/`

The script will create separate folders for different types of visualisations:
- `time_series/` - Line graphs showing progression over time
- `maps/` - Static geographical heatmaps
- `demographics/` - Age and gender breakdowns
- `animations_cumulative/` - Animated maps of cumulative cases
- `animations_current_status/` - Animated maps of active cases