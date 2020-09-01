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

import logging
import numpy, time
from june.mpi_setup import comm, size, rank
from june.infection.infection import Infection
from june.infection.transmission import Transmission
from june.infection.symptoms import Symptoms

logger = logging.getLogger(__name__)

def make_domains(super_areas, size):
    """ Generator to partition world into domains"""
    indices = numpy.arange(len(super_areas))
    splits = numpy.array_split(indices, size)
    for s in splits:
        yield super_areas[s[0]:s[-1]+1]


class DomainPopulation:
    """
    Holds the information necessary to manipulate loops over people in the domain.
    Provides a list-like iterator, but also includes the normal dictionary index.
    """
    def __init__(self, people, inbound_people, n_inbound, n_outbound):
        """
        Initialise with a dictionary of persons who are local, the inbound halos,  and the number of folk
        in the inbound and outbound halo regions.
        """
        self.people = people
        self.n_inbound = n_inbound
        self.n_outbound = n_outbound
        self.n_resident = len(self) - self.n_inbound
        self.halo_people = [item for sublist in
                            [v.values() for v in [halo for halo in inbound_people.values()]]
                            for item in sublist]
        self.outbound_not_working = 0

    def __delitem__(self, key):
        """
        Remove a person from the domain
        """
        # To implement this we would have to make sure we know how to remove
        # people in the inbound/outbound domain as well, and we don't know how to do that now.
        # Really we don't want it to happen!
        raise NotImplementedError

    def __iter__(self):
        for key, person in self.people.items():
            yield person

    def __len__(self):
        return len(self.people)

    def from_index(self, key):
        return self.people[key]

    def initialise(self, timer_state):
        """
        At beginning of the simulation, some people are not actually in the domain.
        We need to start at home. Not at work.
        """
        print('Initialising halo')
        assert timer_state != 'primary_activity'
        for p in self.halo_people:
            p.active = False

    @property
    def infected(self):
        """
        Return an iterator (list) which has all the infected people who are active in this domain
        """
        for person in self:
            if person.infected and person.active:
                yield person
            else:
                continue

    @property
    def number_infected(self):
        """ Find out how many people are infected"""
        return len([p for p in self.infected])

    @property
    def resident(self):
        """
        Iterator over people who are actually resident in the domain
        """
        for person in self:
            if person not in self.halo_people:
                yield person
            else:
                continue

    def number_active(self, timestep_status):
        """
        Return the number of people who are active now
        """
        print('number active', len(self), self.n_outbound, self.n_inbound, self.outbound_not_working, timestep_status)
        if timestep_status == 'primary_activity':
            return len(self) - self.n_outbound + self.outbound_not_working
        else:
            return len(self) - self.n_inbound

    @property
    def debug_stats(self):
        stati = {'dead':0, 'busy':0, 'hospitalised':0, 'active':0}
        for p in self.people:
            for status in stati:
                if getattr(self.people[p], status):
                    stati[status] +=1
        stati['all']=len(self)
        stati['in'] = self.n_inbound
        stati['out'] = self.n_outbound
        stati['notw'] = self.outbound_not_working
        return str(stati)


def parallel_setup(self, comm, debug=False):
    """ Initialise by defining what part of the known world is outside _THIS_ domain."""

    # get comms info
    rank = comm.Get_rank()
    size = comm.Get_size()

    # let's just brute force it with MPI for now
    # partition the list of superareas

    # for now we collect local_peoole as the folk who need to be passed back as a subset of the world.
    # at some point in the future we can remove the rest of the world.
    local_people = {}

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
            local_people[person.id] = person

        if work_here and not live_here:
            # these folk commute into this domain, but where from?
            self.inbound_workers[super_index[home_super_area]][person.id] = person
            local_people[person.id] = person
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

    print("RR", rank, live, inb, oub, gone, len(local_people))
    # we can't delete them inside the loop, bad things happen if we do that.
    # FIXME takes a LONG time for many people eg 1000s for 67000 peeps
    #for p in binable:
    #    del self.people[p]
    # These people probably still exist in other lists, so we need to kill all them too.
    # E.g need to kill unused households and unused companies etc otherwise each partition will
    # need nearly all the memory of the entire world.

    print(rank, npeople, live, inb, oub, gone)
    inbound = sum([len(i) for k,i in self.inbound_workers.items()])
    outbound = sum([len(i) for k, i in self.outside_workers.items()])

    self.local_people = DomainPopulation(local_people, self.inbound_workers, inbound, outbound)

    print(f'Partition {rank} has {len(self.local_people)} (of {npeople} - {inbound} in and {outbound} out).')
    end_time = time.localtime()
    current_time = time.strftime("%H:%M:%S", end_time)
    delta_time = time.mktime(end_time) - time.mktime(start_time)
    print(f'Domain setup complete for rank {rank} at {current_time} ({delta_time}s)')
    # count people checks
    assert len(local_people) == live + inb
    assert live + inb + gone == len(self.people)


