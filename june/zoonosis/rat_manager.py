"""
Rat Zoonosis Simulation Module

This module implements a computational model for simulating rat population
dynamics and disease spread, with particular focus on zoonotic transmission.
The code is structured into smaller component classes with a main RatManager
that orchestrates the simulation.
"""

import os
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter
from scipy.spatial import cKDTree
import geopandas as gpd
from pyproj import Transformer
from shapely.geometry import Point
from rtree import index
from rasterio.transform import Affine
from rasterio.features import rasterize

from june import paths
from june.zoonosis.rat_visualisation import RatVisualisation

class RatDensityCalculator:
    """
    Handles calculation and management of rat population density maps.
    
    This component is responsible for:
    1. Generating rat density maps based on human population
    2. Loading and saving precomputed density maps
    3. Converting human population to estimated rat populations
    """
    
    def __init__(self, parent_manager, world, rat_ratio, cell_size, gaussian_sigma, precomputed_density_path=None):
        """
        Initialize the density calculator.
        
        Parameters:
            parent_manager: Reference to the parent RatManager
            world: JUNE world object containing geographical and population data
            rat_ratio: Number of people per rat (e.g., 4 means 1 rat per 4 people)
            cell_size: size of each grid cell in metres
            gaussian_sigma: Sigma value for Gaussian smoothing of population density
            precomputed_density_path: Path to precomputed density map file
        """
        self.parent = parent_manager
        self.world = world
        self.rat_ratio = rat_ratio
        self.cell_size = cell_size
        self.gaussian_sigma = gaussian_sigma
        self.precomputed_density_path = precomputed_density_path or "rat_density_map.npy"
        
        # Properties to be initialized
        self.rat_density = None
        self.total_population = 0
        self.coordinate_system = None
        self.minx = self.miny = self.maxx = self.maxy = None
        self.sim_rows = self.sim_cols = None
        
    def delete_rat_density_map(self, file_path=None):
        """
        Delete the precomputed rat density map file to force regeneration.
        
        Parameters:
            file_path: Path to the rat density map file, uses instance default if None
        
        Returns:
            bool: True if file was deleted, False otherwise
        """
        if file_path is None:
            file_path = self.precomputed_density_path
            
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted {file_path} using os.remove")
                return True
        
            print(f"File {file_path} not found.")
            return False
            
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")
            return False
            
    def build_density_map(self):
        """
        Load or generate a rat density map for the simulation.
        
        This method either loads a precomputed density map from disk (if available)
        or generates a new one.
        
        Returns:
            numpy.ndarray: The rat density map for the simulation
        """
        if os.path.exists(self.precomputed_density_path):
            print(f"Loading precomputed rat density map from {self.precomputed_density_path}")
            self.rat_density = np.load(self.precomputed_density_path)
            self.sim_rows, self.sim_cols = self.rat_density.shape
            
            # Set bounds directly from shapefile - assume BNG coordinates
            try:
                shapefile_path = paths.data_path / "input/geography/MSOA_2011_EW_BFC_V3.shp"
                msoa_shapes = gpd.read_file(shapefile_path)
                self.minx, self.miny, self.maxx, self.maxy = msoa_shapes.total_bounds
                
                # Add 1km buffer
                buffer = 1000  # meters
                self.minx -= buffer
                self.miny -= buffer
                self.maxx += buffer
                self.maxy += buffer
                
                self.coordinate_system = 'BNG'
            except Exception:
                # If shapefile fails, use WGS84 from JUNE areas
                areas = self.world.areas.members
                coordinates = np.array([area.coordinates for area in areas if hasattr(area, 'coordinates') and area.coordinates is not None])
                self.miny, self.minx = np.min(coordinates, axis=0)
                self.maxy, self.maxx = np.max(coordinates, axis=0)
                
                # Add 0.01 degree buffer
                buffer = 0.01  # degrees
                self.minx -= buffer
                self.miny -= buffer
                self.maxx += buffer
                self.maxy += buffer
                
                self.coordinate_system = 'WGS84'
        else:
            print(f"No precomputed density map found. Generating...")
            
            # Use shapefile if available
            shapefile_path = paths.data_path / "input/geography/MSOA_2011_EW_BFC_V3.shp"
            try:
                if os.path.exists(shapefile_path):
                    self.rat_density = self.precompute_density_map(shapefile_path=shapefile_path)
                    self.coordinate_system = 'BNG'
            except Exception as e:
                print(f"Shapefile not found: {e}")
        
        # Calculate population and rats
        if not hasattr(self, 'total_population') or self.total_population == 0:
            self.total_population = sum(len(area.people) for area in self.world.areas.members if hasattr(area, 'people'))
        
        # Inform parent manager of the rat population
        if hasattr(self.parent, 'num_rats'):
            self.parent.num_rats = int(np.round(self.total_population / self.rat_ratio))
        
        # Return the density map
        if hasattr(self.parent, 'area_mapper') and self.parent.area_mapper is not None:
            # Create the cell mapping if we have MSOA data
            self.parent.area_mapper.create_msoa_cell_mapping()
        
        # Print summary
        print(f"Rat density map ready: {self.rat_density.shape}, {self.coordinate_system} coordinates")
        print(f"Total rat population: {self.parent.num_rats}, max density: {np.max(self.rat_density):.2f} rats/km²")
        
        return self.rat_density
        
    def precompute_density_map(self, output_file=None, shapefile_path=None):
        """
        Generate and save a rat density map based on human population distribution.
        
        This optimised method keeps the original population calculation but improves
        performance for the grid creation and spatial join steps.
        
        Parameters:
            output_file: Optional file path to save the density map. If None, uses the default path.
            shapefile_path: Path to the MSOA shapefile. If None, uses default path.
                
        Returns:
            numpy.ndarray: The computed rat density map
        """
        # Set output file path
        if output_file is None:
            output_file = self.precomputed_density_path
        
        # Set shapefile path
        if shapefile_path is None:
            shapefile_path = paths.data_path / "input/geography/MSOA_2011_EW_BFC_V3.shp"
        
        print(f"Precomputing rat density map using shapefile: {shapefile_path}")
        
        # Load MSOA shapefile - keeping the original projection (EPSG:27700)
        try:
            msoa_shapes = gpd.read_file(shapefile_path)
            print(f"Loaded shapefile with {len(msoa_shapes)} MSOA areas using {msoa_shapes.crs} coordinate system")
        except Exception as e:
            print(f"Error loading shapefile: {e}")
            raise ValueError(f"Could not load shapefile from {shapefile_path}")
        
        # Load the area data CSV with area information if available
        try:
            area_data_path = paths.data_path / "input/geography/area_size_km2.csv"
            area_df = pd.read_csv(area_data_path, encoding='latin1')
            
            # Create a dictionary mapping area codes to their area in km²
            area_sizes = {}
            for _, row in area_df.iterrows():
                area_code = row['OA11CD']
                area_size = row['AREAKM2']
                area_sizes[area_code] = area_size
            print(f"Loaded area size data for {len(area_sizes)} areas")
        except Exception as e:
            print(f"Could not load area size data: {e}")
            print("Will calculate areas directly from geometry")
            area_sizes = {}
        
        # Extract areas from JUNE world
        areas = self.world.areas.members
        print(f"Processing {len(areas)} areas from JUNE world")
        
        # Create mapping between MSOA codes and JUNE areas
        print("Mapping JUNE areas to MSOA shapes...")
        
        # Create a spatial index for faster lookups
        # Create a transformer from WGS84 to BNG
        transformer = Transformer.from_crs("EPSG:4326", msoa_shapes.crs, always_xy=True)
        
        # Build R-tree spatial index on the MSOA shapes
        idx = index.Index()
        for i, msoa in msoa_shapes.iterrows():
            idx.insert(i, msoa.geometry.bounds)
        
        # Map areas to MSOA shapes
        area_to_msoa = {}
        msoa_to_areas = {msoa_id: [] for msoa_id in msoa_shapes['MSOA11CD']}
        
        # Store the mappings in parent's area mapper if available
        if hasattr(self.parent, 'area_mapper') and self.parent.area_mapper is not None:
            self.parent.area_mapper.area_to_msoa = area_to_msoa
            self.parent.area_mapper.msoa_to_areas = msoa_to_areas
        
        for area in areas:
            if not hasattr(area, 'coordinates') or area.coordinates is None:
                continue
                
            lat, lon = area.coordinates
            # Transform WGS84 to BNG
            x, y = transformer.transform(lon, lat)
            point = Point(x, y)
            
            # Find which MSOA contains this point using spatial index
            possible_matches_idx = list(idx.intersection((x, y, x, y)))
            for i in possible_matches_idx:
                try:
                    if i < len(msoa_shapes) and point.within(msoa_shapes.iloc[i].geometry):
                        msoa_id = msoa_shapes.iloc[i]['MSOA11CD']
                        area_to_msoa[area.name] = msoa_id
                        msoa_to_areas[msoa_id].append(area)
                        break
                except Exception as e:
                    print(f"Error processing area with MSOA index {i}: {e}")
        
        mapped_areas = len(area_to_msoa)
        mapped_msoas = len([m for m, a in msoa_to_areas.items() if a])
        print(f"Successfully mapped {mapped_areas} areas to {mapped_msoas} MSOA regions")
        
        # Calculate population for each MSOA from mapped JUNE areas
        msoa_populations = {}
        total_population = 0
        areas_with_people = 0
        
        for msoa_id, areas_list in msoa_to_areas.items():
            if not areas_list:
                continue
                
            # Sum population from JUNE areas
            population = sum(len(area.people) for area in areas_list if hasattr(area, 'people'))
            
            if population > 0:
                msoa_populations[msoa_id] = population
                total_population += population
                areas_with_people += 1
        
        print(f"Calculated population for {areas_with_people} MSOAs, total population: {total_population}")
        
        # Add population data to MSOA shapes
        msoa_shapes['population'] = msoa_shapes['MSOA11CD'].map(
            lambda x: msoa_populations.get(x, 0)
        )
        
        # Calculate area and population density
        # Use pre-loaded area sizes if available, otherwise calculate from geometry
        msoa_shapes['area_km2'] = msoa_shapes['MSOA11CD'].map(
            lambda x: area_sizes.get(x, msoa_shapes.loc[msoa_shapes['MSOA11CD'] == x, 'geometry'].area.values[0] / 1000000 if len(msoa_shapes.loc[msoa_shapes['MSOA11CD'] == x]) > 0 else 1.0)
        )
        
        # Ensure no zero areas
        msoa_shapes['area_km2'] = msoa_shapes['area_km2'].replace(0, 1.0)
        
        # Calculate population density
        msoa_shapes['pop_density'] = msoa_shapes['population'] / msoa_shapes['area_km2']
        msoa_shapes['pop_density'] = msoa_shapes['pop_density'].fillna(0)
        
        # Get bounding box in the BNG coordinate system
        total_bounds = msoa_shapes.total_bounds  # minx, miny, maxx, maxy in meters
        self.minx, self.miny, self.maxx, self.maxy = total_bounds
        
        # Add buffer (in meters)
        buffer = 1000  # 1km buffer around the study area
        self.minx -= buffer
        self.miny -= buffer
        self.maxx += buffer
        self.maxy += buffer
        
        print(f"Study area bounds (meters): minx={self.minx}, miny={self.miny}, maxx={self.maxx}, maxy={self.maxy}")
        
        # Create grid coordinates using cell_size directly in meters
        x_coords = np.arange(self.minx, self.maxx, self.cell_size)
        y_coords = np.arange(self.miny, self.maxy, self.cell_size)
        self.sim_cols = len(x_coords)
        self.sim_rows = len(y_coords)
        
        print(f"Creating grid with {self.sim_rows} rows and {self.sim_cols} columns, cell size: {self.cell_size}m")
        
        # Use rasterio for direct rasterisation
        print("Using rasterisation for faster processing...")
        
        # We only need geometry and pop_density for rasterisation
        msoa_reduced = msoa_shapes[["geometry", "pop_density"]].copy()
        
        # Create transform for rasterisation (align grid cells with our coordinates)
        # Note: rasterio uses (origin_x, pixel_width, 0, origin_y, 0, pixel_height)
        transform = Affine.translation(self.minx, self.miny) * Affine.scale(self.cell_size, self.cell_size)
        
        # Rasterise the shapes to our grid
        features = [(geom, value) for geom, value in zip(msoa_reduced['geometry'], msoa_reduced['pop_density'])]
        
        print("Rasterising MSOA shapes to grid...")
        rasterised = rasterize(
            features,
            out_shape=(self.sim_rows, self.sim_cols),
            transform=transform,
            fill=0,
            all_touched=True,  # Include any cell that the shape touches
            dtype=float
        )
        
        # The rasterised output is in (row, col) format, but our grid is (col, row),
        # so we need to use it directly (no transpose needed)
        density_array = rasterised
        
        self.total_population = total_population
        
        # Apply Gaussian smoothing to create a more realistic distribution
        print("Applying Gaussian smoothing...")
        smoothed_population = gaussian_filter(density_array, sigma=self.gaussian_sigma)
        
        # Calculate total people represented in the smoothed distribution
        cell_area_km2 = (self.cell_size / 1000) ** 2  # Cell area in km²
        total_people_in_grid = np.sum(smoothed_population * cell_area_km2)
        
        # Scale factor to ensure we preserve the total population
        scale_factor = total_population / total_people_in_grid if total_people_in_grid > 0 else 1.0
        print(f"Scaling factor to preserve population: {scale_factor:.4f}")
        
        # Apply scaling to preserve total population
        smoothed_population *= scale_factor
        
        # Scale human density to rat density using rat_ratio
        rat_density = smoothed_population / self.rat_ratio
        
        # Print density statistics
        print(f"Rat density statistics:")
        print(f"  Min: {np.min(rat_density):.4f} rats/km²")
        print(f"  Max: {np.max(rat_density):.4f} rats/km²")
        print(f"  Mean: {np.mean(rat_density):.4f} rats/km²")
        print(f"  Median: {np.median(rat_density):.4f} rats/km²")
        print(f"  Total rats (estimated): {np.sum(rat_density * cell_area_km2):.0f}")
        
        # Save the precomputed density map
        print(f"Saving precomputed rat density map to {output_file}")
        np.save(output_file, rat_density)
        
        # Update instance variables
        self.rat_density = rat_density
        
        # Return the computed density
        return rat_density


