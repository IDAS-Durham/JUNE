import pytest
import numpy as np

from june.utils import (
    parse_age_probabilities,
    parse_prevalence_comorbidities_in_reference_population,
)

from june.epidemiology.infection import Covid19, B117, ImmunitySetter
from june.demography import Person, Population
from june.geography import Area, SuperArea, Region
from june.records import Record, RecordReader
from june import World


@pytest.fixture(name="susceptibility_dict")
def make_susc():
    return {
        Covid19.infection_id(): {"0-13": 0.5, "13-100": 1.0},
        B117.infection_id(): {"20-40": 0.25},
    }


class TestSusceptibilitySetter:
    def test__susceptibility_parser(self, susceptibility_dict):
        susc_setter = ImmunitySetter(susceptibility_dict)
        susceptibilities_parsed = susc_setter.susceptibility_dict
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()
        for i in range(0, 100):
            if i < 13:
                assert susceptibilities_parsed[c19_id][i] == 0.5
            else:
                assert susceptibilities_parsed[c19_id][i] == 1.0
            if i < 20:
                assert susceptibilities_parsed[b117_id][i] == 1.0
            elif i < 40:
                assert susceptibilities_parsed[b117_id][i] == 0.25
            else:
                assert susceptibilities_parsed[b117_id][i] == 1.0

    def test__susceptiblity_setter_avg(self, susceptibility_dict):
        population = Population([])
        for i in range(105):
            population.add(Person.from_attributes(age=i))

        susceptibility_setter = ImmunitySetter(susceptibility_dict)
        susceptibility_setter.set_susceptibilities(population)
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()

        for person in population:
            if person.age < 13:
                assert person.immunity.get_susceptibility(c19_id) == 0.5
            else:
                assert person.immunity.get_susceptibility(c19_id) == 1.0
            if person.age < 20:
                assert person.immunity.get_susceptibility(b117_id) == 1.0
            elif person.age < 40:
                assert person.immunity.get_susceptibility(b117_id) == 0.25
            else:
                assert person.immunity.get_susceptibility(b117_id) == 1.0

    def test__susceptiblity_setter_individual(self, susceptibility_dict):
        population = Population([])
        for i in range(105):
            for j in range(10):
                population.add(Person.from_attributes(age=i))

        susceptibility_setter = ImmunitySetter(
            susceptibility_dict, susceptibility_mode="individual"
        )
        susceptibility_setter.set_susceptibilities(population)
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()
        immune_c19_13 = 0
        immune_b117_13 = 0
        immune_40 = 0
        for person in population:
            if person.age < 13:
                if person.immunity.get_susceptibility(c19_id) == 0.0:
                    immune_c19_13 += 1
                if person.immunity.get_susceptibility(b117_id) == 0.0:
                    immune_b117_13 += 1
            if person.age < 20:
                assert person.immunity.get_susceptibility(b117_id) == 1.0
            elif person.age < 40:
                if person.immunity.get_susceptibility(b117_id) == 0.0:
                    immune_40 += 1
            else:
                assert person.immunity.get_susceptibility(b117_id) == 1.0
        aged_13 = len([person for person in population if person.age < 13])
        aged_40 = len([person for person in population if 20 <= person.age < 40])
        assert np.isclose(immune_c19_13 / aged_13, 0.5, rtol=1e-1)
        assert immune_b117_13 == 0
        assert np.isclose(immune_40 / aged_40, 0.75, rtol=1e-1)


@pytest.fixture(name="multiplier_dict")
def make_multiplier():
    return {
        Covid19.infection_id(): 1.0,
        B117.infection_id(): 1.5,
    }


