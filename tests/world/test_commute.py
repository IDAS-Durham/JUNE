from pathlib import Path

import pytest

from covid import commute as c

data_filename = Path(__file__).parent.parent / "test_data/commute.csv"


@pytest.fixture(name="commute_generator")
def make_commute_generator():
    return c.CommuteGenerator.from_file(data_filename)


@pytest.fixture(name="msoarea")
def make_msoarea():
    return "E00062207"


@pytest.fixture(name="regional_generator")
def make_regional_generator(commute_generator, msoarea):
    return commute_generator.for_msoarea(msoarea)


class TestModeOfTransport:

    def test__setup_with_a_description__check_the_index_is_computed_via_the_index_method(self):

        mode_of_transport = c.ModeOfTransport(description="hello")

        assert mode_of_transport.description == "hello"

        index = mode_of_transport.index(headers=["hi", "hello", "whatsup"])

        assert index == 1

        with pytest.raises(AssertionError):
            mode_of_transport.index(headers=["hi", "hel2lo"])

    def test__equality_override__asserting_to_description_gives_true_else_false(self):

        mode_of_transport = c.ModeOfTransport(description="hello")

        assert mode_of_transport == "hello"

    def test__load_from_file__uses_correct_values_from_default_configs_file(self):

        modes_of_transport = c.ModeOfTransport.load_from_file()
        assert len(modes_of_transport) == 12
        assert "Work mainly at or from home" in modes_of_transport
        assert c.ModeOfTransport.load_from_file()[0] is modes_of_transport[0]


class TestRegionalGenerator:

    def test__total_property__gives_number_of_people_using_all_transports__is_sum_of_people_for_each_transport(self):

        weighted_modes = [(2, c.ModeOfTransport("car"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.total == 2

        weighted_modes = [(2, c.ModeOfTransport("car")), (4, c.ModeOfTransport("bus")), (1, c.ModeOfTransport("magic_carpet"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.total == 7

    def test__modes_property__gives_list_of_all_input_transports(self):

        weighted_modes = [(2, c.ModeOfTransport("car"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.modes == ["car"]

        weighted_modes = [(2, c.ModeOfTransport("car")), (4, c.ModeOfTransport("bus")), (1, c.ModeOfTransport("magic_carpet"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.modes == ["car", "bus", "magic_carpet"]

    def test__weights_property__gives_list_of_total_people_in_each_transport_divided_by_total_people_overall(self):

        weighted_modes = [(2, c.ModeOfTransport("car"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.weights == [1]

        weighted_modes = [(2, c.ModeOfTransport("car")), (4, c.ModeOfTransport("bus")), (1, c.ModeOfTransport("magic_carpet"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.weights == [2/7, 4/7, 1/7]

    def test__weighted_random_choice_property__chooses_a_random_value_from_the_modes(self):

        weighted_modes = [(2, c.ModeOfTransport("car"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.weighted_random_choice() == "car"

        weighted_modes = [(2, c.ModeOfTransport("car")), (4, c.ModeOfTransport("bus")), (1, c.ModeOfTransport("magic_carpet"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.weighted_random_choice() == "car" or "bus" or "magic_carpet"

    def test__weighted_random_choice_property__if_transports_have_zero_people_they_are_not_selected(self):

        weighted_modes = [(0, c.ModeOfTransport("car")), (4, c.ModeOfTransport("bus")), (0, c.ModeOfTransport("magic_carpet"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.weighted_random_choice() == "bus"
        assert regional_gen.weighted_random_choice() == "bus"
        assert regional_gen.weighted_random_choice() == "bus"


def test_load(commute_generator):
    assert isinstance(commute_generator, c.CommuteGenerator)

    regional_generators = commute_generator.regional_generators
    assert len(regional_generators) == 8802


def test_regional_generators(regional_generator, msoarea):

    print(regional_generator.weighted_modes)
    print(regional_generator.total)

    assert regional_generator.msoarea == msoarea


def test_weighted_modes(regional_generator):
    weighted_modes = regional_generator.weighted_modes
    assert len(regional_generator.weighted_modes) == 12

    weighted_mode = weighted_modes[0]
    assert weighted_mode[0] == 15
    assert weighted_mode[1] == "Work mainly at or from home"


def test_weights(regional_generator):
    assert regional_generator.total == 180

    weights = regional_generator.weights
    assert len(weights) == 12
    assert sum(weights) == pytest.approx(1.0)


def test_weighted_random_choice(regional_generator):
    result = regional_generator.weighted_random_choice()
    assert isinstance(result, c.ModeOfTransport)

