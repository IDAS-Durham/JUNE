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

def parallel_setup(self, outside=None):
    """ Initialise by defining what part of the known world is outside _THIS_ domain."""
    self.active = outside is not None
    self.outside_workers = []
    self.inbound_workers = []
    for super_area in outside:
        # find people who work outside
        self.outside_workers += super_area.people
        # FIXME: really what we want to do is decorate people but we don't want to modify them yet.
        # now hide the places outside ... (we can delete them for this instance)
        # FIXME: We probably want to delete stuff in the world so it isn't active here.
        #        But we'll do that later in the p.o.c.


def parallel_update(self, direction):
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
    # This code to be developed in several stages:
    # 1. Develop a method for sending people out, and getting them back
    # 2. ...
    if direction == 'am':
        # send people away
        for person in self.outside_workers:
            person.busy = True
        _put_updates(self)
        # pay attention to people who are coming in
        for person in self.inbound_workers:
            person.busy = False
        _get_updates(self)


def _put_updates(self):
    """ Write necessary information about people for infection transmission while they are outside"""
    pass


def _get_updates(self):
    """" Get necessary information about possible changes which happened to people while outside"""
    pass









