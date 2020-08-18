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


def parallel_setup(self, outside=None):
    """ Initialise by defining what part of the known world is outside _THIS_ domain."""
    self.active = outside is not None
    self.outside_workers = []
    self.inbound_workers = []
    # FIXME: will need to be set by configuration
    self.domain_id = 1
    self.other_domain_ids = [2,]
    for super_area in outside:
        # find people who work outside
        self.outside_workers += super_area.people
        # FIXME: really what we want to do is decorate people but we don't want to modify them yet.
        # now hide the places outside ... (we can delete them for this instance)
        # FIXME: We probably want to delete stuff in the world so it isn't active here.
        #        But we'll do that later in the p.o.c.


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
    tell_them = []
    # Note that we have to put people before getting people, otherwise we get a deadlock
    if direction == 'am':
        # send people away
        # we need only to pass infection status of infected people, so only some of these folk need writing out
        for person in self.outside_workers:
            if not person.hospitalised:
                person.busy = True
            if person.infected:
                tell_them.append(person)
        _put_updates(self, tell_them, timestep)
        # pay attention to people who are coming in
        for person in self.inbound_workers:
            person.busy = False
        # we might need to update the infection status of these people
        _get_updates(self, timestep)
    elif direction == 'pm':

        # FIXME: What happens to inbound workers during initialisation?
        for person in self.inbound_workers:
            person.busy = True
            if person.infected: # it happened at work!
                tell_them.append(person)
        _put_updates(self, tell_them, timestep)
        # now see if any of our workers outside have got infected.
        _get_updates(self)


def _put_updates(self, tell_them, timestep):
    """
    Write necessary information about people for infection transmission while they are outside.
    In practice, we only need to tell them about infected people (the list of people called "tell_them").
    """
    data = [set_person_info(p) for p in tell_them]
    with open(f'parallel_putter_{self.domain_id}_{timestep}.json','w') as f:
        json.dump(data, f)
    print(f"Serialisation of person infection properties for parallelisation is not yet working")


def _get_updates(self, timestep):
    """" Get necessary information about possible changes which happened to people while outside"""
    try:
        for id in self.other_domain_ids:
            with open(f'parallel_putter_{id}_{timestep}.json','r') as f:
                updated = json.load(f)
    except FileNotFoundError:
        # We'd wait a fraction of a second here in real life, but for now, we'll just skip it
        # FIXME
        pass

    #FIXME: Are people indexed in anyway? Then use that index here ...
    print(f"Unable (yet) to update people from domain {id} for timestep {timestep}")


def set_person_info(person):
    """ set person info that needs to be passed and serialise it"""
    return int(person.id)










