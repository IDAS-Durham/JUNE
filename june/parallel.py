#
# Contains two methods to be monkey patched onto the World CLASS definition when we want a parallel world.
# Example usage in run_simulation.py:
#
#   ... load entire world from file as normal ...
#   # add parallelism
#   World.parallel_setup = parallel_setup
#   World.parallel_update = parallel_update
#   comm = MPI.COMM_WORLD
#   world.parallel_setup(comm)
#

import json
import numpy, time
from june.mpi_setup import comm, size, rank

def make_domains(super_areas, size):
    """ Generator to partition world into domains"""
    indices = numpy.arange(len(super_areas))
    splits = numpy.array_split(indices, size)
    for s in splits:
        yield super_areas[s[0]:s[-1]+1]


def parallel_setup(self, comm, debug=False):
    """ Initialise by defining what part of the known world is outside _THIS_ domain."""

    # get comms info
    rank = comm.Get_rank()
    size = comm.Get_size()

    # let's just brute force it with MPI for now
    # partition the list of superareas

    # for now we collect local_peoole as the folk who need to be passed back as a subset of the world.
    # at some point in the future we can remove the rest of the world.
    self.local_people = []

    # these are dictionaries of people in each domain who float back and forward.
    self.outside_workers = {i: {} for i in range(size)}
    self.inbound_workers = {i: {} for i in range(size)}
    # (of course there will never be anything but an empty list in the the rank of this PE.)
    self.domain_id = rank
    self.other_domain_ids = [r for r in range(size) if r != rank]
    start_time = time.localtime()
    current_time = time.strftime("%H:%M:%S", start_time)
    print(f'Starting domain setup for rank {rank} at {current_time}')
    # need to find all the people who are in my domain who work elsewhere, and all those who live
    # elsewhere and work in my domain. All the other people can be deleted in this mpi process.
    # We could probably delete other parts of the world too, but we can do that in a later iteration.

    # Currently the person instances in world.people do not have the work_super_area populated when
    # read back from a file so we have to work this all out from the people in the areas.

    # First partition information about superareas
    self.parallel_partitions = []
    for i, super_areas in enumerate(make_domains(self.super_areas, size)):
        self.parallel_partitions.append([sa.name for sa in super_areas])

    assert len(self.super_areas) == sum([len(i) for i in self.parallel_partitions])

    # Now parse people to see if they are in any of our interesting areas
    # Note that we can delete people who are not interesting!
    # We should probably delete other parts of the world that are not interesting too ...

    npeople = self.people.total_people

    # index the super_areas to domains so we don't have to do a long loop for everyone:
    super_index = {}
    for sa in self.super_areas:
        for i, p in enumerate(self.parallel_partitions):
            if sa.name in p:
                super_index[sa.name] = i

    live, inb, oub, gone = 0, 0, 0, 0
    binable = []

    for person in self.people:
        home_super_area = person.area.super_area.name
        work_super_area = None
        if person.primary_activity:  # some people are too old to work, some are children
            if person.primary_activity.group.spec == "company":
                work_super_area = person.primary_activity.group.super_area.name

        live_here = super_index[home_super_area] == rank
        if work_super_area:
            work_here = super_index[work_super_area] == rank
        else:
            # for this loop we pretend that everyone who doesn't work, but lives here, works here.
            work_here = live_here

        if live_here:
            live += 1
            self.local_people.append(person)

        if work_here and not live_here:
            # these folk commute into this domain, but where from?
            self.inbound_workers[super_index[home_super_area]][person.id] = person
            # these people are the halo people:
            self.local_people.append(person)
            inb += 1
        elif live_here and not work_here:
            # these folk commute out, but where to?
            self.outside_workers[super_index[work_super_area]][person.id] = person
            oub += 1
        elif not live_here:
            # Anyone left is not interesting, and we want to bin them from this domain.
            # they never spend any time here interacting with anyone.
            binable.append(person)
            gone += 1

    print("RR", rank, live, inb, oub, gone, len(self.local_people))
    # we can't delete them inside the loop, bad things happen if we do that.
    # FIXME takes a LONG time for many people eg 1000s for 67000 peeps
    #for p in binable:
    #    del self.people[p]
    # These people probably still exist in other lists, so we need to kill all them too.
    # E.g need to kill unused households and unused companies etc otherwise each partition will
    # need nearly all the memory of the entire world.

    print(rank, npeople, live, inb, oub, gone)
    inbound = sum([len(i) for k,i in self.inbound_workers.items()])
    outbound = sum([len(i) for k,i in self.outside_workers.items()])
    print(f'Partition {rank} has {self.people.total_people} (of {npeople} - {inbound} in and {outbound} out).')
    end_time = time.localtime()
    current_time = time.strftime("%H:%M:%S", end_time)
    delta_time = time.mktime(end_time) - time.mktime(start_time)
    print(f'Domain setup complete for rank {rank} at {current_time} ({delta_time}s)')
    # count people checks
    assert len(self.local_people) == live + inb
    assert live + inb + gone == len(self.people)


    # We'll check everything is covered, and use this as a sync point before integration
    # the total number of people across the world, and split into domains should be
    # the sum of the folk who live in each domain. That number should be, for each
    # domain: the population it knows about, less those people who are commuting in.

    my_population = self.people.total_people - inbound


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
        # we need to loop over the _other_ ranks (avoiding puns about NCOs)
        for other_rank in self.outside_workers:
            if other_rank == self.domain_id:
                continue
            outside_domain = self.outside_workers[other_rank]
            tell_them = {}
            for pid, person in outside_domain.items():
                if not person.hospitalised:
                    person.busy = True
                #FIXME: Actually, this is the wrnog place, since policy may keep them at home ...
                if person.infected:
                    # tell_them.append(person)
                    print('>>a',self.domain_id, other_rank, person.id, person.infected, person.infection.infection_probability)
                    tell_them[pid] = person.infection
            # _put_updates(self, other_rank, tell_them, timestep)
            comm.send(tell_them, dest=other_rank, tag=100)

        # pay attention to people who are coming in
        for other_rank in self.inbound_workers:
            if other_rank == self.domain_id:
                continue
            outside_domain = self.inbound_workers[other_rank]
            for pid, person in outside_domain.items():
                person.busy = False
            # we might need to update the infection status of these people
            # _get_updates(self, id, timestep)
            incoming = comm.recv(source=other_rank, tag=100)

            if incoming:
                for pid, infec in incoming.items():
                   self.inbound_workers[pid].infection = infec

        # print and compare with simulator output
        print("AM INFECTED", rank, len([p for p in self.local_people if p.infected == True]))

        return

    elif direction == 'pm' or direction == "wknd":

        # FIXME: What happens to inbound workers during initialisation?
        for other_rank in self.inbound_workers:
            if other_rank == self.domain_id:
                continue
            outside_domain = self.inbound_workers[other_rank]
            tell_them = {}
            for pid, person in outside_domain.items():
                person.busy = True
                if person.infected: # it happened at work!
                    # tell_them.append(person)
                    tell_them[pid] = person.infection
            # _put_updates(self, other_rank, tell_them, timestep)
            comm.send(tell_them, dest=other_rank, tag=100)

        # now see if any of our workers outside have got infected.
        for other_rank in self.outside_workers:
            if other_rank == self.domain_id:
                continue
            incoming = comm.recv(source=other_rank, tag=100)

            if incoming:
                print('>>i', self.domain_id, other_rank, [id for id, infec in incoming.items()])
            for pid, infec in incoming.items():
                self.outside_workers[other_rank][pid].infection = infec

        print("PM INFECTED", rank, len([p for p in self.local_people if p.infected == True]))


#def _put_updates(self, target_rank, tell_them, timestep):
#    """
#    Write necessary information about people for infection transmission while they are outside.
#    In practice, we only need to tell them about infected people (the list of people called "tell_them").
#    """
    # my domain is self.domain_id, and we are sending to domain_id
#    infected_ids = [set_person_info(p) for p in tell_them]

    # at this point, we do a send/receive in MPI land.
    # after receive would need to do the inverse of set_person_info ...
    # with open(f'parallel_putter_{self.domain_id}_{timestep}.json','w') as f:
    #     json.dump(infected_ids, f)


#def _get_updates(self, target_rank, timestep):
#    """Get necessary information about possible changes which happened to people while outside"""
    # try:
    #     for id in self.other_domain_ids:
    #         with open(f'parallel_putter_{id}_{timestep}.json','r') as f:
    #             updated = json.load(f)
    # except FileNotFoundError:
    #     # We'd wait a fraction of a second here in real life, but for now, we'll just skip it
    #    # FIXME
    #    # TODO lots of missed files due to MPI delays
    #      pass

    #FIXME: Are people indexed in anyway? Then use that index here ...


def set_person_info(person):
    """ set person info that needs to be passed and serialise it"""
    return int(person.id)









