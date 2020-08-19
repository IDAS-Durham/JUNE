#
# Contains two methods to be monkey patched onto the World CLASS definition when we want a parallel world.
# Example usage in run_simulation.py:
#
#   ... load entire world from file as normal ...
#   # add parallelism
#   World.parallel_setup = parallel_setup
#   World.parallel_update = parallel_update
#   world.parallel_setup(world.super_areas[0:2])
#
import json


def mydomain(super_areas, size):
    """ Generator to partition world into domains"""
    for i in range(0, len(super_areas), size):
        yield super_areas[i:i + size]


def parallel_setup(self, rank, size):
    """ Initialise by defining what part of the known world is outside _THIS_ domain."""

    # let's just brute force it with MPI for now
    # partition the list of superareas
    # each of the following lists is 2-d, first dimension is number of "other domains" of relevance,
    # second is workers in those domains.
    self.outside_workers = []
    self.inbound_workers = []
    self.domain_id = rank
    # need to find all the people who are in my domain who work elsewhere, and all those who live
    # elsewhere and work in my domain. All the other people can be deleted in this mpi process.
    # We could probably delete other parts of the world too, but we can do that in a later iteration.

    # Currently the person instances in world.people do not have the work_super_area populated when
    # read back from a file so we have to work this all out from the people in the areas.

    for i, super_area in enumerate(mydomain(self.super_areas, size)):
        if i == self.domain_id:
            continue
            # this is me!
            # who works outside?
            # who from outside works here?




def parallel_update(self, direction, timestep):
    """
    (This method overrides the superclass mixin stub)

    The world can contain two or more domains, each of which is operating in parallel.

    To make this work for this domain , we need to mark some people as outside when they do not need to be processed
    since they have crossed into another domain (gone to work in another domain or returned
    to another domain having worked in this domain).
    :param world:
    :param direction: 'am' or 'pm'
    :return: updated world.

    When
        direction='am': people from outside come in to work or people inside leave to work,
        direction='pm': people return from work or head home to another domain.
    """

    # Note that we have to put people before getting people, otherwise we get a deadlock
    if direction == 'am':
        # send people away
        # we need only to pass infection status of infected people, so only some of these folk need writing out
        for id, outside_domain in enumerate(self.outside_workers):
            tell_them = []
            for person in outside_domain:
                if not person.hospitalised:
                    person.busy = True
                if person.infected:
                    tell_them.append(person)
            _put_updates(self, id, tell_them, timestep)
        # pay attention to people who are coming in
        for id, outside_domain in enumerate(self.inbound_workers):
            for person in outside_domain:
                person.busy = False
            # we might need to update the infection status of these people
            _get_updates(self, id, timestep)
    elif direction == 'pm':

        # FIXME: What happens to inbound workers during initialisation?
        for id, outside_domain in enumerate(self.inbound_workers):
            tell_them = []
            for person in self.inbound_workers:
                person.busy = True
                if person.infected: # it happened at work!
                    tell_them.append(person)
            _put_updates(self, id, tell_them, timestep)
        # now see if any of our workers outside have got infected.
        for id, outside_domain in enumerate(self.outside_workers):
            _get_updates(self, id, timestep)


def _put_updates(self, domain_id, tell_them, timestep):
    """
    Write necessary information about people for infection transmission while they are outside.
    In practice, we only need to tell them about infected people (the list of people called "tell_them").
    """
    data = [set_person_info(p) for p in tell_them]
    #with open(f'parallel_putter_{self.domain_id}_{domain_id}_{timestep}.json','w') as f:
    #    json.dump(data, f)
    #print(f"Serialisation of person infection properties for parallelisation is not yet working")
    #forget all this gubbins, let's use MPI!

def _get_updates(self, domain_id, timestep):
    """" Get necessary information about possible changes which happened to people while outside"""
    #try:
    #    for id in self.other_domain_ids:
    #        with open(f'parallel_putter_{id}_{timestep}.json','r') as f:
    #            updated = json.load(f)
    #except FileNotFoundError:
    #    # We'd wait a fraction of a second here in real life, but for now, we'll just skip it
    #    # FIXME
    #    pass
    # forget all this gubbins, let's use MPI.

    #FIXME: Are people indexed in anyway? Then use that index here ...
    print(f"Unable (yet) to update people from domain {id} for timestep {timestep}")


def set_person_info(person):
    """ set person info that needs to be passed and serialise it"""
    return int(person.id)










