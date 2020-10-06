from june.demography.person import Person
from june.groups.care_home import CareHome
from june.groups.household import Household


class TestGroup:
    def test_group_types(self):
        group = Household()
        group.add(
            Person(),
            Household.SubgroupType.adults
        )
        assert group[Household.SubgroupType.adults].size == 1

    def test_ids(self):
        household_1 = Household()
        household_2 = Household()
        care_home_1 = CareHome(None, None, None)
        care_home_2 = CareHome(None, None, None)

        assert household_2.id == household_1.id + 1
        assert household_1.name == f"Household_{household_1.id:05d}"

        assert care_home_2.id == care_home_1.id + 1
        assert care_home_1.name == f"CareHome_{care_home_1.id:05d}"