def parallel_update(self, direction, timer):
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

    other_rank_ifs_am = {i: {} for i in range(size)}
    other_rank_ifs_pm = {i: {} for i in range(size)}

    coll_inf_send_am = {i: {} for i in range(size)}
    coll_inf_send_pm = {i: {} for i in range(size)}

    logger.info(f"Direction {direction} in domain {self.domain_id}"
                f" - active/infected people initially "
                f"{self.local_people.number_active(timer.last_state)}/{self.local_people.number_infected}")

    # Note that we have to put people before getting people, otherwise we get a deadlock
    if direction == 'am':
        # send people away
        # we need only to pass infection status of infected people, so only some of these folk need writing out
        # we need to loop over the _other_ ranks (avoiding puns about NCOs)
        for other_rank in self.outside_workers:
            if other_rank == self.domain_id:
                continue
            outside_domain = self.outside_workers[other_rank]
            infected_status_outside_workers = {}
            for pid, person in outside_domain.items():

                if person.infected:
                    infected_status_outside_workers[pid] = person.infected

#            print(rank, "sending to ", other_rank)
#            for pid, infec in infected_status_outside_workers.items():
#                print(rank, "sending to ", other_rank, "infec status outside ", infec)
            comm.send(infected_status_outside_workers, dest=other_rank, tag=200)
#            for pid, infec in infected_status_outside_workers.items():
#                print(rank, "sent to ", other_rank, "infec status outside ", infec)


        # pay attention to people who are coming in
        for other_rank in self.inbound_workers:
            if other_rank == self.domain_id:
                continue
            outside_domain = self.inbound_workers[other_rank]

            infection_test_am = comm.recv(source=other_rank, tag=200)
            

            if infection_test_am:
                for pid, infec in infection_test_am.items():
                    print(rank, pid, "rcv from ", other_rank, "infection_status of incoming workers ", infec)
                    print(rank, pid, "infect stat here ", self.inbound_workers[other_rank][pid].infected)
#                    other_rank_ifs_am[other_rank][pid] = infec
                    if infec != self.inbound_workers[other_rank][pid].infected:
                        other_rank_ifs_am[other_rank][pid] = infec
            print("other_rank_ifs_am ", other_rank_ifs_am)
#                        print("am rank, other_rank, pid, infec ", rank, other_rank, pid, infec)
        coll_inf_send_am[rank]  = other_rank_ifs_am
            
        XX = comm.allgather(coll_inf_send_am[rank])
        for d in range(size):
            print("col am ", d, XX[d])


    elif direction == 'pm':

        # FIXME: What happens to inbound workers during initialisation?
        for other_rank in self.inbound_workers:
            if other_rank == self.domain_id:
                continue
            outside_domain = self.inbound_workers[other_rank]
            infected_status_inbound_workers = {}
            for pid, person in outside_domain.items():
                if person.infected:
                    infected_status_inbound_workers[pid] = person.infected

#            for pid, infec in infected_status_inbound_workers.items():
#                print(rank, "sending to ", other_rank, "infec status ourside ", infec)
            comm.send(infected_status_inbound_workers, dest=other_rank, tag=200)
#            for pid, infec in infected_status_inbound_workers.items():
#                print(rank, "sent to ", other_rank, "infec status ourside ", infec)

        # now see if any of our workers outside have got infected.
        for other_rank in self.outside_workers:
            if other_rank == self.domain_id:
                continue
            infection_test_pm = comm.recv(source=other_rank, tag=200)

            if infection_test_pm:
                for pid, infec in infection_test_pm.items():
                    print(rank, pid, "recv fromm ", other_rank, "infection status ", infec )
                    print(rank, pid, "infect stat here ", self.outside_workers[other_rank][pid].infected)
                    if infec != self.outside_workers[other_rank][pid].infected:
                        other_rank_ifs_pm[other_rank][pid] = infec
            print("other_rank_ifs_pm ", other_rank_ifs_pm)
#                        print("pm rank, other_rank, pid, infec ", rank, other_rank, pid, infec)
        coll_inf_send_pm[rank]  = other_rank_ifs_pm
        YY = comm.allgather(coll_inf_send_pm[rank])
        for d in range(size):
            print("col pm ", d, YY[d])



    if direction == 'am':
        # send people away
        # we need only to pass infection status of infected people, so only some of these folk need writing out
        # we need to loop over the _other_ ranks (avoiding puns about NCOs)
        not_working_today = 0
        for other_rank in self.outside_workers:
            if other_rank == self.domain_id:
                continue
            outside_domain = self.outside_workers[other_rank]
            tell_them = {}
            tmp = {}
            for pid, person in outside_domain.items():
                if person.hospitalised:
                    not_working_today += 1
                else:
                    person.active = False
                if person.infected:
                    print("PERS ", rank, other_rank_ifs_am[rank], person.id)
                    print("RANK ", rank, other_rank_ifs_am, person.id)