class TestMultiplierSetter:
    def test__multiplier_variants_setter(self, multiplier_dict):
        population = Population([])
        for i in range(105):
            population.add(Person.from_attributes(age=i))

        multiplier_setter = ImmunitySetter(multiplier_dict=multiplier_dict)
        multiplier_setter.set_multipliers(population)
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()

        for person in population:
            assert person.immunity.get_effective_multiplier(c19_id) == 1.0
            assert person.immunity.get_effective_multiplier(b117_id) == 1.5

    def test__mean_multiplier_reference(
        self,
    ):
        prevalence_reference_population = {
            "feo": {
                "f": {"0-10": 0.2, "10-100": 0.4},
                "m": {"0-10": 0.6, "10-100": 0.5},
            },
            "guapo": {
                "f": {"0-10": 0.1, "10-100": 0.1},
                "m": {"0-10": 0.05, "10-100": 0.2},
            },
            "no_condition": {
                "f": {"0-10": 0.7, "10-100": 0.5},
                "m": {"0-10": 0.35, "10-100": 0.3},
            },
        }
        comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_condition": 1.0}
        multiplier_setter = ImmunitySetter(
            multiplier_by_comorbidity=comorbidity_multipliers,
            comorbidity_prevalence_reference_population=prevalence_reference_population,
        )
        dummy = Person.from_attributes(
            sex="f",
            age=40,
        )
        mean_multiplier_uk = (
            prevalence_reference_population["feo"]["f"]["10-100"]
            * comorbidity_multipliers["feo"]
            + prevalence_reference_population["guapo"]["f"]["10-100"]
            * comorbidity_multipliers["guapo"]
            + prevalence_reference_population["no_condition"]["f"]["10-100"]
            * comorbidity_multipliers["no_condition"]
        )
        assert (
            multiplier_setter.get_multiplier_from_reference_prevalence(
                dummy.age, dummy.sex
            )
            == mean_multiplier_uk
        )

    def test__interaction_changes_multiplier(
        self,
    ):
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()
        comorbidity_multipliers = {"guapo": 0.8, "feo": 1.2, "no_condition": 1.0}
        population = Population([])
        for comorbidity in comorbidity_multipliers.keys():
            population.add(Person.from_attributes(age=40, comorbidity=comorbidity))
        for person in population:
            assert person.immunity.get_effective_multiplier(c19_id) == 1.0
            assert person.immunity.get_effective_multiplier(b117_id) == 1.0
        comorbidity_prevalence_reference_population = {
            "guapo": {
                "f": {"0-100": 0.0},
                "m": {"0-100": 0.0},
            },
            "feo": {
                "f": {"0-100": 0.0},
                "m": {"0-100": 0.0},
            },
            "no_condition": {
                "m": {"0-100": 1.0},
                "f": {"0-100": 1.0},
            },
        }

        multiplier_setter = ImmunitySetter(
            multiplier_by_comorbidity=comorbidity_multipliers,
            comorbidity_prevalence_reference_population=comorbidity_prevalence_reference_population,
        )
        multiplier_setter.set_multipliers(population)
        assert population[0].immunity.effective_multiplier_dict[c19_id] == 0.8
        assert population[0].immunity.effective_multiplier_dict[b117_id] == 1.3

        assert population[1].immunity.effective_multiplier_dict[c19_id] == 1.2
        assert population[1].immunity.effective_multiplier_dict[b117_id] == 1.7

        assert population[2].immunity.effective_multiplier_dict[c19_id] == 1.0
        assert population[2].immunity.effective_multiplier_dict[b117_id] == 1.5