class RatAreaMapper:
    """
    Maps between geographic areas and simulation grid cells.
    
    This component is responsible for:
    1. Mapping JUNE areas to MSOA regions
    2. Creating mappings between MSOAs and simulation grid cells
    3. Calculating area-specific infection risk
    """
    
    def __init__(self, parent_manager, world):
        """
        Initialize the area mapper.
        
        Parameters:
            parent_manager: Reference to the parent RatManager
            world: JUNE world object containing geographical and population data
        """
        self.parent = parent_manager
        self.world = world
        
        # Initialize mapping dictionaries
        self.area_to_msoa = {}
        self.msoa_to_areas = {}
        self.msoa_to_cells = {}
        self.msoa_shapes = None
        self.grid_transform = None
        
        # Cache for risk calculations
        self._msoa_risk_cache = {}
        self._area_risk_cache = {}
        self._risk_grid_reference = None
        self._msoa_mappings_initialised = False
        
    def initialise_msoa_mappings(self):
        """
        Initialise MSOA to area mappings needed for rat-to-human transmission.
        This creates the area_to_msoa and msoa_to_areas attributes if they don't exist.
        """
        print("Initialising MSOA mappings for area risk calculation...")
        try:
            # Load MSOA shapefile
            shapefile_path = paths.data_path / "input/geography/MSOA_2011_EW_BFC_V3.shp"
            if not os.path.exists(shapefile_path):
                print(f"MSOA shapefile not found at {shapefile_path}")
                self.area_to_msoa = {}
                self.msoa_to_areas = {}
                return
                
            msoa_shapes = gpd.read_file(shapefile_path)
            print(f"Loaded shapefile with {len(msoa_shapes)} MSOA areas")
            
            # Store MSOA shapes for later use
            self.msoa_shapes = msoa_shapes
            
            # Set grid bounds if not already set by density calculator
            if not hasattr(self.parent.density_calculator, 'minx') or not hasattr(self.parent.density_calculator, 'maxx'):
                # Set bounds from shapefile - assume BNG coordinates
                self.parent.density_calculator.minx, self.parent.density_calculator.miny, \
                self.parent.density_calculator.maxx, self.parent.density_calculator.maxy = msoa_shapes.total_bounds
                
                # Add 1km buffer
                buffer = 1000  # meters
                self.parent.density_calculator.minx -= buffer
                self.parent.density_calculator.miny -= buffer
                self.parent.density_calculator.maxx += buffer
                self.parent.density_calculator.maxy += buffer
                
                self.parent.density_calculator.coordinate_system = 'BNG'
                print(f"Set grid bounds from shapefile: {self.parent.density_calculator.minx},"
                      f"{self.parent.density_calculator.miny} to {self.parent.density_calculator.maxx},"
                      f"{self.parent.density_calculator.maxy}")
            
            # Set grid dimensions if not already set
            if not hasattr(self.parent.density_calculator, 'sim_rows') or not hasattr(self.parent.density_calculator, 'sim_cols'):
                # Calculate grid dimensions based on the bounds and cell size
                x_coords = np.arange(self.parent.density_calculator.minx, self.parent.density_calculator.maxx, self.parent.density_calculator.cell_size)
                y_coords = np.arange(self.parent.density_calculator.miny, self.parent.density_calculator.maxy, self.parent.density_calculator.cell_size)
                self.parent.density_calculator.sim_cols = len(x_coords)
                self.parent.density_calculator.sim_rows = len(y_coords)
                print(f"Set grid dimensions: {self.parent.density_calculator.sim_rows} rows, {self.parent.density_calculator.sim_cols} columns")
            
            # Create mapping dictionaries - only initialise what we need
            self.area_to_msoa = {}
            self.msoa_to_areas = {}  # We'll populate this as we go
            
            # Transform coordinates (JUNE uses WGS84, shapefile uses EPSG:27700)
            transformer = Transformer.from_crs("EPSG:4326", msoa_shapes.crs, always_xy=True)
            
            # Create R-tree spatial index for faster lookups
            idx = index.Index()
            for i, msoa in msoa_shapes.iterrows():
                idx.insert(i, msoa.geometry.bounds)
            
            # Map areas to MSOA shapes
            areas = self.world.areas.members
            mapped_areas = 0
            
            for area in areas:
                if not hasattr(area, 'coordinates') or area.coordinates is None:
                    continue
                    
                lat, lon = area.coordinates
                # Transform WGS84 to BNG
                x, y = transformer.transform(lon, lat)
                point = Point(x, y)
                
                # Find which MSOA contains this point using spatial index
                possible_matches_idx = list(idx.intersection((x, y, x, y)))
                for i in possible_matches_idx:
                    try:
                        if i < len(msoa_shapes) and point.within(msoa_shapes.iloc[i].geometry):
                            msoa_id = msoa_shapes.iloc[i]['MSOA11CD']
                            self.area_to_msoa[area.name] = msoa_id
                            
                            # Add area to msoa_to_areas dictionary, creating entry if needed
                            if msoa_id not in self.msoa_to_areas:
                                self.msoa_to_areas[msoa_id] = []
                            self.msoa_to_areas[msoa_id].append(area)
                            
                            mapped_areas += 1
                            break
                    except Exception as e:
                        print(f"Error processing area with MSOA index {i}: {e}")
            
            print(f"MSOA mappings initialised with {mapped_areas} mapped areas")
            
            # Process each super area in the world to initialise if needed
            try:
                # Check if Bath areas are missing from our mapping
                bath_areas = [area for area in self.world.areas.members 
                             if hasattr(area, 'name') and 'bath' in area.name.lower()]
                bath_mapped = [area for area in bath_areas 
                              if hasattr(area, 'name') and area.name in self.area_to_msoa]
                
                if bath_areas and len(bath_mapped) < len(bath_areas):
                    print(f"Warning: {len(bath_areas) - len(bath_mapped)} Bath areas not mapped!")
                    # Force initialisation of all Bath areas with any MSOA geometry they overlap with
                    bath_unmapped = [area for area in bath_areas if area.name not in self.area_to_msoa]
                    for area in bath_unmapped:
                        if not hasattr(area, 'coordinates') or area.coordinates is None:
                            continue
                        
                        lat, lon = area.coordinates
                        # Transform WGS84 to BNG
                        try:
                            x, y = transformer.transform(lon, lat)
                            point = Point(x, y)
                            
                            # Try to find any overlapping MSOA
                            for i, msoa in msoa_shapes.iterrows():
                                try:
                                    if point.within(msoa.geometry) or msoa.geometry.contains(point):
                                        msoa_id = msoa['MSOA11CD']
                                        print(f"Mapped Bath area {area.name} to MSOA {msoa_id}")
                                        self.area_to_msoa[area.name] = msoa_id
                                        
                                        # Add area to msoa_to_areas dictionary, creating entry if needed
                                        if msoa_id not in self.msoa_to_areas:
                                            self.msoa_to_areas[msoa_id] = []
                                        self.msoa_to_areas[msoa_id].append(area)
                                        mapped_areas += 1
                                        break
                                except Exception as e:
                                    print(f"Error checking Bath area with MSOA: {e}")
                        except Exception as e:
                            print(f"Error transforming Bath coordinates: {e}")
                
                # Now manually check if Bath is properly represented in the mappings
                bath_msoas = set()
                for area_name, msoa_id in self.area_to_msoa.items():
                    if 'bath' in area_name.lower():
                        bath_msoas.add(msoa_id)
                
                print(f"Bath areas mapped to {len(bath_msoas)} MSOAs: {', '.join(str(m) for m in bath_msoas)}")
                
            except Exception as e:
                print(f"Error in Bath area mapping check: {e}")
            
            # Create the cell mapping now that we have MSOA data
            self.create_msoa_cell_mapping()
            
            # Mark as initialized
            self._msoa_mappings_initialised = True
            
        except Exception as e:
            print(f"Error initialising MSOA mappings: {e}")
            import traceback
            traceback.print_exc()
            # Create empty dictionaries to prevent future errors
            self.area_to_msoa = {}
            self.msoa_to_areas = {}
            self._msoa_mappings_initialised = False
            
    def create_msoa_cell_mapping(self):
        """
        Create a mapping from MSOA IDs to grid cells that fall within them.
        This is crucial for calculating area-specific risk.
        """
        print("Creating MSOA to cell mapping...")
        
        # Initialise the mapping
        self.msoa_to_cells = {}
        
        # Get grid dimensions from density calculator
        if not hasattr(self.parent.density_calculator, 'sim_rows') or not hasattr(self.parent.density_calculator, 'sim_cols'):
            print("Warning: Grid dimensions not set. Cannot create MSOA-cell mapping.")
            return
            
        if not hasattr(self.parent.density_calculator, 'minx') or not hasattr(self.parent.density_calculator, 'miny'):
            print("Warning: Grid bounds not set. Cannot create MSOA-cell mapping.")
            return
            
        # Ensure we have MSOA shapes
        if not hasattr(self, 'msoa_shapes') or self.msoa_shapes is None:
            shapefile_path = paths.data_path / "input/geography/MSOA_2011_EW_BFC_V3.shp"
            try:
                self.msoa_shapes = gpd.read_file(shapefile_path)
                print(f"Loaded MSOA shapefile with {len(self.msoa_shapes)} areas")
            except Exception as e:
                print(f"Error loading MSOA shapefile: {e}")
                return
        
        # Create transform for rasterisation if not exists
        if not hasattr(self, 'grid_transform') or self.grid_transform is None:
            self.grid_transform = Affine.translation(
                self.parent.density_calculator.minx, 
                self.parent.density_calculator.miny
            ) * Affine.scale(
                self.parent.density_calculator.cell_size, 
                self.parent.density_calculator.cell_size
            )
        
        # Process only the MSOAs that have mapped areas
        cell_mapping_count = 0
        processed_msoas = 0
        total_msoas = len(self.msoa_shapes) if hasattr(self, 'msoa_shapes') else 0
        
        # Check if we have any areas mapped to MSOAs
        if not hasattr(self, 'msoa_to_areas') or not self.msoa_to_areas:
            print("No areas mapped to MSOAs. Cannot create cell mapping.")
            return
        
        print(f"Creating cell mappings for {len(self.msoa_to_areas)} MSOAs with mapped areas (out of {total_msoas} total)")
        
        # Process only the MSOAs that have mapped areas in our simulation
        for msoa_id, areas in self.msoa_to_areas.items():
            # Skip if no areas are mapped to this MSOA
            if not areas:
                continue
                
            # Find the corresponding MSOA shape
            msoa = None
            for m in self.msoa_shapes.itertuples():
                if m.MSOA11CD == msoa_id:
                    msoa = m
                    break
                    
            if msoa is None:
                print(f"Could not find shape for MSOA {msoa_id}")
                continue
                
            processed_msoas += 1
            
            # Use rasterisation to create a binary mask of cells in this MSOA
            features = [(msoa.geometry, 1)]
            try:
                # Try different dtype options to handle various shapefile formats
                try:
                    msoa_grid = rasterize(
                        features,
                        out_shape=(self.parent.density_calculator.sim_rows, self.parent.density_calculator.sim_cols),
                        transform=self.grid_transform,
                        fill=0,
                        all_touched=True,
                        dtype=bool
                    )
                except Exception as type_error:
                    # Try with float dtype instead
                    msoa_grid = rasterize(
                        features,
                        out_shape=(self.parent.density_calculator.sim_rows, self.parent.density_calculator.sim_cols),
                        transform=self.grid_transform,
                        fill=0,
                        all_touched=True,
                        dtype=float
                    )
                    # Convert to boolean
                    msoa_grid = msoa_grid > 0
                
                # Store the indices of cells that fall within this MSOA
                row_indices, col_indices = np.where(msoa_grid)
                self.msoa_to_cells[msoa_id] = list(zip(row_indices, col_indices))
                cell_mapping_count += len(self.msoa_to_cells[msoa_id])
            except Exception as e:
                print(f"Error rasterising MSOA {msoa_id}: {e}")
                continue
                
        print(f"Created cell mapping for {len(self.msoa_to_cells)} MSOAs with {cell_mapping_count} total cell mappings")
        print(f"Successfully processed {processed_msoas} out of {len(self.msoa_to_areas)} relevant MSOAs")
        
    def calculate_msoa_risk_vectorised(self, msoa_id, risk_grid):
        """
        Calculate risk for a single MSOA using vectorised operations.
        
        Parameters:
            msoa_id: MSOA identifier
            risk_grid: 2D array of rat infection risk values
            
        Returns:
            float: Population-weighted risk value for the MSOA
        """
        if not hasattr(self, 'msoa_to_cells') or msoa_id not in self.msoa_to_cells:
            return 0.0
            
        cells = self.msoa_to_cells.get(msoa_id, [])
        if not cells:
            return 0.0
            
        # Get human population density grid from parent's density calculator
        human_density = self.parent.density_calculator.rat_density * self.parent.density_calculator.rat_ratio
        
        # Convert cells list to NumPy arrays for vectorised operations
        cells_array = np.array(cells)
        if cells_array.size == 0:
            return 0.0
        
        cell_rows, cell_cols = cells_array.T
        
        # Filter to cells within grid bounds
        valid_mask = (
            (cell_rows >= 0) & (cell_rows < risk_grid.shape[0]) &
            (cell_cols >= 0) & (cell_cols < risk_grid.shape[1])
        )
        
        if not np.any(valid_mask):
            return 0.0
            
        # Get valid cells
        valid_rows = cell_rows[valid_mask]
        valid_cols = cell_cols[valid_mask]
        
        # Get population and risk values using array indexing (vectorised)
        cell_populations = human_density[valid_rows, valid_cols]
        cell_risks = risk_grid[valid_rows, valid_cols]
        
        # Calculate weighted risk using NumPy operations
        total_population = np.sum(cell_populations)
        
        if total_population > 0:
            weighted_risk_sum = np.sum(cell_populations * cell_risks)
            return weighted_risk_sum / total_population
        else:
            return 0.0
            
    def calculate_area_risk(self, area, risk_grid):
        """
        Calculate infection risk for an Area by finding its parent MSOA,
        then computing population-weighted average risk from all grid cells 
        that overlap with that MSOA.
        
        Optimised version with caching and vectorised operations.
        
        Parameters:
            area: A JUNE Area object
            risk_grid: 2D array of rat infection risk values
            
        Returns:
            float: Risk value for the area
        """
        # Initialise mappings only once
        if not self._msoa_mappings_initialised:
            if not hasattr(self, 'area_to_msoa') or not self.area_to_msoa:
                self.initialise_msoa_mappings()
            if not hasattr(self, 'msoa_to_cells') or not self.msoa_to_cells:
                self.create_msoa_cell_mapping()
            self._msoa_mappings_initialised = True
        
        # Get area name
        area_name = getattr(area, 'name', None)
        if not area_name:
            return 0.0
        
        # Check if risk grid has changed by comparing reference
        if self._risk_grid_reference is not risk_grid:
            # Clear caches when grid changes
            self._msoa_risk_cache = {}
            self._area_risk_cache = {}
            self._risk_grid_reference = risk_grid
        
        # Return cached area risk if available
        if area_name in self._area_risk_cache:
            return self._area_risk_cache[area_name]
        
        # Get MSOA ID
        if not hasattr(self, 'area_to_msoa') or area_name not in self.area_to_msoa:
            return 0.0
        
        msoa_id = self.area_to_msoa.get(area_name)
        
        # Return cached MSOA risk if available
        if msoa_id in self._msoa_risk_cache:
            risk = self._msoa_risk_cache[msoa_id]
            self._area_risk_cache[area_name] = risk
            return risk
        
        # Calculate risk for this MSOA using vectorised operations
        risk = self.calculate_msoa_risk_vectorised(msoa_id, risk_grid)
        
        # Cache the results
        self._msoa_risk_cache[msoa_id] = risk
        self._area_risk_cache[area_name] = risk
        
        return risk


