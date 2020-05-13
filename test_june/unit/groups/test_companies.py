import os
from pathlib import Path

import pytest

from june.demography.geography import Geography
from june.demography import Person
from june.groups import Company, Companies


default_data_path = Path(os.path.abspath(__file__)).parent.parent.parent.parent / \
    "data/processed/census_data/company_data/"
default_size_nr_file = default_data_path / "companysize_msoa11cd_2019.csv"
default_sector_nr_per_msoa_file = default_data_path / "companysector_msoa11cd_2011.csv"


@pytest.fixture(name="super_area_companies", scope="module")
def super_area_name():
    return "E02002559"

@pytest.fixture(name="geography_companies", scope="module")
def create_geography(super_area_companies):
    return Geography.from_file(filter_key={"msoa" : [super_area_companies]})

@pytest.fixture(name="person")
def create_person():
    return Person(sex="m", age=44)


class TestCompany:
    @pytest.fixture(name="company")
    def create_company(self, super_area_companies):
        return Company(
            super_area = super_area_companies,
            n_employees_max = 115,
            industry = "Q",
        )
    
    def test__company_grouptype(self, company):
        assert company.GroupType.workers == 0

    def test__empty_company(self, company):
        assert bool(company.GroupType.workers) is False
    
    def test__filling_company(self, person, company):
        company.add(person, Company.GroupType.workers)
        assert bool(company.subgroups[0].people) is True

    def test__person_is_employed(self, person, company):
        company.add(person, Company.GroupType.workers)
        assert person.company.id == company.id

class TestCompanies:
    def test__creating_companies_from_file(self, super_area_companies):
        schools = Companies.from_file(
            area_names = [super_area_companies],
            size_nr_file = default_size_nr_file,
            sector_nr_per_superarea_file = default_sector_nr_per_msoa_file,
        )
    
    def test_creating_schools_for_areas(self, super_area_companies):
        schools = Companies.for_super_areas([super_area_companies])

    @pytest.fixture(name="companies", scope="module")
    def test__creating_companies_for_geography(self, geography_companies):
        return Companies.for_geography(geography_companies)

    def test__companies_nr_for_geography(self, companies):
        print(len(companies.members))
        assert len(companies) == 610
