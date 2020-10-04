from june.world import World


class CampWorld(World):
    """
    This Class creates the world that will later be simulated.
    The world will be stored in pickle, but a better option needs to be found.
    
    Note: BoxMode = Demography +- Sociology - Geography
    """

    def __init__(self):
        """
        Initializes a world given a geography and a demography. For now, households are
        a special group because they require a mix of both groups (we need to fix
        this later). 
        """
        self.areas = None
        self.super_areas = None
        self.regions = None
        self.people = None
        self.households = None
        self.schools = None
        self.hospitals = None
        self.cemeteries = None
        self.box_mode = False
        self.pump_latrines = None
        self.distribution_centers = None
        self.communals = None
        self.female_communals = None
        self.religiouss = None
        self.shelters = None
        self.e_vouchers = None
        self.n_f_distribution_centers = None