class RatSpatialGrid:
    """
    Manages spatial data structures for efficient rat population simulation.
    
    This component is responsible for:
    1. Maintaining the spatial grid for fast neighbour lookups
    2. Handling rat movement and position updates
    3. Providing spatial queries for finding nearby rats
    """
    
    def __init__(self, parent_manager, cell_size, max_trans_distance, enable_movement=True, 
                 p_move=0.05, lambda_move=0.5, Rmax_move=5):
        """
        Initialize the spatial grid manager.
        
        Parameters:
            parent_manager: Reference to the parent RatManager
            cell_size: size of each grid cell in metres
            max_trans_distance: Maximum transmission distance in cells
            enable_movement: Whether rat movement is enabled
            p_move: Probability of movement per time step
            lambda_move: Movement decay factor
            Rmax_move: Maximum Manhattan movement distance in cells
        """
        self.parent = parent_manager
        self.cell_size = cell_size
        self.max_trans_distance = max_trans_distance
        
        # Movement parameters
        self.enable_movement = enable_movement
        self.p_move = p_move
        self.lambda_move = lambda_move
        self.Rmax_move = Rmax_move
        
        # Spatial grid attributes
        self.spatial_grid_array = None
        self.grid_cell_size = self.cell_size * max_trans_distance
        self.grid_cell_rows = None
        self.grid_cell_cols = None
        self._last_positions = None
        
        # Movement offset precomputation
        self.move_offsets = []
        self.move_offset_dists = []
        if self.enable_movement:
            self._precompute_movement_offsets()
            
    def _precompute_movement_offsets(self):
        """
        Creates an array of all possible movement directions and distances.
        
        This method builds an array of movement options up to the maximum movement range,
        which allows for consistent movement calculations during the simulation.
        """
        for di in range(-self.Rmax_move, self.Rmax_move + 1):
            for dj in range(-self.Rmax_move, self.Rmax_move + 1):
                if di == 0 and dj == 0:
                    continue
                d = abs(di) + abs(dj)
                if d <= self.Rmax_move:
                    self.move_offsets.append([di, dj])
                    self.move_offset_dists.append(d)
        
        self.move_offsets = np.array(self.move_offsets)
        self.move_offset_dists = np.array(self.move_offset_dists)
            
    def initialise_spatial_grid(self):
        """
        Initialise the spatial grid data structure for efficient neighbour lookups.
        
        This method creates an array-based spatial grid that partitions the simulation
        area into cells, allowing for fast identification of nearby rats during
        disease transmission calculations.
        """
        # Get grid dimensions from parent's density calculator
        minx = self.parent.density_calculator.minx
        miny = self.parent.density_calculator.miny
        maxx = self.parent.density_calculator.maxx
        maxy = self.parent.density_calculator.maxy
        
        # Determine grid dimensions based on the world bounds
        self.grid_cell_rows = int(np.ceil((maxy - miny) / self.grid_cell_size))
        self.grid_cell_cols = int(np.ceil((maxx - minx) / self.grid_cell_size))
        
        # Create empty grid (list of lists is faster than nested NumPy arrays for this use case)
        self.spatial_grid_array = [[[] for _ in range(self.grid_cell_cols)] for _ in range(self.grid_cell_rows)]
        
        # Pre-calculate positions to grid cell mapping for all rats
        if hasattr(self.parent, 'positions') and self.parent.positions is not None:
            cell_y = np.clip(((self.parent.positions[:, 1] - miny) / self.grid_cell_size).astype(int), 
                            0, self.grid_cell_rows - 1)
            cell_x = np.clip(((self.parent.positions[:, 0] - minx) / self.grid_cell_size).astype(int), 
                            0, self.grid_cell_cols - 1)
            
            # Add rats to the grid
            for idx in range(self.parent.num_rats):
                y, x = cell_y[idx], cell_x[idx]
                self.spatial_grid_array[y][x].append(idx)
    
    def update_spatial_grid(self):
        """
        Update the spatial grid to reflect current rat positions.
        
        This method rebuilds the spatial acceleration grid whenever rat positions
        change significantly. It uses an optimised array-based approach that avoids
        creating a new grid structure, instead clearing and repopulating the existing one.
        """
        # Track position changes to determine if update is necessary
        if not hasattr(self, '_last_positions') or self._last_positions is None:
            self._last_positions = self.parent.positions.copy() if self.parent.positions is not None else None
            self.initialise_spatial_grid()
            return
        
        # Skip update if no positions exist
        if self.parent.positions is None or self.parent.num_rats == 0:
            return
            
        # Check if enough rats have moved to justify a rebuild
        position_delta = np.abs(self.parent.positions - self._last_positions).max(axis=1)
        moved_count = np.sum(position_delta > self.cell_size/10)
        
        # Only rebuild if significant movement (>5% rats moved or first time)
        if moved_count > (self.parent.num_rats * 0.05):
            # Update last positions record
            self._last_positions = self.parent.positions.copy()
            
            # Initialise grid if not already done
            if self.spatial_grid_array is None:
                self.initialise_spatial_grid()
                return
            
            # Get bounds from parent
            minx = self.parent.density_calculator.minx
            miny = self.parent.density_calculator.miny
            
            # Use NumPy operations to find cell indices for all rats at once
            cell_y = np.clip(((self.parent.positions[:, 1] - miny) / self.grid_cell_size).astype(np.int32), 
                            0, self.grid_cell_rows - 1)
            cell_x = np.clip(((self.parent.positions[:, 0] - minx) / self.grid_cell_size).astype(np.int32), 
                            0, self.grid_cell_cols - 1)
            
            # Create a mapping of cells to rats first, to avoid repeated list operations
            cell_to_rats = {}
            for idx in range(self.parent.num_rats):
                key = (cell_y[idx], cell_x[idx])
                if key not in cell_to_rats:
                    cell_to_rats[key] = []
                cell_to_rats[key].append(idx)
                
            # Clear all cells
            for i in range(self.grid_cell_rows):
                for j in range(self.grid_cell_cols):
                    self.spatial_grid_array[i][j].clear()
            
            # Now populate the grid using the mapping
            for (y, x), rat_indices in cell_to_rats.items():
                # Extend is faster than repeated appends
                self.spatial_grid_array[y][x].extend(rat_indices)
                
    def move_rats(self):
        """
        Move rats according to movement parameters.
        
        Returns:
            int: Number of rats that moved
        """
        if not self.enable_movement or self.p_move <= 0:
            return 0
            
        # Determine which rats move (vectorised operation)
        move_flags = np.random.random(self.parent.num_rats) < self.p_move
        moving_idx = np.where(move_flags)[0]
        
        if moving_idx.size == 0:
            return 0
            
        # Pre-select random movement directions for all moving rats at once
        rand_directions = np.random.randint(0, len(self.move_offsets), size=moving_idx.size)
        
        # Get offsets for all moving rats
        offsets = self.move_offsets[rand_directions] * self.cell_size
        
        # Apply offsets to positions
        new_positions = self.parent.positions[moving_idx] + offsets
        
        # Get bounds from parent
        minx = self.parent.density_calculator.minx
        miny = self.parent.density_calculator.miny
        maxx = self.parent.density_calculator.maxx
        maxy = self.parent.density_calculator.maxy
        
        # Check if the positions are valid (vectorised)
        valid_mask = np.all((
            new_positions[:, 0] >= minx,
            new_positions[:, 0] < maxx,
            new_positions[:, 1] >= miny,
            new_positions[:, 1] < maxy
        ), axis=0)
        
        # Only update valid positions
        moved_rats_count = 0
        if np.any(valid_mask):
            self.parent.positions[moving_idx[valid_mask]] = new_positions[valid_mask]
            moved_rats_count = np.sum(valid_mask)
        
        # Update grid if enough rats moved
        if moved_rats_count > (self.parent.num_rats * 0.01):
            self.update_spatial_grid()
            
        return moved_rats_count


