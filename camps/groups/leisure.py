from june.groups.leisure import Leisure
import yaml
from june.groups.leisure import (
    SocialVenueDistributor,
    PubDistributor,
    GroceryDistributor,
    CinemaDistributor,
    HouseholdVisitsDistributor,
    CareHomeVisitsDistributor,
)
from camps.groups import (
    PumpLatrineDistributor,
    FemaleCommunalDistributor,
    DistributionCenterDistributor,
    CommunalDistributor,
)


def generate_leisure_for_world(list_of_leisure_groups, world):
    """
    Generates an instance of the leisure class for the specified geography and leisure groups.

    Parameters
    ----------
    list_of_leisure_groups
        list of names of the lesire groups desired. Ex: ["pubs", "cinemas"]
    """
    leisure_distributors = []
    if "pubs" in list_of_leisure_groups:
        if not hasattr(world, "pubs"):
            raise ValueError("Your world does not have pubs.")
        leisure_distributors.append(PubDistributor.from_config(world.pubs))
    if "cinemas" in list_of_leisure_groups:
        if not hasattr(world, "cinemas"):
            raise ValueError("Your world does not have cinemas.")
        leisure_distributors.append(CinemaDistributor.from_config(world.cinemas))
    if "groceries" in list_of_leisure_groups:
        if not hasattr(world, "groceries"):
            raise ValueError("Your world does not have groceries.")
        leisure_distributors.append(GroceryDistributor.from_config(world.groceries))
    if "care_home_visits" in list_of_leisure_groups:
        if not hasattr(world, "care_homes"):
            raise ValueError("Your world does not have care homes.")
        leisure_distributors.append(
            CareHomeVisitsDistributor.from_config(world.super_areas)
        )
    if "pump_latrines" in list_of_leisure_groups:
        if not hasattr(world, "pump_latrines"):
            raise ValueError("Your world does note have pumps and latrines")
        leisure_distributors.append(
            PumpLatrineDistributor.from_config(world.pump_latrines)
        )
    if "distribution_centers" in list_of_leisure_groups:
        if not hasattr(world, "distribution_centers"):
            raise ValueError("Your world does note have distribution centers")
        leisure_distributors.append(
            DistributionCenterDistributor.from_config(world.distribution_centers)
        )
    if "communals" in list_of_leisure_groups:
        if not hasattr(world, "communals"):
            raise ValueError("Your world does note have communal spaces")
        leisure_distributors.append(CommunalDistributor.from_config(world.communals))
    if "female_communals" in list_of_leisure_groups:
        if not hasattr(world, "female_communals"):
            raise ValueError(
                "Your world does note have female friendly communal spaces"
            )
        leisure_distributors.append(
            FemaleCommunalDistributor.from_config(world.female_communals)
        )
    if "household_visits" in list_of_leisure_groups:
        if not hasattr(world, "households"):
            raise ValueError("Your world does not have households.")
        leisure_distributors.append(
            HouseholdVisitsDistributor.from_config(world.super_areas)
        )
    if "residence_visits" in list_of_leisure_groups:
        raise NotImplementedError

    return Leisure(leisure_distributors)

def generate_leisure_for_config(world, config_filename):
    """
    Generates an instance of the leisure class for the specified geography and leisure groups.
    Parameters
    ----------
    list_of_leisure_groups
        list of names of the lesire groups desired. Ex: ["pubs", "cinemas"]
    """
    with open(config_filename) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    list_of_leisure_groups = config['activity_to_super_groups']['leisure']
    leisure_instance = generate_leisure_for_world(list_of_leisure_groups, world)
    return leisure_instance
