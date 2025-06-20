import os
import subprocess
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import contextily as ctx
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from pathlib import Path

from pyproj import Transformer
from scipy import ndimage
from sklearn.cluster import DBSCAN


from june import paths

class RatVisualisation:
    """
    Handles visualization of rat populations and disease spread.
    Works with a RatManager instance to create visualizations.
    """
    
    def __init__(self, rat_manager):
        """
        Initialize the visualization component.
        
        Parameters:
            rat_manager: Reference to the parent RatManager instance
        """
        self.rat_manager = rat_manager
        self.viz_output_dir = None
        self.viz_frame_count = 0
        self.sections = None
        self.geo_frame_count = 0
        self.geo_frame_paths = {}

    def visualise_comparison(self, shapefile_path=None, output_file=None, dpi=300, zoom_to_population=True):
        """
        Create a side-by-side visualisation comparing:
        1. MSOA boundaries and population data
        2. Generated rat density map
        
        Uses the existing population mapping from precompute_density_map method.
        
        Parameters:
            shapefile_path: Path to the MSOA shapefile. If None, uses default path.
            output_file: Path to save the figure. If None, displays on screen.
            dpi: Resolution for saved figure.
            zoom_to_population: Whether to automatically zoom to populated areas only.
            
        Returns:
            The path to the saved figure, or None if displayed on screen.
        """

        
        # Make sure we have a rat density map
        if not hasattr(self.rat_manager.density_calculator, 'rat_density') or self.rat_manager.density_calculator.rat_density is None:
            print("No rat density map available. Run precompute_density_map first.")
            return None
        
        print("Generating comparison visualisation...")
        
        try:
            # Set up the shapefile path
            if shapefile_path is None:
                shapefile_path = paths.data_path / "input/geography/MSOA_2011_EW_BFC_V3.shp"
            
            if not os.path.exists(shapefile_path):
                print(f"Shapefile not found at {shapefile_path}, cannot create comparison")
                return None
            
            # Load MSOA shapefile
            msoa_shapes = gpd.read_file(shapefile_path)
            print(f"Loaded {len(msoa_shapes)} MSOA shapes from shapefile")
            
            # Find populated areas to focus on
            if zoom_to_population:
                # Get indices where rat density is above a threshold
                threshold = max(0.1, np.percentile(self.rat_manager.density_calculator.rat_density[self.rat_manager.density_calculator.rat_density > 0], 5))
                populated = self.rat_manager.density_calculator.rat_density > threshold
                
                if np.any(populated):
                    # Find populated area bounds
                    rows, cols = np.where(populated)
                    min_row, max_row = np.min(rows), np.max(rows)
                    min_col, max_col = np.min(cols), np.max(cols)
                    
                    # Add a small buffer for context (10% of the size)
                    row_buffer = max(2, int((max_row - min_row) * 0.1))
                    col_buffer = max(2, int((max_col - min_col) * 0.1))
                    
                    min_row = max(0, min_row - row_buffer)
                    max_row = min(self.rat_manager.density_calculator.rat_density.shape[0] - 1, max_row + row_buffer)
                    min_col = max(0, min_col - col_buffer)
                    max_col = min(self.rat_manager.density_calculator.rat_density.shape[1] - 1, max_col + col_buffer)
                    
                    # Calculate map bounds for the populated area
                    x_scale = (self.rat_manager.density_calculator.maxx - self.rat_manager.density_calculator.minx) / self.rat_manager.density_calculator.rat_density.shape[1]
                    y_scale = (self.rat_manager.density_calculator.maxy - self.rat_manager.density_calculator.miny) / self.rat_manager.density_calculator.rat_density.shape[0]
                    
                    vis_minx = self.rat_manager.density_calculator.minx + min_col * x_scale
                    vis_maxx = self.rat_manager.density_calculator.minx + (max_col + 1) * x_scale
                    vis_miny = self.rat_manager.density_calculator.miny + min_row * y_scale
                    vis_maxy = self.rat_manager.density_calculator.miny + (max_row + 1) * y_scale
                    
                    print(f"Zooming to populated area: {vis_minx:.0f},{vis_miny:.0f} to {vis_maxx:.0f},{vis_maxy:.0f}")
                else:
                    # No populated areas found, use full extent
                    vis_minx, vis_miny, vis_maxx, vis_maxy = self.minx, self.miny, self.maxx, self.maxy
            else:
                # Use full extent
                vis_minx, vis_miny, vis_maxx, vis_maxy = self.rat_manager.density_calculator.minx, self.rat_manager.density_calculator.miny, self.rat_manager.density_calculator.maxx, self.rat_manager.density_calculator.maxy
                
            # Filter to MSOAs in our area of interest
            msoa_shapes_filtered = msoa_shapes.cx[vis_minx:vis_maxx, vis_miny:vis_maxy]
            print(f"Filtered to {len(msoa_shapes_filtered)} MSOA shapes in the visible area")
            
            # Map population data to MSOAs - reuse the mapping that was already done in precompute_density_map
            # We need to regenerate this mapping for visualisation
            msoa_shapes_filtered = msoa_shapes_filtered.copy()
            
            # Calculate area
            msoa_shapes_filtered['area_km2'] = msoa_shapes_filtered.geometry.area / 1e6
            
            # Use our existing population mapping to add population data to msoa_shapes_filtered
            # Extract the MSOA boundaries into a simple image for visualisation
            msoa_boundaries = msoa_shapes_filtered.boundary
            
            # Create a figure with two subplots side by side
            fig = plt.figure(figsize=(18, 8))
            gs = gridspec.GridSpec(1, 2, width_ratios=[1, 1])
            
            # Plot 1: Population density from rat_density before division by rat_ratio
            ax1 = plt.subplot(gs[0])
            
            # Create extent for the rat density map (in meters)
            extent = [self.rat_manager.density_calculator.minx, self.rat_manager.density_calculator.maxx, self.rat_manager.density_calculator.miny, self.rat_manager.density_calculator.maxy]
            
            # Recreate the human population density (rat density * rat_ratio)
            human_density = np.copy(self.rat_manager.density_calculator.rat_density) * self.rat_manager.density_calculator.rat_ratio
            
            # Only include areas with population in the population map
            pop_mask = human_density > 0
            masked_pop_density = np.copy(human_density)
            masked_pop_density[~pop_mask] = np.nan  # Set areas without population to NaN
            
            # Plot the population density heatmap
            vmin_pop = max(0.1, np.min(human_density[pop_mask])) if np.any(pop_mask) else 0.1
            vmax_pop = np.max(human_density)
            
            im1 = ax1.imshow(masked_pop_density, extent=extent, origin='lower', 
                        cmap='viridis', norm=LogNorm(vmin=vmin_pop, vmax=vmax_pop), alpha=0.7)
            
            # Add MSOA boundaries for context
            msoa_boundaries.plot(ax=ax1, color='gray', linewidth=0.2, alpha=0.3)
            
            # Add basemap
            try:
                ctx.add_basemap(ax1, crs="EPSG:27700", source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.4)
            except Exception as e:
                print(f"Could not add basemap to first plot: {e}")
                # Add grid for context
                ax1.grid(alpha=0.3, linestyle='--')
            
            ax1.set_title('Human Population Density (people/km²)', fontsize=14)
            ax1.set_xlabel('Easting (m)')
            ax1.set_ylabel('Northing (m)')
            
            # Set the axis limits to just the focus area
            ax1.set_xlim(vis_minx, vis_maxx)
            ax1.set_ylim(vis_miny, vis_maxy)
            
            # Add a colorbar
            cbar1 = plt.colorbar(im1, ax=ax1, pad=0.01)
            cbar1.set_label('People per km²')
            
            # Plot 2: Rat density map
            ax2 = plt.subplot(gs[1])
            
            # Only include areas with rats in the rat density map
            rat_mask = self.rat_manager.density_calculator.rat_density > 0
            masked_rat_density = np.copy(self.rat_manager.density_calculator.rat_density)
            masked_rat_density[~rat_mask] = np.nan  # Set areas without rats to NaN
            
            # Plot the rat density heatmap
            vmin_rat = max(0.1, np.min(self.rat_manager.density_calculator.rat_density[rat_mask])) if np.any(rat_mask) else 0.1
            vmax_rat = np.max(self.rat_manager.density_calculator.rat_density)
            
            im2 = ax2.imshow(masked_rat_density, extent=extent, origin='lower', 
                        cmap='YlOrRd', norm=LogNorm(vmin=vmin_rat, vmax=vmax_rat), alpha=0.7)
            
            # Add MSOA boundaries for context
            msoa_boundaries.plot(ax=ax2, color='gray', linewidth=0.2, alpha=0.3)
            
            # Add basemap
            try:
                ctx.add_basemap(ax2, crs="EPSG:27700", source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.5)
            except Exception as e:
                print(f"Could not add basemap to second plot: {e}")
                # Add grid for context
                ax2.grid(alpha=0.3, linestyle='--')
            
            ax2.set_title('Calculated Rat Density (rats/km²)', fontsize=14)
            ax2.set_xlabel('Easting (m)')
            
            # Set the axis limits to just the focus area
            ax2.set_xlim(vis_minx, vis_maxx)
            ax2.set_ylim(vis_miny, vis_maxy)
            
            # Add a colorbar
            cbar2 = plt.colorbar(im2, ax=ax2, pad=0.01)
            cbar2.set_label('Rats per km²')
            
            # Add summary info as text
            summary_text = (
                f"Total rat population: {self.rat_manager.num_rats:,}\n"
                f"Based on human population: {self.rat_manager.density_calculator.total_population:,}\n"
                f"Rat-to-human ratio: 1:{self.rat_manager.density_calculator.rat_ratio}\n"
                f"Max rat density: {vmax_rat:.1f} rats/km²\n"
                f"Max human density: {vmax_pop:.1f} people/km²\n"
                f"Cell size: {self.rat_manager.density_calculator.cell_size}m\n"
                f"Area: {vis_minx:.0f},{vis_miny:.0f} to {vis_maxx:.0f},{vis_maxy:.0f}"
            )
            
            # Add text box with summary
            props = dict(boxstyle='round', facecolor='white', alpha=0.7)
            ax2.text(0.02, 0.02, summary_text, transform=ax2.transAxes, fontsize=10,
                    verticalalignment='top', bbox=props)
            
            # Set overall title
            plt.suptitle('Comparison: Human Population Density vs. Calculated Rat Density', fontsize=16)
            
            # Set tight layout
            plt.tight_layout(rect=[0, 0, 1, 0.96])  # Make room for suptitle
            
            # Save or show the figure
            if output_file:
                # Ensure the output directory exists
                output_dir = os.path.dirname(output_file)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                    print(f"Created output directory: {output_dir}")
                    
                plt.savefig(output_file, dpi=dpi, bbox_inches='tight')
                print(f"Comparison visualisation saved to {output_file}")
                plt.close(fig)
                return output_file
            else:
                plt.show()
                return None
                
        except Exception as e:
            print(f"Error creating comparison visualisation: {e}")
            import traceback
            traceback.print_exc()
            return None
    

    def initialise_visualisation_tracker(self, output_dir="outputs"):
        """
        Initialise a tracker for creating section-specific visualisation frames.
        
        Parameters:
            output_dir: Base directory to save the individual frames
        """
        # Create output directory
        self.viz_output_dir = Path(output_dir)
        if not self.viz_output_dir.exists():
            self.viz_output_dir.mkdir(parents=True)
        
        # Initialise frame counter
        self.viz_frame_count = 0
        
        # Track paths to frames for each section
        self.viz_frame_paths = {}
        
        # Identify sections based on rat population distribution
        self.sections = self._identify_sections()
        
        # Create section-specific directories
        for section_id in self.sections:
            section_dir = self.viz_output_dir / f"section_{section_id}"
            if not section_dir.exists():
                section_dir.mkdir(parents=True)
            self.viz_frame_paths[section_id] = []
        
        print(f"Rat visualisation tracker initialised for {len(self.sections)} sections. Frames will be saved to {self.viz_output_dir}")

    def _identify_sections(self):
        """
        Identify distinct geographical sections based on rat population.
        
        This method divides the simulation area into natural regions based on 
        spatial distribution of rats.
        
        Returns:
            dict: section ID to bounding box mapping (section_id -> (min_row, min_col, max_row, max_col))
        """
        # First, identify areas with any rat population
        # Access rat_density from the parent rat_manager
        populated_areas = self.rat_manager.density_calculator.rat_density > 0
        
        # If no rats anywhere, return the whole area as one section
        if not np.any(populated_areas):
            return {0: (0, 0, self.rat_manager.density_calculator.sim_rows, self.rat_manager.density_calculator.sim_cols)}
        
        # Use DBSCAN clustering which naturally finds clusters without specifying a number
        try:
            # Get coordinates of cells with rats
            rows, cols = np.where(populated_areas)
            
            # Prepare data for clustering
            X = np.column_stack((rows, cols))
            
            # Calculate an appropriate epsilon (neighbourhood size) based on data
            # Larger grids need larger epsilon values
            grid_size = max(self.rat_manager.density_calculator.sim_rows, self.rat_manager.density_calculator.sim_cols)
            epsilon = max(3, grid_size // 30)  # Adaptive epsilon based on grid size
            
            # Use DBSCAN for clustering
            dbscan = DBSCAN(eps=epsilon, min_samples=5)
            cluster_labels = dbscan.fit_predict(X)
            
            # Count number of clusters (-1 is noise)
            num_clusters = len(set(cluster_labels)) - (1 if -1 in cluster_labels else 0)
            
            # If we found clusters, create sections
            if num_clusters > 0:
                sections = {}
                cluster_id = 0
                
                # Process each cluster including noise points (label -1)
                for label in set(cluster_labels):
                    mask = cluster_labels == label
                    if not np.any(mask):
                        continue
                        
                    cluster_rows = rows[mask]
                    cluster_cols = cols[mask]
                    
                    # Create bounding box
                    min_row = max(0, np.min(cluster_rows))
                    max_row = min(self.rat_manager.density_calculator.sim_rows - 1, np.max(cluster_rows))
                    min_col = max(0, np.min(cluster_cols))
                    max_col = min(self.rat_manager.density_calculator.sim_cols - 1, np.max(cluster_cols))
                    
                    # Only include if it has some size
                    if (max_row - min_row) > 0 and (max_col - min_col) > 0:
                        sections[cluster_id] = (min_row, min_col, max_row, max_col)
                        cluster_id += 1
                
                # If we found sections, return them
                if sections:
                    return sections
        except (ImportError, Exception) as e:
            print(f"DBSCAN clustering failed: {e}. Falling back to simpler approach.")
        
        # Fallback: Use connected components with median threshold
        
        # Use median density as threshold
        threshold = np.median(self.rat_manager.density_calculator.rat_density[populated_areas])
        high_density = self.rat_manager.density_calculator.rat_density > threshold
        
        # Label connected components
        labeled_array, num_sections = ndimage.label(high_density)
        
        # Create sections
        sections = {}
        for section_id in range(1, num_sections + 1):
            section_mask = labeled_array == section_id
            rows, cols = np.where(section_mask)
            
            if len(rows) == 0:
                continue
                
            # No padding
            min_row = max(0, np.min(rows))
            max_row = min(self.rat_manager.density_calculator.sim_rows - 1, np.max(rows))
            min_col = max(0, np.min(cols))
            max_col = min(self.rat_manager.density_calculator.sim_cols - 1, np.max(cols))
            
            sections[section_id-1] = (min_row, min_col, max_row, max_col)
        
        # If no valid sections were found, fall back to the whole area
        if not sections:
            return {0: (0, 0, self.rat_manager.density_calculator.sim_rows, self.rat_manager.density_calculator.sim_cols)}
        
        return sections
    
    def save_geo_sections_frame(self, date=None, shapefile_path=None, output_dir="outputs", dpi=100):
        """
        Save visualisation frames showing rat infection and immunity status with proper geographic context,
        using the identified sections for more focused views of relevant areas.
        
        Parameters:
            date: Current simulation date (for naming convention)
            shapefile_path: Path to the MSOA shapefile. If None, uses default path.
            output_dir: Directory to save the frames
            dpi: Resolution of the saved image
            
        Returns:
            Dict mapping section IDs to saved frame paths
        """

        
        # Create output directory
        output_path = Path(output_dir)
        if not output_path.exists():
            output_path.mkdir(parents=True)
        
        # Initialise frame counter and tracking if needed
        if not hasattr(self, 'geo_frame_count'):
            self.geo_frame_count = 0
            self.geo_frame_paths = {}
        
        # Increment frame counter
        self.geo_frame_count += 1
        
        # Identify sections to visualise (re-use existing method)
        if not hasattr(self, 'sections') or not self.sections:
            self.sections = self._identify_sections()
        
        # Generate frame paths for all sections for this timestamp
        frame_paths = {}
        for section_id in self.sections:
            # Create section directory if it doesn't exist
            section_dir = output_path / f"section_{section_id}"
            if not section_dir.exists():
                section_dir.mkdir(parents=True)
                
            # Initialise section tracking if needed
            if section_id not in self.geo_frame_paths:
                self.geo_frame_paths[section_id] = []
                
            # Generate filename with date or frame number
            if date:
                frame_name = f"day_{date.strftime('%Y-%m-%d')}.png"
            else:
                frame_name = f"frame_{self.geo_frame_count:04d}.png"
            
            frame_path = section_dir / frame_name
            frame_paths[section_id] = frame_path
        
        try:

            

            # Set up the shapefile path
            if shapefile_path is None:
                shapefile_path = paths.data_path / "input/geography/MSOA_2011_EW_BFC_V3.shp"
            
            if not os.path.exists(shapefile_path):
                print(f"Shapefile not found at {shapefile_path}, will create visualisation without boundaries")
                msoa_shapes = None
            else:
                # Load MSOA shapefile
                msoa_shapes = gpd.read_file(shapefile_path)
                transformer = Transformer.from_crs("EPSG:27700", "EPSG:4326")

            # Create grids for infected rats and immunity
            infected_grid = np.zeros((self.rat_manager.density_calculator.sim_rows, self.rat_manager.density_calculator.sim_cols))
            immunity_grid = np.zeros((self.rat_manager.density_calculator.sim_rows, self.rat_manager.density_calculator.sim_cols))
            
            if self.rat_manager.num_rats > 0 and self.rat_manager.grid_indices is not None:
                # Create infected rat grid
                infected_mask = self.rat_manager.states == 1
                infected_positions = self.rat_manager.grid_indices[infected_mask]
                for r, c in infected_positions:
                    if 0 <= r < self.rat_manager.density_calculator.sim_rows and 0 <= c < self.rat_manager.density_calculator.sim_cols:
                        infected_grid[r, c] += 1
                
                # Create immunity grid
                for i in range(self.rat_manager.num_rats):
                    r, c = self.rat_manager.grid_indices[i]
                    if 0 <= r < self.rat_manager.density_calculator.sim_rows and 0 <= c < self.rat_manager.density_calculator.sim_cols:
                        immunity_grid[r, c] += self.rat_manager.immunity[i]
                
                # Normalise immunity by rat count (avoid division by zero)
                rat_count_grid = np.zeros((self.rat_manager.density_calculator.sim_rows, self.rat_manager.density_calculator.sim_cols))
                for r, c in self.rat_manager.grid_indices:
                    if 0 <= r < self.rat_manager.density_calculator.sim_rows and 0 <= c < self.rat_manager.density_calculator.sim_cols:
                        rat_count_grid[r, c] += 1
                
                mask = rat_count_grid > 0
                immunity_grid[mask] = immunity_grid[mask] / rat_count_grid[mask]
            
            # Process each section
            for section_id, (min_row, min_col, max_row, max_col) in self.sections.items():
                # Convert grid coordinates to BNG coordinates (meters)
                min_x = self.rat_manager.density_calculator.minx + min_col * self.rat_manager.density_calculator.cell_size
                max_x = self.rat_manager.density_calculator.minx + (max_col+1) * self.rat_manager.density_calculator.cell_size
                min_y = self.rat_manager.density_calculator.miny + min_row * self.rat_manager.density_calculator.cell_size
                max_y = self.rat_manager.density_calculator.miny + (max_row+1) * self.rat_manager.density_calculator.cell_size
                
                # Optional: Add a small buffer to ensure we see enough context (in meters)
                buffer = 500  # meters
                min_x -= buffer
                max_x += buffer
                min_y -= buffer
                max_y += buffer
                
                # Print debug info about coordinates
                print(f"Section {section_id} BNG coordinates: min_x={min_x}, max_x={max_x}, min_y={min_y}, max_y={max_y}")
                
                # Transform BNG coordinates to WGS84 for filtering MSOA shapes
                wgs_min_x, wgs_min_y = transformer.transform(min_x, min_y)
                wgs_max_x, wgs_max_y = transformer.transform(max_x, max_y)
                
                print(f"Section {section_id} WGS84 coordinates: min_lon={wgs_min_x}, max_lon={wgs_max_x}, min_lat={wgs_min_y}, max_lat={wgs_max_y}")

                # Extract the section data
                section_infected = infected_grid[min_row:max_row+1, min_col:max_col+1]
                section_immunity = immunity_grid[min_row:max_row+1, min_col:max_col+1]
                section_rat_count = rat_count_grid[min_row:max_row+1, min_col:max_col+1] if 'rat_count_grid' in locals() else None
                
                # Skip if this section has no rats at all (unlikely but possible)
                if section_rat_count is not None and np.sum(section_rat_count) == 0:
                    continue
                
                # Create a figure with two subplots side by side
                fig, axs = plt.subplots(1, 2, figsize=(16, 8))
                fig.suptitle(f"Rat Disease - Section {section_id} - {date.strftime('%Y-%m-%d') if date else f'Day {self.geo_frame_count}'}", 
                            fontsize=16)
                
                # -- First subplot: Infected Rat Distribution --
                ax = axs[0]
                
                # Filter the MSOA shapes for just this section if available
                if msoa_shapes is not None:
                    section_msoa = msoa_shapes.cx[min_x:max_x, min_y:max_y]
                else:
                    section_msoa = None
                
                # Create extent for the section data - USING BNG COORDINATES
                section_extent = [min_x, max_x, min_y, max_y]
                
                # Create a custom colourmap for infection
                infected_cmap = LinearSegmentedColormap.from_list(
                    "infected_cmap", [(0, (1, 0, 0, 0)), (1, (1, 0, 0, 1))]
                )
                
                # Only show areas with infected rats
                masked_infected = np.ma.masked_where(section_infected == 0, section_infected)
                
                # Plot the infected rat distribution
                if np.max(section_infected) > 0:
                    vmin = max(0.1, np.min(section_infected[section_infected > 0]))
                    vmax = np.max(section_infected)
                    
                    im1 = ax.imshow(
                        masked_infected, 
                        extent=section_extent, 
                        origin='lower',
                        cmap=infected_cmap, 
                        interpolation='nearest',
                        norm=LogNorm(vmin=vmin, vmax=vmax)
                    )
                    
                    # Add a colourbar
                    cbar1 = plt.colorbar(im1, ax=ax)
                    cbar1.set_label('Infected Rats')
                
                # Add MSOA boundaries if available
                if section_msoa is not None and not section_msoa.empty:
                    section_msoa.boundary.plot(ax=ax, color='gray', linewidth=0.5, alpha=0.5)
                
                # Add basemap for context
                try:
                    ctx.add_basemap(
                        ax, 
                        crs="EPSG:27700",  # BNG coordinates
                        source=ctx.providers.OpenStreetMap.Mapnik, 
                        alpha=0.5,
                        zoom=10  # Set explicit zoom level
                    )
                except Exception as e:
                    print(f"Could not add basemap to first plot: {e}")
                    # Try alternative provider
                    try:
                        ctx.add_basemap(
                            ax, 
                            crs="EPSG:27700",  # BNG coordinates
                            source=ctx.providers.CartoDB.Positron,  # Alternative provider
                            alpha=0.5,
                            zoom=10
                        )
                    except Exception as e2:
                        print(f"Alternative basemap also failed: {e2}")
                        ax.grid(alpha=0.3, linestyle='--')
                
                ax.set_title('Infected Rat Distribution', fontsize=14)
                ax.set_xlabel('Easting (m)')  # BNG uses easting/northing
                ax.set_ylabel('Northing (m)')
                
                # Set axis limits using BNG coordinates to match the imshow extent
                ax.set_xlim(min_x, max_x)
                ax.set_ylim(min_y, max_y)
                
                # -- Second subplot: Immunity Levels --
                ax = axs[1]
                
                # Only show areas with rats
                if section_rat_count is not None:
                    masked_immunity = np.ma.masked_where(section_rat_count == 0, section_immunity)
                else:
                    masked_immunity = section_immunity
                
                # Plot the immunity levels
                im2 = ax.imshow(
                    masked_immunity, 
                    extent=section_extent, 
                    origin='lower',
                    cmap='viridis', 
                    vmin=0, 
                    vmax=1,
                    interpolation='nearest'
                )
                
                # Add a colobar
                cbar2 = plt.colorbar(im2, ax=ax)
                cbar2.set_label('Immunity Level')
                
                # Add MSOA boundaries if available
                if section_msoa is not None and not section_msoa.empty:
                    section_msoa.boundary.plot(ax=ax, color='gray', linewidth=0.5, alpha=0.5)
                
                # Add basemap for context
                try:
                    ctx.add_basemap(
                        ax, 
                        crs="EPSG:27700",  # BNG coordinates
                        source=ctx.providers.OpenStreetMap.Mapnik, 
                        alpha=0.5,
                        zoom=10  # Set explicit zoom level
                    )
                except Exception as e:
                    print(f"Could not add basemap to second plot: {e}")
                    # Try alternative provider
                    try:
                        ctx.add_basemap(
                            ax, 
                            crs="EPSG:27700",  # BNG coordinates
                            source=ctx.providers.CartoDB.Positron,  # Alternative provider
                            alpha=0.5,
                            zoom=10
                        )
                    except Exception as e2:
                        print(f"Alternative basemap also failed: {e2}")
                        ax.grid(alpha=0.3, linestyle='--')
                
                ax.set_title('Rat Immunity Levels', fontsize=14)
                ax.set_xlabel('Easting (m)')  # BNG uses easting/northing
                
                # Set axis limits using BNG coordinates to match the imshow extent
                ax.set_xlim(min_x, max_x)
                ax.set_ylim(min_y, max_y)
                
                # Add statistics as text
                if hasattr(self, 'infected_history') and self.infected_history:
                    # Calculate section-specific stats if possible
                    total_rats_in_section = np.sum(section_rat_count) if section_rat_count is not None else '?'
                    infected_in_section = np.sum(section_infected) if section_infected is not None else '?'
                    
                    # Calculate global stats
                    current_infected = self.infected_history[-1]
                    immunity_high = self.immunity_08_history[-1] if hasattr(self, 'immunity_08_history') and self.immunity_08_history else 0
                    
                    stats_text = (
                        f"Section {section_id} Stats:\n"
                        f"Rats in section: {int(total_rats_in_section) if isinstance(total_rats_in_section, (int, float)) else total_rats_in_section}\n"
                        f"Infected in section: {int(infected_in_section) if isinstance(infected_in_section, (int, float)) else infected_in_section}\n"
                        f"Global Stats:\n"
                        f"Total Rats: {self.rat_manager.num_rats}\n"
                        f"Total Infected: {current_infected} ({current_infected/self.rat_manager.num_rats*100:.1f}%)\n"
                        f"High Immunity: {immunity_high} ({immunity_high/self.rat_manager.num_rats*100:.1f}%)"
                    )
                    
                    # Add text box with statistics
                    props = dict(boxstyle='round', facecolor='white', alpha=0.7)
                    fig.text(0.01, 0.01, stats_text, fontsize=9, bbox=props)
                
                # Make sure dimensions are even for video encoding
                plt.tight_layout(rect=[0, 0.02, 1, 0.95])  # Make room for title and stats
                
                # Save the frame
                plt.savefig(frame_paths[section_id], dpi=dpi, bbox_inches='tight')
                print(f"Saved frame for section {section_id} to {frame_paths[section_id]}")
                plt.close(fig)
                
                # Store the path for future reference
                self.geo_frame_paths[section_id].append(str(frame_paths[section_id]))
            
            return frame_paths
            
        except Exception as e:
            print(f"Error creating geographic section visualisation frames: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def compile_geo_sections_animations(self, output_dir="outputs", fps=5, dpi=100):
        """
        Compile animations for each geographic section.
        
        Parameters:
            output_dir: Directory for the compiled animations
            fps: Frames per second in the animation
            dpi: Resolution of the animation
            
        Returns:
            dict: Mapping of section IDs to animation file paths
        """
        if not hasattr(self, 'geo_frame_paths'):
            print("No geographic frames found to compile. Run save_geo_sections_frame() first.")
            return {}
        
        # Create output directory
        output_path = Path(output_dir)
        if not output_path.exists():
            output_path.mkdir(parents=True)
        
        animation_paths = {}
        
        # Process each section
        for section_id, frame_paths in self.geo_frame_paths.items():
            if not frame_paths:
                print(f"No frames found for section {section_id}. Skipping.")
                continue
            
            print(f"Compiling animation for section {section_id} from {len(frame_paths)} frames...")
            animation_file = f"rat_geo_section_{section_id}.mp4"
            full_path = output_path / animation_file
            
            try:
                # Create a temporary file list
                list_file = output_path / f'geo_frames_section_{section_id}.txt'
                with open(list_file, 'w') as f:
                    for frame_path in frame_paths:
                        f.write(f"file '{os.path.abspath(frame_path)}'\n")
                
                # Run ffmpeg command
                cmd = [
                    'ffmpeg', '-y', '-r', str(fps), '-f', 'concat', 
                    '-safe', '0', '-i', str(list_file), 
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', 
                    '-vf', 'pad=width=ceil(iw/2)*2:height=ceil(ih/2)*2',  # Ensure even dimensions
                    str(full_path)
                ]
                
                print(f"Running command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
                
                # Clean up
                os.remove(list_file)
                
                animation_paths[section_id] = str(full_path)
                print(f"Animation for section {section_id} saved to {full_path}")
                
            except Exception as e:
                print(f"Error creating animation for section {section_id}: {e}")
                print(f"Command details: {getattr(e, 'stderr', '')}")
                
                # Try alternate method: Create GIF instead
                try:
                    print(f"Attempting to create GIF animation for section {section_id} instead...")
                    from PIL import Image
                    
                    gif_path = output_path / f"rat_geo_section_{section_id}.gif"
                    frames = [Image.open(frame_path) for frame_path in frame_paths]
                    
                    frames[0].save(
                        gif_path,
                        save_all=True,
                        append_images=frames[1:],
                        optimise=False,
                        duration=1000//fps,  # milliseconds between frames
                        loop=0  # 0 means loop indefinitely
                    )
                    
                    animation_paths[section_id] = str(gif_path)
                    print(f"GIF animation for section {section_id} saved to {gif_path}")
                    
                except Exception as gif_error:
                    print(f"Error creating GIF for section {section_id}: {gif_error}")
        
        return animation_paths