class TestVaccinationSetter:
    @pytest.fixture(name="vaccination_dict")
    def make_vacc(self):
        return {
            "pfizer": {
                "percentage_vaccinated": {"0-50": 0.7, "50-100": 1.0},
                "infections": {
                    Covid19.infection_id(): {
                        "sterilisation_efficacy": {"0-100": 0.5},
                        "symptomatic_efficacy": {"0-100": 0.5},
                    },
                },
            },
            "sputnik": {
                "percentage_vaccinated": {"0-30": 0.3, "30-100": 0.0},
                "infections": {
                    B117.infection_id(): {
                        "sterilisation_efficacy": {"0-100": 0.8},
                        "symptomatic_efficacy": {"0-100": 0.8},
                    },
                },
            },
        }

    def test__vaccination_parser(self, vaccination_dict):
        susc_setter = ImmunitySetter(vaccination_dict=vaccination_dict)
        vp = susc_setter.vaccination_dict
        c19_id = Covid19.infection_id()
        b117_id = B117.infection_id()
        for age in range(0, 100):
            # pfizer
            if age < 50:
                assert vp["pfizer"]["percentage_vaccinated"][age] == 0.7
            else:
                assert vp["pfizer"]["percentage_vaccinated"][age] == 1.0
            assert (
                vp["pfizer"]["infections"][Covid19.infection_id()][
                    "sterilisation_efficacy"
                ][age]
                == 0.5
            )
            assert (
                vp["pfizer"]["infections"][Covid19.infection_id()][
                    "symptomatic_efficacy"
                ][age]
                == 0.5
            )

            # sputnik
            if age < 30:
                assert vp["sputnik"]["percentage_vaccinated"][age] == 0.3
            else:
                assert vp["sputnik"]["percentage_vaccinated"][age] == 0.0
            assert (
                vp["sputnik"]["infections"][B117.infection_id()][
                    "sterilisation_efficacy"
                ][age]
                == 0.8
            )
            assert (
                vp["sputnik"]["infections"][B117.infection_id()][
                    "symptomatic_efficacy"
                ][age]
                == 0.8
            )

    def test__set_pre_vaccinations(self, vaccination_dict):
        population = Population([])
        for i in range(100):
            for _ in range(200):
                population.add(Person.from_attributes(age=i))
        immunity = ImmunitySetter(vaccination_dict=vaccination_dict)
        immunity.set_vaccinations(population)
        under50_pfizer = 0
        under50_pfizer_not = 0
        over50_pfizer = 0
        over50_pfizer_not = 0
        under30_sputnik = 0
        under30_sputnik_not = 0
        b117id = B117.infection_id()
        c19id = Covid19.infection_id()
        for person in population:
            if person.age < 30:
                if b117id in person.immunity.susceptibility_dict:
                    assert np.isclose(person.immunity.get_susceptibility(b117id), 0.2)
                    under30_sputnik += 1
                if b117id in person.immunity.effective_multiplier_dict:
                    assert (
                        pytest.approx(person.immunity.get_effective_multiplier(b117id))
                        == 0.2
                    )
                    under30_sputnik_not += 1
            if person.age > 30:
                if b117id in person.immunity.susceptibility_dict:
                    assert False
                if b117id in person.immunity.effective_multiplier_dict:
                    assert False

            if person.age < 50:
                if c19id in person.immunity.susceptibility_dict:
                    assert person.immunity.get_susceptibility(c19id) == 0.5
                    under50_pfizer += 1
                if c19id in person.immunity.effective_multiplier_dict:
                    under50_pfizer_not += 1
                    assert person.immunity.get_effective_multiplier(c19id) == 0.5
            else:
                if c19id in person.immunity.susceptibility_dict:
                    assert person.immunity.get_susceptibility(c19id) == 0.5
                    over50_pfizer += 1
                if c19id in person.immunity.effective_multiplier_dict:
                    over50_pfizer_not += 1
                    assert person.immunity.get_effective_multiplier(c19id) == 0.5

        under30 = len([person for person in population if person.age < 30])
        over30 = len([person for person in population if person.age >= 30])
        under50 = len([person for person in population if person.age < 50])
        over50 = len([person for person in population if person.age >= 50])
        assert np.isclose(under30_sputnik / under30, 0.3, rtol=1e-1)
        assert np.isclose(under30_sputnik_not / under30, 0.3, rtol=1e-1)
        assert np.isclose(under50_pfizer / under50, 0.7, rtol=1e-1)
        assert np.isclose(under50_pfizer_not / under50, 0.7, rtol=1e-1)
        assert np.isclose(over50_pfizer / over50, 1, rtol=1e-1)
        assert np.isclose(over50_pfizer_not / over50, 1, rtol=1e-1)

    def test__set_save_vaccine_type_record(self):
        vaccination_dict = {
            "sputnik": {
                "percentage_vaccinated": {"0-30": 1.0, "30-100": 0.0},
                "infections": {
                    B117.infection_id(): {
                        "sterilisation_efficacy": {"0-100": 0.8},
                        "symptomatic_efficacy": {"0-100": 0.8},
                    },
                },
            }
        }
        record = Record(record_path="results/", record_static_data=True)
        population = Population([])
        world = World()
        world.people = population

        for i in range(100):
            for _ in range(200):
                population.add(Person.from_attributes(age=i))
        immunity = ImmunitySetter(vaccination_dict=vaccination_dict, record=record)
        immunity.set_vaccinations(population)
        record.static_data(world=world)

        record_reader = RecordReader()
        people_df = record_reader.table_to_df("population")
        for id, row in people_df.iterrows():
            if row["age"] < 30:
                assert row["vaccine_type"] == "sputnik"
            else:
                assert row["vaccine_type"] == "none"


