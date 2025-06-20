import numpy as np
from time import perf_counter
from scipy.ndimage import gaussian_filter

# Helper function for compatibility with both old and new RatManager versions
def get_risk_grid(rat_manager):
    """Get risk grid from rat_manager, compatible with both old and new versions"""
    # Check if new structure with disease_model
    if hasattr(rat_manager, 'disease_model'):
        if hasattr(rat_manager.disease_model, '_risk_grid') and rat_manager.disease_model._risk_grid is not None:
            return rat_manager.disease_model._risk_grid
        try:
            return rat_manager.disease_model.build_risk_grid()
        except Exception as e:
            print(f"Error building risk grid from disease_model: {e}")
            return None
    
    # Check if old structure with direct _risk_grid attribute
    if hasattr(rat_manager, '_risk_grid') and rat_manager._risk_grid is not None:
        return rat_manager._risk_grid
    try:
        return rat_manager.build_risk_grid()
    except Exception as e:
        print(f"Error building risk grid directly: {e}")
        return None

def calculate_area_risk(rat_manager, area, risk_grid):
    """Calculate area risk in a version-compatible way"""
    if hasattr(rat_manager, 'area_mapper'):
        # New structure: use area_mapper
        return rat_manager.area_mapper.calculate_area_risk(area, risk_grid)
    else:
        # Old structure: direct method call
        return rat_manager.calculate_area_risk(area, risk_grid)

