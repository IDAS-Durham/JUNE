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

    def test__load_from_file__uses_correct_values_from_default_configs_file(self):

        modes_of_transport = c.ModeOfTransport.load_from_file()
        assert len(modes_of_transport) == 12
        assert "Work mainly at or from home" in modes_of_transport
        assert c.ModeOfTransport.load_from_file()[0] is modes_of_transport[0]


class TestRegionalGenerator:

    def test__total__sum_of_people_using_all_transports(self):

        weighted_modes = [(2, c.ModeOfTransport("car"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.total == 2

        weighted_modes = [(2, c.ModeOfTransport("car")), (4, c.ModeOfTransport("bus")), (1, c.ModeOfTransport("magic_carpet"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.total == 7

    def test__modes__list_of_all_transports(self):

        weighted_modes = [(2, c.ModeOfTransport("car"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.modes == ["car"]

        weighted_modes = [(2, c.ModeOfTransport("car")), (4, c.ModeOfTransport("bus")), (1, c.ModeOfTransport("magic_carpet"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.modes == ["car", "bus", "magic_carpet"]

    def test__weights__lists_people_per_transport_divided_by_total(self):

        weighted_modes = [(2, c.ModeOfTransport("car"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.weights == [1]

        weighted_modes = [(2, c.ModeOfTransport("car")), (4, c.ModeOfTransport("bus")), (1, c.ModeOfTransport("magic_carpet"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.weights == [2/7, 4/7, 1/7]

    def test__weighted_choice__chooses_random_value_from_the_modes(self):

        weighted_modes = [(2, c.ModeOfTransport("car"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.weighted_random_choice() == "car"

        weighted_modes = [(2, c.ModeOfTransport("car")), (4, c.ModeOfTransport("bus")), (1, c.ModeOfTransport("magic_carpet"))]

        regional_gen = c.RegionalGenerator(msoarea="test_area", weighted_modes=weighted_modes)

        assert regional_gen.weighted_random_choice() == "car" or "bus" or "magic_carpet"

    def test__weighted_choice__cant_choose_transports_with_0_people(self):

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

