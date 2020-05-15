import pytest

from june.geography import Geography
from june.demography import Demography
from june.world import World
from june.interaction import DefaultInteraction
from june.infection import Infection
from june.infection.symptoms import SymptomsConstant
from june.infection.transmission import TransmissionConstant
from june.groups import Hospitals, Schools, Companies, Households, CareHomes, Cemeteries
from june.simulator import Simulator


@pytest.fixture(name='sim',scope='module')
def create_simulator():

    geography = Geography.from_file({"msoa": ["E00088544", "E02002560", "E02002559"]})
    geography.hospitals = Hospitals.for_geography(geography)
    geography.cemeteries = Cemeteries()
    geography.carehomes = CareHomes.for_geography(geography)
    geography.schools = Schools.for_geography(geography)
    geography.companies = Companies.for_geography(geography)
    demography = Demography.for_geography(geography)
    world = World(geography, demography, include_households=True)

    symptoms = SymptomsConstant(recovery_rate=0.05)
    transmission = TransmissionConstant(probability=0.7)
    infection = Infection(transmission, symptoms)
    interaction = DefaultInteraction.from_file()
    return Simulator.from_file(
    world, interaction, infection, 
)

def test__clear_all_groups(sim): 

    #TODO: households and carehomes should be residences
    sim.clear_all_groups()
    for group_name in sim.activities_to_groups(sim.all_activities):
        grouptype = getattr(sim.world, group_name)
        for group in grouptype.members:
            for subgroup in group.subgroups:
                assert len(subgroup.people) == 0

def test__get_subgroup_active(sim):

    active_subgroup = sim.get_subgroup_active(['residence'], sim.world.people.members[0])
    assert active_subgroup.spec in ('carehome', 'household')

def test__move_people_to_active_subgroups(sim):

    sim.move_people_to_active_subgroups(['residence'])
    for person in sim.world.people.members:
        assert person in person.residence.people