class TestPreviousInfectionSetter:
    @pytest.fixture(name="previous_infections_dict")
    def make_prev_inf_dict(self):
        dd = {
            "infections": {
                Covid19.infection_id(): {
                    "sterilisation_efficacy": 0.5,
                    "symptomatic_efficacy": 0.6,
                },
                B117.infection_id(): {
                    "sterilisation_efficacy": 0.2,
                    "symptomatic_efficacy": 0.3,
                },
            },
            "ratios": {
                "London": {"0-50": 0.5, "50-100": 0.2},
                "North East": {"0-70": 0.3, "70-100": 0.8},
            },
        }
        return dd

    def test__setting_prev_infections(self, previous_infections_dict):
        ne = Region(name="North East")
        ne_super_area = SuperArea(region=ne)
        ne_area = Area(super_area=ne_super_area)

        london = Region(name="London")
        london_super_area = SuperArea(region=london)
        london_area = Area(super_area=london_super_area)

        population = Population([])
        for area in [ne_area, london_area]:
            for age in range(100):
                for _ in range(100):
                    p = Person.from_attributes(age=age)
                    p.area = area
                    population.add(p)
        immunity = ImmunitySetter(previous_infections_dict=previous_infections_dict)
        immunity.set_previous_infections(population)
        vaccinated = {"London" : {1: 0, 2 : 0} , "North East" : {1: 0, 2: 0}}
        vaccinated_london = 0
        vaccinated_ne = 0
        for person in population:
            c19_susc = person.immunity.get_susceptibility(Covid19.infection_id())
            b117_susc = person.immunity.get_susceptibility(B117.infection_id())
            if c19_susc < 1.0:
                assert c19_susc == 0.5
                if person.region.name == "London":
                    if person.age < 50:
                        vaccinated[person.region.name][1] += 1
                    else:
                        vaccinated[person.region.name][2] += 1
                else:
                    if person.age < 70:
                        vaccinated[person.region.name][1] += 1
                    else:
                        vaccinated[person.region.name][2] += 1
            if b117_susc < 1.0:
                assert b117_susc == 0.8

        people_london1 = len([person for person in population if person.region.name == "London" if person.age < 50])
        people_london2 = len([person for person in population if person.region.name == "London" if person.age >= 50])
        people_ne1 = len([person for person in population if person.region.name == "North East" if person.age < 70])
        people_ne2 = len([person for person in population if person.region.name == "North East" if person.age >= 70])
        assert np.isclose(vaccinated["London"][1] / people_london1, 0.5, rtol=0.1)
        assert np.isclose(vaccinated["London"][2] / people_london2, 0.2, rtol=0.1)
        assert np.isclose(vaccinated["North East"][1] / people_ne1, 0.3, rtol=0.1)
        assert np.isclose(vaccinated["North East"][2] / people_ne2, 0.8, rtol=0.1)
