class CommuteCityDistributor:
    """
    Distirbute people to commute cities based on where they work
    """

    def __init__(self, commutecities, msoas):
        """
        commutecities: members of CommuteCities class
        msoa: members of the MSOArea class
        """

        self.commutecities = commutecities
        self.msoas = msoas

    def distribute_people(self):
        "Distirbute people to commute cities"

        for commutecity in self.commutecities:
            metro_msoas = commutecity.metro_msoas

            none_type = 0
            for msoa in self.msoas:
                if msoa.name in metro_msoas:
                    for person in msoa.workers:
                        # assign people who commute to the given city

                        if (
                            person.mode_of_transport is not None
                            and person.mode_of_transport.is_public
                        ):
                            commutecity.add(
                                person,
                            )
