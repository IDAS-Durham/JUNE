import os

import pandas as pd
import pytest

from june import commute as c
from june.groups import CommuteHubDistributor
from june.groups.commute import default_geographical_data_directory

test_data_filename = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "..",
    "..",
    "data",
    "census_data",
    "commute.csv"
)


#class TestCommute:
    #def test_coordinate_lookup(self):
    #    distributor = CommuteHubDistributor.from_file(
    #        commute_cities=[]
    #    )
    #    assert distributor._get_msoa_oa(
    #        "E00000001"
    #    ) == "E02000001"
    #    lat, long = distributor._get_area_lat_lon(
    #        "E00000001"
    #    )
    #    assert lat == pytest.approx(51.520271, abs=5)
    #    assert long == pytest.approx(-0.094911, abs=5)


class TestModeOfTransport:
    def test__setup_with_a_description__check_index(self):
        mode_of_transport = c.ModeOfTransport(description="hello")

        assert mode_of_transport.description == "hello"

        index = mode_of_transport.index(headers=["hi", "hello", "whatsup"])

        assert index == 1

        with pytest.raises(AssertionError):
            mode_of_transport.index(headers=["hi", "hel2lo"])

    def test__equality_override(self):
        mode_of_transport = c.ModeOfTransport(description="hello")

        assert mode_of_transport == "hello"

    def test__load_from_file__uses_correct_values_from_configs(self):
        modes_of_transport = c.ModeOfTransport.load_from_file()
        assert len(modes_of_transport) == 12
        assert "Work mainly at or from home" in modes_of_transport
        assert c.ModeOfTransport.load_from_file()[0] is modes_of_transport[0]

    def test__is_public(self):
        c.ModeOfTransport.load_from_file()
        bus = c.ModeOfTransport.with_description(
            "Bus, minibus or coach"
        )
        assert bus.is_public is True
        assert bus.is_private is False

        car = c.ModeOfTransport.with_description(
            "Driving a car or van"
        )
        assert car.is_public is False
        assert car.is_private is True


class TestRegionalGenerator:
    def test__total__sum_of_people_using_all_transports(self):
        weighted_modes = [(2, c.ModeOfTransport("car"))]

        regional_gen = c.RegionalGenerator(
            msoarea="test_area", weighted_modes=weighted_modes
        )

        assert regional_gen.total == 2

        weighted_modes = [
            (2, c.ModeOfTransport("car")),
            (4, c.ModeOfTransport("bus")),
            (1, c.ModeOfTransport("magic_carpet")),
        ]

        regional_gen = c.RegionalGenerator(
            msoarea="test_area", weighted_modes=weighted_modes
        )

        assert regional_gen.total == 7

    def test__modes__list_of_all_transports(self):
        weighted_modes = [(2, c.ModeOfTransport("car"))]

        regional_gen = c.RegionalGenerator(
            msoarea="test_area", weighted_modes=weighted_modes
        )

        assert regional_gen.modes == ["car"]

        weighted_modes = [
            (2, c.ModeOfTransport("car")),
            (4, c.ModeOfTransport("bus")),
            (1, c.ModeOfTransport("magic_carpet")),
        ]

        regional_gen = c.RegionalGenerator(
            msoarea="test_area", weighted_modes=weighted_modes
        )

        assert regional_gen.modes == ["car", "bus", "magic_carpet"]

    def test__weights__lists_people_per_transport_divided_by_total(self):
        weighted_modes = [(2, c.ModeOfTransport("car"))]

        regional_gen = c.RegionalGenerator(
            msoarea="test_area", weighted_modes=weighted_modes
        )

        assert regional_gen.weights == [1]

        weighted_modes = [
            (2, c.ModeOfTransport("car")),
            (4, c.ModeOfTransport("bus")),
            (1, c.ModeOfTransport("magic_carpet")),
        ]

        regional_gen = c.RegionalGenerator(
            msoarea="test_area", weighted_modes=weighted_modes
        )

        assert regional_gen.weights == [2 / 7, 4 / 7, 1 / 7]

    def test__weighted_choice__chooses_random_value_from_the_modes(self):
        weighted_modes = [(2, c.ModeOfTransport("car"))]

        regional_gen = c.RegionalGenerator(
            msoarea="test_area", weighted_modes=weighted_modes
        )

        assert regional_gen.weighted_random_choice() == "car"

        weighted_modes = [
            (2, c.ModeOfTransport("car")),
            (4, c.ModeOfTransport("bus")),
            (1, c.ModeOfTransport("magic_carpet")),
        ]

        regional_gen = c.RegionalGenerator(
            msoarea="test_area", weighted_modes=weighted_modes
        )

        assert regional_gen.weighted_random_choice() == "car" or "bus" or "magic_carpet"

    def test__weighted_choice__cant_choose_transports_with_0_people(self):
        weighted_modes = [
            (0, c.ModeOfTransport("car")),
            (4, c.ModeOfTransport("bus")),
            (0, c.ModeOfTransport("magic_carpet")),
        ]

        regional_gen = c.RegionalGenerator(
            msoarea="test_area", weighted_modes=weighted_modes
        )

        assert regional_gen.weighted_random_choice() == "bus"
        assert regional_gen.weighted_random_choice() == "bus"
        assert regional_gen.weighted_random_choice() == "bus"


class TestCommuteGenerator:
    # def test__region_gen_from_commute_gen__via_msoarea(self):
    #     regional_gen_0 = c.RegionalGenerator(
    #         msoarea="test_area", weighted_modes=[(2, c.ModeOfTransport("car"))]
    #     )

    #     commute_gen = c.CommuteGenerator(regional_generators={"north": regional_gen_0})

    #     regional_gen = commute_gen.regional_gen_from_msoarea(super_area="north")

    #     assert regional_gen == regional_gen_0

    #     regional_gen_1 = c.RegionalGenerator(
    #         msoarea="test_area",
    #         weighted_modes=[
    #             (2, c.ModeOfTransport("car")),
    #             (4, c.ModeOfTransport("bus")),
    #             (1, c.ModeOfTransport("magic_carpet")),
    #         ],
    #     )

    #     commute_gen = c.CommuteGenerator(
    #         regional_generators={
    #             "north": regional_gen_0, "south": regional_gen_1
    #         }
    #     )

    #     regional_gen = commute_gen.regional_gen_from_msoarea(super_area="north")

    #     assert regional_gen == regional_gen_0

    #     regional_gen = commute_gen.regional_gen_from_msoarea(super_area="south")

    #     assert regional_gen == regional_gen_1

    def test__load_from_file__uses_correct_values_from_configs(self):
        commute_gen = c.CommuteGenerator.from_file(test_data_filename)

        assert isinstance(commute_gen, c.CommuteGenerator)

        regional_generators = commute_gen.regional_generators
        assert len(regional_generators) == 8802