class ZoonoticTransmission:
    """
    Handles transmission of disease between rats and humans.
    Acts as an interface between the rat model and human epidemiology.
    """
    def __init__(self, rat_manager=None):
        """
        Initialize the zoonotic transmission handler.
        
        Parameters:
            rat_manager: The RatManager instance handling rat population and disease spread
        """
        self.rat_manager = rat_manager
        
    def process_rat_to_human_infections(self, world, timer, epidemiology, record=None, duration=None):
        """
        Direct approach for rat-to-human disease transmission using the risk grid.
        
        Uses the actual risk grid from the rat manager to determine infection probabilities
        in different areas, with precise coordinate transformations.
        
        Parameters:
            world: The JUNE world object containing geographical and population data
            timer: The simulation timer containing current time information
            epidemiology: The epidemiology module handling human infections
            record: Optional record object for tracking infections
            duration: Optional custom duration for this transmission step (in days)
            
        Returns:
            int: Number of human infections caused by rats
        """
        # Start timing
        start_time = perf_counter()
        
        print("\n==== Rat-to-Human Infection ====")
        
        # Use the class's rat_manager if not explicitly provided
        rat_manager = self.rat_manager
        
        # Early exit checks
        if rat_manager is None:
            print("No rat manager available")
            return 0
            
        # Get risk grid in a compatible way
        risk_grid = get_risk_grid(rat_manager)
        
        # Ensure risk grid was successfully built
        if risk_grid is None:
            print("No risk grid available after build attempt")
            return 0
            
        # Ensure we have infection selectors
        if not hasattr(epidemiology, 'infection_selectors') or not epidemiology.infection_selectors._infection_selectors:
            print("No infection selectors available")
            return 0
                
        # Get infection parameters
        infection_selector = epidemiology.infection_selectors._infection_selectors[0]
        infection_id = infection_selector.infection_id
        
        # Get rat-to-human transmission factor
        Beta = getattr(rat_manager, 'rat_to_human_factor', 0.001)
        T = duration if duration is not None else timer.duration
        
        print(f"Using parameters: Beta={Beta}, T={T}")
        
        # Print rat infection statistics
        if hasattr(rat_manager, 'states'):
            infected_rats = np.sum(rat_manager.states == 1)
            total_rats = rat_manager.num_rats if hasattr(rat_manager, 'num_rats') else 0
            infection_ratio = infected_rats / total_rats if total_rats > 0 else 0
            print(f"Infected rats: {infected_rats} of {total_rats} ({infection_ratio:.2%})")
        
        # Print risk grid stats
        non_zero_cells = np.sum(risk_grid > 0)
        max_risk = np.max(risk_grid)
        print(f"Risk grid stats: {risk_grid.shape}, {non_zero_cells} non-zero cells, max risk = {max_risk:.4f}")
        
        # Process human infections
        infections_caused = 0
        processed_areas = 0
        attempted_areas = 0
        
        # Process each area in the world
        for super_area in world.super_areas:
            for area in super_area.areas:
                attempted_areas += 1  # Count each area we attempt to process
                
                # Skip areas without people
                if not hasattr(area, 'people') or len(area.people) == 0:
                    continue
                
                # Calculate area risk using the polygon-based method
                area_risk = calculate_area_risk(rat_manager, area, risk_grid)
                
                # Skip areas with no risk
                if area_risk <= 0:
                    continue
                    
                processed_areas += 1  # Count areas with non-zero risk
                
                # Find susceptible people
                susceptible_people = []
                for person in area.people:
                    if not person.infected and not person.dead:
                        susceptible_people.append(person)
                
                if not susceptible_people:
                    continue
                
                # Calculate infection probability
                infection_prob = 1 - np.exp(-area_risk * Beta * T)
                
                # Process each susceptible person
                area_infections = 0
                for person in susceptible_people:
                    # Apply susceptibility modifier if available
                    susceptibility = person.immunity.get_susceptibility(infection_id) if hasattr(person, 'immunity') else 1.0
                    adjusted_prob = infection_prob * susceptibility
                    
                    # Determine if person gets infected
                    if np.random.random() < adjusted_prob:
                        epidemiology.infection_selectors.infect_person_at_time(
                            person=person,
                            time=timer.now,
                            infection_id=infection_id
                        )
                        area_infections += 1
                        
                        # Record if needed
                        if record:
                            region_name = (person.super_area.region.name 
                                        if hasattr(person, 'super_area') and person.super_area 
                                        else "unknown")
                            record.accumulate(
                                table_name="infections",
                                location_spec="rat_transmission",
                                region_name=region_name,
                                location_id=0,
                                infected_ids=[person.id],
                                infector_ids=[0],
                                infection_ids=[infection_id],
                            )
                infections_caused += area_infections
        
        # Log timing
        end_time = perf_counter()
        print(f"Attempted {attempted_areas} areas")
        print(f"Processed {processed_areas} areas with non-zero risk")
        print(f"Total infections caused by rats: {infections_caused}")
        print(f"Execution time: {end_time - start_time:.3f} seconds")
        
        return infections_caused
            
    def process_human_to_rat_infections(self, world, timer, epidemiology, record=None, duration=None):
        """
        Implements human-to-rat disease transmission using a human infection risk grid.
        
        Creates a risk grid based on infected humans and uses it to determine infection 
        probabilities for rats in different areas.
        
        Parameters:
            world: The JUNE world object containing geographical and population data
            timer: The simulation timer containing current time information
            epidemiology: The epidemiology module handling human infections
            record: Optional record object for tracking infections
            duration: Optional custom duration for this transmission step (in days)
            
        Returns:
            int: Number of rat infections caused by humans
        """
        # Start timing
        start_time = perf_counter()
        
        print("\n==== Human-to-Rat Infection ====")
        
        # Use the class's rat_manager if not explicitly provided
        rat_manager = self.rat_manager
        
        # Early exit checks
        if rat_manager is None:
            print("No rat manager available")
            return 0
        
        # Get the risk grid for shape reference
        risk_grid = get_risk_grid(rat_manager)
        if risk_grid is None:
            print("No risk grid available for reference")
            return 0
            
        # Parameters for human-to-rat transmission
        human_to_rat_factor = getattr(rat_manager, 'human_to_rat_factor', 0.001)
        T = duration if duration is not None else timer.duration
        
        print(f"Using parameters: human_to_rat_factor={human_to_rat_factor}, T={T}")
        
        # Create a human infection grid with the same dimensions as the rat grid
        human_infection_grid = np.zeros_like(risk_grid)
        
        # Track statistics
        infected_humans = 0
        processed_areas = 0
        attempted_areas = 0
        
        # Process each area to build the human infection grid
        for super_area in world.super_areas:
            for area in super_area.areas:
                attempted_areas += 1
                
                # Skip areas without people
                if not hasattr(area, 'people') or len(area.people) == 0:
                    continue
                
                # Count infected people in this area
                area_infected = sum(1 for person in area.people if person.infected)
                
                if area_infected == 0:
                    continue
                
                infected_humans += area_infected
                processed_areas += 1
                
                # Get the MSOA for this area
                area_name = getattr(area, 'name', None)
                
                # Check msoa mappings location based on RatManager version
                if hasattr(rat_manager, 'area_mapper'):
                    # New structure
                    area_to_msoa = rat_manager.area_mapper.area_to_msoa
                    msoa_to_cells = rat_manager.area_mapper.msoa_to_cells
                else:
                    # Old structure
                    area_to_msoa = getattr(rat_manager, 'area_to_msoa', {})
                    msoa_to_cells = getattr(rat_manager, 'msoa_to_cells', {})
                    
                if not area_name or area_name not in area_to_msoa:
                    continue
                
                msoa_id = area_to_msoa.get(area_name)
                
                # Get cells for this MSOA
                if msoa_id not in msoa_to_cells:
                    continue
                
                cells = msoa_to_cells.get(msoa_id, [])
                if not cells:
                    continue
                
                # Calculate risk based on infected people density
                # First get total people in area
                total_people = len(area.people)
                if total_people == 0:
                    continue
                
                # Calculate infected ratio
                infected_ratio = area_infected / total_people
                
                # Add risk to grid cells for this MSOA
                for row, col in cells:
                    if 0 <= row < human_infection_grid.shape[0] and 0 <= col < human_infection_grid.shape[1]:
                        human_infection_grid[row, col] += infected_ratio
        
        # Apply spatial smoothing to the grid
        smoothed_grid = gaussian_filter(human_infection_grid, sigma=2)
        
        # Process rat infections based on the human infection grid
        infections_caused = 0
        
        # Get susceptible rats
        if hasattr(rat_manager, 'states'):
            susceptible_indices = np.where(rat_manager.states == 0)[0]
        
            if len(susceptible_indices) > 0:
                for rat_idx in susceptible_indices:
                    # Get rat's cell location
                    if not hasattr(rat_manager, 'grid_indices') or rat_manager.grid_indices is None or rat_idx >= len(rat_manager.grid_indices):
                        continue
                        
                    row, col = rat_manager.grid_indices[rat_idx]
                    
                    # Check bounds
                    if not (0 <= row < smoothed_grid.shape[0] and 0 <= col < smoothed_grid.shape[1]):
                        continue
                        
                    # Get cell risk
                    cell_risk = smoothed_grid[row, col]
                    
                    # Skip if no risk
                    if cell_risk <= 0:
                        continue
                        
                    # Apply immunity if rat has any
                    rat_immunity = rat_manager.immunity[rat_idx] if hasattr(rat_manager, 'immunity') else 0
                    susceptibility = max(0, 1 - rat_immunity)
                    
                    # Calculate infection probability
                    infection_prob = 1 - np.exp(-cell_risk * human_to_rat_factor * T * susceptibility)
                    
                    # Determine if rat gets infected
                    if np.random.random() < infection_prob:
                        # Infect the rat
                        rat_manager.states[rat_idx] = 1  # Set to infected
                        rat_manager.infection_age[rat_idx] = 0.1  # Initial infection age
                        
                        infections_caused += 1
        
        # Log timing and statistics
        end_time = perf_counter()
        print(f"Attempted {attempted_areas} areas")
        print(f"Processed {processed_areas} areas with infected humans")
        print(f"Total infected humans considered: {infected_humans}")
        print(f"Total infections caused in rats: {infections_caused}")
        print(f"Execution time: {end_time - start_time:.3f} seconds")
        
        return infections_caused