# figure out what to send  - if the person sending to doesn't have an infection, we need to send it, else just send the suscptibility & trans prob
                    if person.id in XX[other_rank][rank]:
                        #send the infection class
                        print("SENDING INFECTION CLASS for ", person.id, "from to ", rank, other_rank)
                        tmp["infection"] = person.infection
                        tmp["susceptibility"] = person.susceptibility
                    else:
                        tmp["infection"] = None
                        tmp["susceptibility"] = person.susceptibility
                        tmp["transmission_probability"] = person.infection.transmission.probability
                        tell_them[pid] = tmp
                        for a, b in tell_them.items():
                            print("sending ", a, b)
            # _put_updates(self, other_rank, tell_them, timestep)
            comm.send(tell_them, dest=other_rank, tag=100)


        # pay attention to people who are coming in
        more_active = 0
        for other_rank in self.inbound_workers:
            if other_rank == self.domain_id:
                continue
            outside_domain = self.inbound_workers[other_rank]

            # FIXME and we need to sort out their hospitalisation status
            # _get_updates(self, id, timestep)


            incoming = comm.recv(source=other_rank, tag=100)
            if incoming:
                for pid, infec in incoming.items():
                   if infec == None:
                       continue

                   if infec["infection"] == None:
                       print(rank, "from ", other_rank, "pid ", pid, outside_domain[pid].susceptibility,
                                                                 outside_domain[pid].infection.transmission.probability)
                       outside_domain[pid].susceptibility = infec["susceptibility"]
                       outside_domain[pid].infection.transmission.probability = infec["transmission_probability"]
                       print(rank, "updated from ", other_rank, "pid ", pid, outside_domain[pid].susceptibility,
                                                                 outside_domain[pid].infection.transmission.probability)
                   else:
                       print("*** passed infectiom class apparently")
                       print(rank, "updating from nothing", other_rank, "pid ", pid )
                       outside_domain[pid].susceptibility = infec["susceptibility"]
                       outside_domain[pid].infection = infec["infection"]
                       print(rank, "updated from nothing", other_rank, "pid ", pid, outside_domain[pid].susceptibility,
                                                                 outside_domain[pid].infection.transmission.probability)


            for pid, person in outside_domain.items():
                person.active = True
                more_active += 1

        self.local_people.outbound_not_working = not_working_today

    elif direction == 'pm':

        # FIXME: What happens to inbound workers during initialisation?
        for other_rank in self.inbound_workers:
            if other_rank == self.domain_id:
                continue
            outside_domain = self.inbound_workers[other_rank]
            tell_them = {}
            tmp = {}
            for pid, person in outside_domain.items():
                person.active = False
                if person.infected: # it happened at work!
                    print("PERSPM ", rank, other_rank_ifs_pm[rank], person.id)
                    print("RANKPM ", rank, other_rank_ifs_pm, person.id)
                    if person.id in YY[other_rank][rank]:
                        #send the infection class
                        print("SENDING INFECTION CLASS for ", person.id, "from to ", rank, other_rank)
                        tmp["infection"] = person.infection
                        tmp["susceptibility"] = person.susceptibility
                    else:
                        tmp["infection"] = None
                        tmp["susceptibility"] = person.susceptibility
                        tmp["transmission_probability"] = person.infection.transmission.probability
                        tell_them[pid] = tmp
                        for a, b in tell_them.items():
                            print("sending ", a, b)
            # _put_updates(self, other_rank, tell_them, timestep)
            comm.send(tell_them, dest=other_rank, tag=100)

        # now see if any of our workers outside have got infected.
        for other_rank in self.outside_workers:
            if other_rank == self.domain_id:
                continue
            outside_domain = self.outside_workers[other_rank]

            incoming = comm.recv(source=other_rank, tag=100)
            if incoming:
                for pid, infec in incoming.items():
                   if infec == None:
                       continue

                   if infec["infection"] == None:
                       print("$$$$ pid ", pid)
                       print(rank, "from ", other_rank, "pid ", pid, outside_domain[pid].susceptibility,
                                                                 outside_domain[pid].infection.transmission.probability)
                       outside_domain[pid].susceptibility = infec["susceptibility"]
                       outside_domain[pid].infection.transmission.probability = infec["transmission_probability"]
                       print(rank, "updated from ", other_rank, "pid ", pid, outside_domain[pid].susceptibility,
                                                                 outside_domain[pid].infection.transmission.probability)
                   else:
                       outside_domain[pid].susceptibility = infec["susceptibility"]
                       outside_domain[pid].infection = infec["infection"]
                       print(rank, "updated from nothing", other_rank, "pid ", pid, outside_domain[pid].susceptibility,
                                                                 outside_domain[pid].infection.transmission.probability)

            for pid, person in self.outside_workers[other_rank].items():
                self.outside_workers[other_rank][pid].active=True

    logger.info(f"Direction {direction} in domain {self.domain_id}"
                f" - active/infected people now "
                f"{self.local_people.number_active(timer.state)}/{self.local_people.number_infected}")



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