class RatDiseaseModel:
    """
    Manages disease transmission and progression among rats.
    
    This component is responsible for:
    1. Handling infection transmission between rats
    2. Updating disease states (infection, recovery, immunity)
    3. Building the infection risk grid for zoonotic transmission
    """
    
    def __init__(self, parent_manager, beta=0.3, alpha=0.1, gamma=0.15, 
                 delta_mean=0.05, delta_std=0.01, max_trans_distance=1,
                 p_global_seed=0.05, global_seed_range=(1, 4),
                 global_seed_immunity_threshold=0.5,
                 infectiousness_threshold=0.1):
        """
        Initialize the disease model.
        
        Parameters:
            parent_manager: Reference to the parent RatManager
            beta: Base transmission rate parameter
            alpha: Spatial seeding coefficient
            gamma: Recovery probability per time step
            delta_mean: Mean immunity decay rate
            delta_std: Standard deviation of immunity decay rate
            max_trans_distance: Maximum distance for disease transmission
            p_global_seed: Probability of random global seeding
            global_seed_range: (min, max) number of global seeds per step
            global_seed_immunity_threshold: Immunity threshold for global infections
            infectiousness_threshold: Minimum infectiousness to consider
        """
        self.parent = parent_manager
        self.beta = beta
        self.alpha = alpha
        self.gamma = gamma
        self.delta_mean = delta_mean
        self.delta_std = delta_std
        self.max_trans_distance = max_trans_distance
        self.p_global_seed = p_global_seed
        self.global_seed_min, self.global_seed_max = global_seed_range
        self.global_seed_immunity_threshold = global_seed_immunity_threshold
        self.infectiousness_threshold = infectiousness_threshold
        
        # Statistics tracking
        self.infected_history = []
        self.immunity_08_history = []
        self.immunity_05_history = []
        self.global_seeds_history = []
        self.total_global_seeds = 0
        
        # Transmission kernel
        self.transmission_kernel = None
        self._risk_grid = None
        
    def build_kernel(self):
        """
        Build a spatial interaction kernel for disease transmission calculations.
        
        This method creates a 2D kernel that models how infection probability
        decreases with distance. The kernel uses a power-law decay where
        probability halves for each unit increase in Manhattan distance.
        
        Returns:
            numpy.ndarray: The transmission kernel matrix
        """
        kernel_size = 2 * self.max_trans_distance + 1
        kernel = np.zeros((kernel_size, kernel_size))
        
        for di in range(-self.max_trans_distance, self.max_trans_distance + 1):
            for dj in range(-self.max_trans_distance, self.max_trans_distance + 1):
                d = abs(di) + abs(dj)
                if d <= self.max_trans_distance:
                    kernel[di + self.max_trans_distance, dj + self.max_trans_distance] = 0.5 ** d
        
        return kernel
        
    def infectiousness(self, age):
        """
        Calculates infectiousness of rats based on their infection age.
        
        This method implements a Gaussian-like infectiousness curve where:
        - Infectiousness peaks around day 7 of infection
        - Infectious period spans approximately 14 days
        - Rats below the infectiousness threshold are considered non-infectious
        
        Parameters:
            age: Array or scalar of infection ages in days
            
        Returns:
            numpy.ndarray: Calculated infectiousness values (0 to 1)
        """
        # Use vectorised operations for speed
        peak_infectiousness_day = 7.0
        infectious_period = 14.0
        
        # Simple mask for common cases to avoid expensive calculations
        zero_mask = age <= 0
        peak_mask = np.abs(age - peak_infectiousness_day) < 0.5  # Almost at peak
        
        # Return early for obvious cases
        if np.all(zero_mask):
            return np.zeros_like(age)
        
        # Precompute division for efficiency (avoid repeated divisions)
        scale = infectious_period/4
        
        # Calculate infectiousness using vectorised operations
        exponent = -0.5 * ((age - peak_infectiousness_day) / scale)**2
        infectiousness = np.exp(exponent)
        
        # Optimise for performance: set below threshold to zero directly
        infectiousness[infectiousness < self.infectiousness_threshold] = 0.0
        
        # Handle special cases for further optimisation
        infectiousness[zero_mask] = 0.0
        infectiousness[peak_mask] = 1.0  # Set to max at peak for efficiency
        
        return infectiousness
        
    def process_infection_transmission(self):
        """
        Calculates disease transmission between rats based on spatial proximity.
        
        This method:
        1. Identifies infectious rats with sufficient infectiousness
        2. Finds susceptible rats within transmission range
        3. Calculates infection probabilities based on distance and immunity
        4. Determines which susceptible rats become infected
        
        Returns:
            list: Indices of newly infected rats
        """
        # Pre-filter infected rats with significant infectiousness to reduce computation
        inf_ages = self.parent.infection_age[self.parent.states == 1]
        inf_idx_with_ages = np.where(self.parent.states == 1)[0]
        
        if len(inf_idx_with_ages) == 0:
            return []  # No infectious rats, early return
            
        # Vectorised calculation of infectiousness for all infected rats
        infectiousness_values = self.infectiousness(inf_ages)
        
        # Only consider rats with significant infectiousness (above threshold)
        valid_mask = infectiousness_values >= self.infectiousness_threshold
        
        if not np.any(valid_mask):
            return []  # No significantly infectious rats, early return
            
        inf_idx = inf_idx_with_ages[valid_mask]
        infectiousness_values = infectiousness_values[valid_mask]
        
        sus_idx = np.where(self.parent.states == 0)[0]
        
        if len(sus_idx) == 0:
            return []  # No susceptible rats, early return
        
        # Use a more efficient spatial search structure
        # Build KD-Tree for infectious rats (only once)
        inf_positions = self.parent.positions[inf_idx]
        tree_inf = cKDTree(inf_positions, leafsize=32)  # Larger leaf size for better performance
        
        # Get infection parameters for vectorised operations
        inf_max_dist = self.max_trans_distance * self.parent.spatial_grid.cell_size
        
        # Find all susceptible rats within infection distance of any infectious rat
        # This is much faster than checking each susceptible rat individually
        sus_positions = self.parent.positions[sus_idx]
        
        # Use optimised query_ball_tree to find all potential interactions
        # This returns indices of nearby points rather than computing all distances
        nearby_indices = tree_inf.query_ball_point(
            sus_positions, 
            r=inf_max_dist,
            return_sorted=False
        )
        
        # Initialise new infections list
        new_infections = []
        
        # Process each susceptible rat with potential infectious contacts
        for i, neighbours in enumerate(nearby_indices):
            if not neighbours:  # No nearby infectious rats
                continue
                
            sus_rat_idx = sus_idx[i]
            sus_position = sus_positions[i]
            sus_immunity = self.parent.immunity[sus_rat_idx]
            
            # If rat has high immunity, less likely to process it (optimisation)
            if sus_immunity > 0.8 and np.random.random() > 0.2:
                continue
                
            # Calculate total infection probability from all nearby infectious rats
            p_total = 0.0
            
            for j in neighbours:
                # Get infectious rat information
                inf_rat_idx = inf_idx[j]
                inf_position = inf_positions[j]
                inf_value = infectiousness_values[j]
                
                # Calculate Manhattan distance (faster than Euclidean)
                d = (abs(sus_position[0] - inf_position[0]) + 
                     abs(sus_position[1] - inf_position[1])) / self.parent.spatial_grid.cell_size
                
                if d <= self.max_trans_distance:
                    # Use precomputed value for common case
                    if d == 0:
                        distance_factor = 1.0
                    elif d == 1:
                        distance_factor = 0.5
                    elif d == 2:
                        distance_factor = 0.25
                    elif d == 3:
                        distance_factor = 0.125
                    else:
                        distance_factor = 0.5 ** d
                    
                    # Calculate infection probability
                    p_ij = self.beta * inf_value * distance_factor * (1 - sus_immunity)
                    p_total += p_ij
            
            # Apply cumulative probability (capped at 1.0)
            p_total = min(p_total, 0.99)  # Cap at 0.99 to avoid certainty
            
            # Determine if infection occurs (using faster random method)
            if np.random.random() < p_total:
                new_infections.append(sus_rat_idx)
        
        return new_infections
        
    def update_disease_states(self, duration=1.0):
        """
        Update disease states for all rats, including infection progression,
        recovery, and immunity changes.
        
        Parameters:
            duration: Duration of time step in days
            
        Returns:
            dict: Updated statistics about disease states
        """
        # Apply new infections (these are the infection indices generated from process_infection_transmission)
        # This is handled in the time_step method of the parent
        
        # Update infection age for infected rats
        inf_mask = self.parent.states == 1
        self.parent.infection_age[inf_mask] += duration
        
        # Determine which infected rats recover
        recover = (np.random.rand(self.parent.num_rats) < (self.gamma * duration)) & inf_mask
        self.parent.states[recover] = 2  # Recovered
        self.parent.immunity[recover] = 1.0
        self.parent.infection_age[recover] = 0
        
        # Update immunity decay for recovered rats
        rec_mask = self.parent.states == 2
        self.parent.immunity[rec_mask] *= np.exp(-self.parent.personal_delta[rec_mask] * duration)
        
        # Rats with low immunity become susceptible again
        self.parent.states[(rec_mask) & (self.parent.immunity < 0.1)] = 0
        
        # Process random global seeding
        global_seeds_this_step = 0
        if np.random.rand() < self.p_global_seed * duration:
            sus_idx = np.where((self.parent.states == 0) & (self.parent.immunity < self.global_seed_immunity_threshold))[0]
            
            if sus_idx.size > 0:
                num_seeds = np.random.randint(
                    self.global_seed_min, 
                    min(self.global_seed_max, sus_idx.size + 1)
                )
                chosen = np.random.choice(sus_idx, size=num_seeds, replace=False)
                
                self.parent.states[chosen] = 1
                self.parent.infection_age[chosen] = 0.1
                self.parent.immunity[chosen] = 0
                global_seeds_this_step += num_seeds
        
        # Update parent's grid indices
        # Convert positions to grid indices
        grid_cols = np.clip(((self.parent.positions[:, 0] - self.parent.density_calculator.minx) // 
                          self.parent.spatial_grid.cell_size).astype(int), 
                        0, self.parent.density_calculator.sim_cols - 1)
        grid_rows = np.clip(((self.parent.positions[:, 1] - self.parent.density_calculator.miny) // 
                          self.parent.spatial_grid.cell_size).astype(int), 
                        0, self.parent.density_calculator.sim_rows - 1)
        self.parent.grid_indices = np.column_stack((grid_rows, grid_cols))
        
        # Update statistics
        self.infected_history.append(np.sum(self.parent.states == 1))
        self.immunity_08_history.append(np.sum(self.parent.immunity > 0.8))
        self.immunity_05_history.append(np.sum(self.parent.immunity > 0.5))
        self.global_seeds_history.append(global_seeds_this_step)
        self.total_global_seeds += global_seeds_this_step
        
        return {
            'infected': self.infected_history[-1],
            'immunity_08': self.immunity_08_history[-1],
            'immunity_05': self.immunity_05_history[-1],
            'global_seeds': global_seeds_this_step
        }
    
    def build_risk_grid(self):
        """
        Creates a grid representing infection risk across the simulation area.
        
        Returns:
            numpy.ndarray: The risk grid for the current time step
        """
        print("\n==== Building Risk Grid ====")
        
        try:
            # Check if we have required attributes
            if not hasattr(self.parent.density_calculator, 'sim_rows') or not hasattr(self.parent.density_calculator, 'sim_cols'):
                print("Warning: Grid dimensions not set. Initialising with defaults.")
                # Use default grid size
                self.parent.density_calculator.sim_rows = self.parent.density_calculator.sim_cols = 100
                
            # Skip calculation if no rats or no infected rats
            if not hasattr(self.parent, 'num_rats') or self.parent.num_rats == 0:
                print("No rats in simulation, creating empty risk grid")
                self._risk_grid = np.zeros((self.parent.density_calculator.sim_rows, self.parent.density_calculator.sim_cols))
                return self._risk_grid
                
            if not hasattr(self.parent, 'states'):
                print("No rat states found, creating empty risk grid")
                self._risk_grid = np.zeros((self.parent.density_calculator.sim_rows, self.parent.density_calculator.sim_cols))
                return self._risk_grid
                
            infected_count = np.sum(self.parent.states == 1)
            if infected_count == 0:
                print("No infected rats, creating empty risk grid")
                self._risk_grid = np.zeros((self.parent.density_calculator.sim_rows, self.parent.density_calculator.sim_cols))
                return self._risk_grid
                
            print(f"Building risk grid with {infected_count} infected rats out of {self.parent.num_rats}")
            
            # Ensure we have rat density
            if not hasattr(self.parent.density_calculator, 'rat_density'):
                print("No rat density found, assuming uniform density")
                self.parent.density_calculator.rat_density = np.ones((self.parent.density_calculator.sim_rows, self.parent.density_calculator.sim_cols))
            
            # Make sure grid indices are calculated
            if not hasattr(self.parent, 'grid_indices') or self.parent.grid_indices is None:
                if not hasattr(self.parent, 'positions'):
                    print("No rat positions found, cannot calculate grid indices")
                    self._risk_grid = np.zeros((self.parent.density_calculator.sim_rows, self.parent.density_calculator.sim_cols))
                    return self._risk_grid
                    
                # Calculate grid indices if not already done
                grid_cols = np.clip(((self.parent.positions[:, 0] - self.parent.density_calculator.minx) // 
                                  self.parent.spatial_grid.cell_size).astype(int), 
                                0, self.parent.density_calculator.sim_cols - 1)
                grid_rows = np.clip(((self.parent.positions[:, 1] - self.parent.density_calculator.miny) // 
                                  self.parent.spatial_grid.cell_size).astype(int), 
                                0, self.parent.density_calculator.sim_rows - 1)
                self.parent.grid_indices = np.column_stack((grid_rows, grid_cols))
            
            # Create grid of infected rats
            infected_grid = np.zeros((self.parent.density_calculator.sim_rows, self.parent.density_calculator.sim_cols))
            
            # Ensure we have a transmission kernel
            if self.transmission_kernel is None:
                print("No transmission kernel found, building default kernel")
                self.transmission_kernel = self.build_kernel()
            
            # Get infectious rat positions with significant infectiousness
            if not hasattr(self.parent, 'infection_age'):
                print("No infection ages found, using state only")
                inf_mask = (self.parent.states == 1)
            else:
                # Use infectiousness function if available
                inf_mask = (self.parent.states == 1) & (self.infectiousness(self.parent.infection_age) >= self.infectiousness_threshold)
                
            inf_positions = self.parent.grid_indices[inf_mask]
            
            # Build infected rat grid
            if len(inf_positions) > 0:
                for r, c in inf_positions:
                    if 0 <= r < self.parent.density_calculator.sim_rows and 0 <= c < self.parent.density_calculator.sim_cols:
                        infected_grid[r, c] += 1
            
            # Apply spatial kernel using convolution
            from scipy.signal import convolve2d
            risk_grid = convolve2d(infected_grid, self.transmission_kernel, mode='same')
            
            # Apply rat density factor - only areas with sufficient rat density have risk
            rat_density_threshold = 1.0  # Default threshold
            rat_density_mask = self.parent.density_calculator.rat_density > rat_density_threshold
            risk_grid = risk_grid * rat_density_mask
            
            # After creating risk grid
            non_zero = np.sum(risk_grid > 0)
            print(f"Created risk grid with {non_zero} non-zero cells ({100*non_zero/risk_grid.size:.2f}%)")
            print(f"Max risk value: {np.max(risk_grid)}")
            
            # Store for this timestep
            self._risk_grid = risk_grid
            
            # Clear caches in area mapper if available
            if hasattr(self.parent, 'area_mapper') and self.parent.area_mapper is not None:
                self.parent.area_mapper._risk_grid_reference = risk_grid
                self.parent.area_mapper._msoa_risk_cache = {}
                self.parent.area_mapper._area_risk_cache = {}
            
            return risk_grid
            
        except Exception as e:
            print(f"Error building risk grid: {e}")
            import traceback
            traceback.print_exc()
            # Return empty grid in case of errors
            self._risk_grid = np.zeros((self.parent.density_calculator.sim_rows, self.parent.density_calculator.sim_cols))
            return self._risk_grid


