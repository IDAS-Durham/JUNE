import numpy as np
from time import perf_counter
from time import time as wall_clock
import logging

from .infection import InfectionSelectors, ImmunitySetter
from june.demography import Population, Activities
from june.policy import MedicalCarePolicies
from june.mpi_setup import mpi_comm, mpi_size, mpi_rank, move_info
from june.groups import MedicalFacilities
from june.records import Record
from june.world import World
from june.time import Timer

logger = logging.getLogger("epidemiology")
mpi_logger = logging.getLogger("mpi")

if mpi_rank > 0:
    logger.propagate = False


def _get_medical_facilities(world, activity_manager):
    medical_facilities = []
    for group_name in activity_manager.all_super_groups:
        if "visits" in group_name:
            continue
        grouptype = getattr(world, group_name)
        if grouptype is not None:
            if isinstance(grouptype, MedicalFacilities):
                medical_facilities.append(grouptype)
    return medical_facilities


class Epidemiology:
    """
    This class boxes all the functionality related to epidemics,
    namely the infections, infection seeds, infection selectors,
    and susceptibility setter.
    """

    def __init__(
        self,
        infection_selectors: InfectionSelectors = None,
        infection_seeds: "InfectionSeeds" = None,
        immunity_setter: ImmunitySetter = None,
        medical_care_policies: MedicalCarePolicies = None,
        medical_facilities: MedicalFacilities = None,
    ):
        self.infection_selectors = infection_selectors
        self.infection_seeds = infection_seeds
        self.immunity_setter = immunity_setter 
        self.medical_care_policies = medical_care_policies
        self.medical_facilities = medical_facilities

    def set_immunity(self, population):
        if self.immunity_setter:
            self.immunity_setter.set_immunity(population)

    def set_effective_multipliers(self, population):
        if self.effective_multiplier_setter:
            self.effective_multiplier_setter.set_multipliers(population)

    def set_medical_care(self, world, activity_manager):
        self.medical_facilities = _get_medical_facilities(
            world=world, activity_manager=activity_manager
        )
        if activity_manager.policies:
            self.medical_care_policies = activity_manager.policies.medical_care_policies

    def infection_seeds_timestep(self, timer, record: Record = None):
        if self.infection_seeds:
            self.infection_seeds.unleash_virus_per_day(timer.date, record=record)

    def do_timestep(
        self,
        world: World,
        timer: Timer,
        record: Record = None,
        infected_ids: list = None,
        infection_ids: list = None,
        people_from_abroad_dict: dict = None,
    ):
        # infect the people that got exposed
        if self.infection_selectors:
            infect_in_domains = self.infect_people(
                world=world,
                time=timer.now,
                infected_ids=infected_ids,
                infection_ids=infection_ids,
                people_from_abroad_dict=people_from_abroad_dict,
            )
            to_infect = self.tell_domains_to_infect(
                world=world, timer=timer, infect_in_domains=infect_in_domains
            )

        # update the health status of the population
        self.update_health_status(
            world=world, time=timer.now, duration=timer.duration, record=record
        )
        if record:
            record.summarise_time_step(timestamp=timer.date, world=world)
            record.time_step(timestamp=timer.date)

    @staticmethod
    def bury_the_dead(world: World, person: "Person", record: Record = None):
        """
        When someone dies, send them to cemetery.
        ZOMBIE ALERT!!

        Parameters
        ----------
        time
        person:
            person to send to cemetery
        """
        if record is not None:
            if person.medical_facility is not None:
                death_location = person.medical_facility.group
            else:
                death_location = person.residence.group
            record.accumulate(
                table_name="deaths",
                location_spec=death_location.spec,
                location_id=death_location.id,
                dead_person_id=person.id,
            )
        person.dead = True
        person.infection = None
        cemetery = world.cemeteries.get_nearest(person)
        cemetery.add(person)
        if person.residence.group.spec == "household":
            household = person.residence.group
            person.residence.residents = tuple(
                mate for mate in household.residents if mate != person
            )
        person.subgroups = Activities(None, None, None, None, None, None)


    @staticmethod
    def recover(person: "Person", record: Record = None):
        """
        When someone recovers, erase the health information they carry and change their susceptibility.

        Parameters
        ----------
        person:
            person to recover
        time:
            time (in days), at which the person recovers
        """
        if record:
            record.accumulate(
                table_name="recoveries",
                recovered_person_id=person.id,
                infection_id=person.infection.infection_id(),
            )
        person.infection = None

    def update_health_status(
        self, world: World, time: float, duration: float, record: Record = None
    ):
        """
        Update symptoms and health status of infected people.
        Send them to hospital if necessary, or bury them if they
        have died.

        Parameters
        ----------
        time:
            time now
        duration:
            duration of time step
        """
        for person in world.people.infected:
            previous_tag = person.infection.tag
            new_status = person.infection.update_health_status(time, duration)
            if record is not None:
                if previous_tag != person.infection.tag:
                    record.accumulate(
                        table_name="symptoms",
                        infected_id=person.id,
                        symptoms=person.infection.tag.value,
                        infection_id=person.infection.infection_id(),
                    )
            # Take actions on new symptoms
            if self.medical_care_policies:
                self.medical_care_policies.apply(
                    person=person,
                    medical_facilities=self.medical_facilities,
                    days_from_start=time,
                    record=record,
                )
            if new_status == "recovered":
                self.recover(person, record=record)
            elif new_status == "dead":
                self.bury_the_dead(world, person, record=record)

    def infect_people(
        self, world, time, infected_ids, infection_ids, people_from_abroad_dict
    ):
        """
        Given a list of infected ids, it initialises an infection object for them
        and sets it to person.infection. For the people who do not live in this domain
        a dictionary with their ids and domains is prepared to be sent through MPI.
        """
        foreign_ids = []
        foreign_infection_ids = []
        for person_id, infection_id in zip(infected_ids, infection_ids):
            if person_id in world.people.people_ids:
                person = world.people.get_from_id(person_id)
                self.infection_selectors.infect_person_at_time(
                    person=person, time=time, infection_id=infection_id
                )
            else:
                foreign_ids.append(person_id)
                foreign_infection_ids.append(infection_id)

        infect_in_domains = {}
        if foreign_ids:
            people_ids = []
            people_domains = []
            for spec in people_from_abroad_dict:
                for group in people_from_abroad_dict[spec]:
                    for subgroup in people_from_abroad_dict[spec][group]:
                        p_ids = list(
                            people_from_abroad_dict[spec][group][subgroup].keys()
                        )
                        people_ids += p_ids
                        for id in p_ids:
                            people_domains.append(
                                people_from_abroad_dict[spec][group][subgroup][id][
                                    "dom"
                                ]
                            )
            infection_counter = 0
            for id, domain in zip(people_ids, people_domains):
                if id in foreign_ids:
                    if domain not in infect_in_domains:
                        infect_in_domains[domain] = {}
                        infect_in_domains[domain]["id"] = []
                        infect_in_domains[domain]["inf_id"] = []
                    infect_in_domains[domain]["id"].append(id)
                    infect_in_domains[domain]["inf_id"].append(
                        foreign_infection_ids[infection_counter]
                    )
                    infection_counter += 1
        return infect_in_domains

    def tell_domains_to_infect(self, world, timer, infect_in_domains):
        """
        Sends information about the people who got infected in this domain to the other domains.
        """
        mpi_comm.Barrier()
        tick, tickw = perf_counter(), wall_clock()

        invalid_id = 4294967295  # largest possible uint32
        empty = np.array(
            [
                invalid_id,
            ],
            dtype=np.uint32,
        )

        # we want to make sure we transfer something for every domain.
        # (we have an np.concatenate which doesn't work on empty arrays)

        people_ids = [empty for x in range(mpi_size)]
        infection_ids = [empty for x in range(mpi_size)]

        # FIXME: domain id should not be floats! Origin is well upstream!
        for x in infect_in_domains:
            people_ids[int(x)] = np.array(infect_in_domains[x]["id"], dtype=np.uint32)
            infection_ids[int(x)] = np.array(
                infect_in_domains[x]["inf_id"], dtype=np.uint32
            )

        people_to_infect, n_sending, n_receiving = move_info(people_ids)
        infection_to_infect, n_sending, n_receiving = move_info(infection_ids)

        tock, tockw = perf_counter(), wall_clock()
        logger.info(
            f"CMS: Infection COMS-v2 for rank {mpi_rank}/{mpi_size}({n_sending+n_receiving})"
            f"{tock-tick},{tockw-tickw} - {timer.date}"
        )
        mpi_logger.info(f"{timer.date},{mpi_rank},infection,{tock-tick}")

        for person_id, infection_id in zip(people_to_infect, infection_to_infect):
            try:
                person = world.people.get_from_id(person_id)
                self.infection_selectors.infect_person_at_time(
                    person=person, time=timer.now, infection_id=infection_id
                )
            except:
                if person_id == invalid_id:
                    continue
                raise