class RatManager:
    """
    Orchestrates rat population dynamics and disease spread simulation.
    
    This class serves as the main interface for the rat simulation, coordinating
    the activities of specialized component classes for different aspects of the simulation.
    """
    
    def __init__(
        self,
        world,  # JUNE world
        rat_ratio: int = 9,  # 1 rat per 4 people
        cell_size: float = 200,  # cell size in metres
        gaussian_sigma: float = 2,
        initial_infections: int = 90,
        beta: float = 0.3,  # transmission rate
        alpha: float = 0.1,  # spatial seeding coefficient
        dt: float = 1.0,  # time step (days)
        gamma: float = 0.15,  # recovery probability per time step
        delta_mean: float = 0.05,  # mean immunity decay rate
        delta_std: float = 0.01,  # std of immunity decay rate
        max_trans_distance: int = 1,  # transmission distance (in cells)
        p_global_seed: float = 0.05,  # probability for random global seeding per step
        global_seed_range: tuple = (1, 4),  # (min, max) number of global seeds per step
        global_seed_immunity_threshold: float = 0.5,  # only globally infect if immunity below threshold
        enable_movement: bool = True,  # option to completely disable movement
        p_move: float = 0.05,  # probability a rat moves per step (if movement enabled)
        lambda_move: float = 0.5,  # movement decay factor for candidate weighting
        Rmax_move: int = 5,  # maximum Manhattan movement distance (in cells)
        precomputed_density_path: str = "rat_density_map.npy",  # path to precomputed density
        infectiousness_threshold: float = 0.1,  # minimum infectiousness to consider
        rat_to_human_factor = 0.001,
        human_to_rat_factor = 0.001
    ):
        """
        Initialise the RatManager with simulation parameters.
        """
        # Store core parameters
        self.world = world
        self.num_rats = 0
        self.dt = dt
        self.rat_to_human_factor = rat_to_human_factor
        self.human_to_rat_factor = human_to_rat_factor
        self.initial_infections = initial_infections
        
        # Create component instances
        self.density_calculator = RatDensityCalculator(
            parent_manager=self,
            world=world,
            rat_ratio=rat_ratio,
            cell_size=cell_size,
            gaussian_sigma=gaussian_sigma,
            precomputed_density_path=precomputed_density_path
        )
        
        self.spatial_grid = RatSpatialGrid(
            parent_manager=self,
            cell_size=cell_size,
            max_trans_distance=max_trans_distance,
            enable_movement=enable_movement,
            p_move=p_move,
            lambda_move=lambda_move,
            Rmax_move=Rmax_move
        )
        
        self.disease_model = RatDiseaseModel(
            parent_manager=self,
            beta=beta,
            alpha=alpha,
            gamma=gamma,
            delta_mean=delta_mean,
            delta_std=delta_std,
            max_trans_distance=max_trans_distance,
            p_global_seed=p_global_seed,
            global_seed_range=global_seed_range,
            global_seed_immunity_threshold=global_seed_immunity_threshold,
            infectiousness_threshold=infectiousness_threshold
        )
        
        self.area_mapper = RatAreaMapper(
            parent_manager=self,
            world=world
        )

        self.rat_visualisation = RatVisualisation(
            rat_manager=self,
        )
        
        # Internal state (using arrays for efficiency)
        self.rat_density = None  # 2D grid of rat density
        self.positions = None  # Array of rat positions (x, y)
        self.states = None  # Array of rat states
        self.infection_age = None  # Array of infection ages
        self.immunity = None  # Array of immunity values
        self.personal_delta = None  # Array of personal immunity decay rates
        self.grid_indices = None  # Array of grid indices for each rat
        
        # Grid parameters from density calculator
        self.minx = self.miny = self.maxx = self.maxy = None
        self.sim_rows = self.sim_cols = None
        
        # Initialize the simulation
        self._initialise_simulation()
        
    def _initialise_simulation(self):
        """
        Initialize the rat population and disease states for the simulation.
        """
        # Build the density map
        self.rat_density = self.density_calculator.build_density_map()
        
        # Transfer grid dimensions from density calculator
        self.minx = self.density_calculator.minx
        self.miny = self.density_calculator.miny
        self.maxx = self.density_calculator.maxx
        self.maxy = self.density_calculator.maxy
        self.sim_rows = self.density_calculator.sim_rows
        self.sim_cols = self.density_calculator.sim_cols
        
        # Initialize MSOA mappings for area risk calculation
        self.area_mapper.initialise_msoa_mappings()
        
        if self.num_rats == 0:
            print("Warning: No rats in simulation. Check population data and rat_ratio")
            return
            
        print(f"Total rats in simulation: {self.num_rats}")
        
        # Create positions for rats based on density
        p = self.rat_density.flatten() / np.sum(self.rat_density)
        indices = np.random.choice(np.arange(self.sim_rows * self.sim_cols), size=self.num_rats, p=p)
        rows = indices // self.sim_cols
        cols = indices % self.sim_cols
        
        # Convert grid indices to metric coordinates - using direct cell size in meters
        self.positions = np.column_stack((
            self.minx + cols * self.spatial_grid.cell_size,  # Already in meters
            self.miny + rows * self.spatial_grid.cell_size   # Already in meters
        ))
        
        # Initialize disease states
        self.states = np.zeros(self.num_rats, dtype=int)
        self.infection_age = np.zeros(self.num_rats)
        self.immunity = np.zeros(self.num_rats)
        
        # Seed initial infections (cap by number of rats)
        initial_infections = min(self.initial_infections, self.num_rats)
        if initial_infections > 0:
            initial_infected = np.random.choice(self.num_rats, size=initial_infections, replace=False)
            self.states[initial_infected] = 1
            self.infection_age[initial_infected] = 0.1
        
        # Assign personal immunity decay rates
        self.personal_delta = np.random.normal(
            self.disease_model.delta_mean, 
            self.disease_model.delta_std, 
            self.num_rats
        )
        self.personal_delta = np.clip(self.personal_delta, 0.001, None)
        
        print(f"Initialized {self.num_rats} rats with {initial_infections} initial infections")
        
        # Initialize spatial grid for efficient neighbor lookups
        self.spatial_grid.initialise_spatial_grid()
        
        # Initialize transmission kernel
        self.disease_model.transmission_kernel = self.disease_model.build_kernel()
    
    def time_step(self, duration=None):
        """
        Advances the rat population and disease simulation by one time step.
        
        Parameters:
            duration: Optional custom time step duration (in days). If None, uses default dt.
            
        Returns:
            dict: Simulation statistics for the current step
        """
        if self.num_rats == 0:
            # No rats, nothing to do
            empty_grid = np.zeros((self.sim_rows, self.sim_cols))
            return {
                'infected': 0,
                'immunity_08': 0,
                'immunity_05': 0,
                'global_seeds': 0,
                'risk_grid': empty_grid
            }
        
        # Use provided duration or default
        dt = duration if duration is not None else self.dt
        
        # Move rats (if enabled)
        moved_rats_count = self.spatial_grid.move_rats()
        
        # Process disease transmission
        new_infections = self.disease_model.process_infection_transmission()
        
        # Update disease states for newly infected rats
        if new_infections:
            self.states[new_infections] = 1
            self.infection_age[new_infections] = 0.1
            self.immunity[new_infections] = 0
        
        # Update disease states (infection progression, recovery, immunity)
        state_updates = self.disease_model.update_disease_states(dt)
        
        # Build risk grid for human transmission
        risk_grid = self.disease_model.build_risk_grid()
        
        # Return statistics including the risk grid
        return {
            'infected': state_updates['infected'],
            'immunity_08': state_updates['immunity_08'],
            'immunity_05': state_updates['immunity_05'],
            'global_seeds': state_updates['global_seeds'],
            'risk_grid': risk_grid
        }
    
    def calculate_area_risk(self, area, risk_grid):
        """
        Calculate infection risk for an Area.
        Delegates to area_mapper component.
        
        Parameters:
            area: A JUNE Area object
            risk_grid: 2D array of rat infection risk values
            
        Returns:
            float: Risk value for the area
        """
        return self.area_mapper.calculate_area_risk(area, risk_grid)
