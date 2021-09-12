import h5py
import numpy as np
from collections import defaultdict

from june.groups import ExternalGroup, ExternalSubgroup
from june.geography import (
    Geography,
    Area,
    SuperArea,
    Areas,
    SuperAreas,
    Region,
    Regions,
)
from .utils import read_dataset
from june.world import World

nan_integer = -999
int_vlen_type = h5py.vlen_dtype(np.dtype("int64"))
str_vlen_type = h5py.vlen_dtype(np.dtype("S40"))

spec_to_supergroup_mapper = {
    "pub": "pubs",
    "cinema": "cinemas",
    "grocery": "groceries",
    "gym": "gyms",
}


def save_geography_to_hdf5(geography: Geography, file_path: str):
    """
    Saves the households object to hdf5 format file ``file_path``. Currently for each person,
    the following values are stored:
    - id, n_beds, n_icu_beds, super_area, coordinates

    Parameters
    ----------
    companies
        population object
    file_path
        path of the saved hdf5 file
    chunk_size
        number of people to save at a time. Note that they have to be copied to be saved,
        so keep the number below 1e6.
    """
    n_areas = len(geography.areas)
    area_ids = []
    area_names = []
    area_super_areas = []
    area_coordinates = []
    area_socioeconomic_indices = []
    n_super_areas = len(geography.super_areas)
    super_area_ids = []
    super_area_names = []
    super_area_coordinates = []
    super_area_regions = []
    closest_hospitals_ids = []
    closest_hospitals_super_areas = []
    hospital_lengths = []
    social_venues_specs_list = []
    social_venues_ids_list = []
    social_venues_super_areas = []
    social_venues_lengths = []
    super_area_city = []
    super_area_closest_stations_cities = []
    super_area_closest_stations_stations = []
    super_area_closest_stations_lengths = []
    super_area_n_people = []
    super_area_n_workers = []
    super_area_n_pupils = []
    n_regions = len(geography.regions)
    region_ids = []
    region_names = []

    for area in geography.areas:
        area_ids.append(area.id)
        area_super_areas.append(area.super_area.id)
        area_names.append(area.name.encode("ascii", "ignore"))
        area_coordinates.append(np.array(area.coordinates, dtype=np.float64))
        area_socioeconomic_indices.append(area.socioeconomic_index)
        social_venues_ids = []
        social_venues_specs = []
        social_venues_sas = []
        for spec in area.social_venues.keys():
            for social_venue in area.social_venues[spec]:
                social_venues_specs.append(spec.encode("ascii", "ignore"))
                social_venues_ids.append(social_venue.id)
                social_venues_sas.append(social_venue.super_area.id)
        social_venues_specs_list.append(np.array(social_venues_specs, dtype="S20"))
        social_venues_ids_list.append(np.array(social_venues_ids, dtype=np.int64))
        social_venues_super_areas.append(np.array(social_venues_sas, dtype=np.int64))
        social_venues_lengths.append(len(social_venues_specs))
    if len(np.unique(social_venues_lengths)) == 1:
        social_venues_specs_list = np.array(social_venues_specs_list, dtype="S20")
        social_venues_ids_list = np.array(social_venues_ids_list, dtype=np.int64)
        social_venues_super_areas = np.array(social_venues_super_areas, dtype=np.int64)
    else:
        social_venues_specs_list = np.array(
            social_venues_specs_list, dtype=str_vlen_type
        )
        social_venues_ids_list = np.array(social_venues_ids_list, dtype=int_vlen_type)
        social_venues_super_areas = np.array(
            social_venues_super_areas, dtype=int_vlen_type
        )

    for super_area in geography.super_areas:
        super_area_ids.append(super_area.id)
        super_area_names.append(super_area.name.encode("ascii", "ignore"))
        super_area_regions.append(super_area.region.id)
        super_area_coordinates.append(np.array(super_area.coordinates))
        super_area_n_people.append(len(super_area.people))
        super_area_n_workers.append(len(super_area.workers))
        super_area_n_pupils.append(
            sum([len(school.people) for area in super_area.areas for school in area.schools])
        )
        if super_area.closest_hospitals is None:
            closest_hospitals_ids.append(np.array([nan_integer], dtype=np.int64))
            closest_hospitals_super_areas.append(np.array([nan_integer], dtype=np.int64))
            hospital_lengths.append(1)
        else:
            hospital_ids = np.array(
                [hospital.id for hospital in super_area.closest_hospitals], dtype=np.int64
            )
            hospital_sas = np.array(
                [hospital.super_area.id for hospital in super_area.closest_hospitals],
                dtype=np.int64,
            )
            closest_hospitals_ids.append(hospital_ids)
            closest_hospitals_super_areas.append(hospital_sas)
            hospital_lengths.append(len(hospital_ids))
        if super_area.city is None:
            super_area_city.append(nan_integer)
        else:
            super_area_city.append(super_area.city.id)

        for region in geography.regions:
            region_ids.append(region.id)
            region_names.append(region.name)
        cities = []
        stations = []
        for key, value in super_area.closest_inter_city_station_for_city.items():
            cities.append(key.encode("ascii", "ignore"))
            stations.append(value.id)
        super_area_closest_stations_cities.append(cities)
        super_area_closest_stations_stations.append(stations)
        super_area_closest_stations_lengths.append(
            len(super_area.closest_inter_city_station_for_city)
        )

    area_ids = np.array(area_ids, dtype=np.int64)
    area_names = np.array(area_names, dtype="S20")
    area_super_areas = np.array(area_super_areas, dtype=np.int64)
    area_coordinates = np.array(area_coordinates, dtype=np.float64)
    area_socioeconomic_indices = np.array(area_socioeconomic_indices, dtype=np.float64)
    super_area_ids = np.array(super_area_ids, dtype=np.int64)
    super_area_names = np.array(super_area_names, dtype="S20")
    super_area_coordinates = np.array(super_area_coordinates, dtype=np.float64)
    super_area_regions = np.array(super_area_regions, dtype=np.int64)
    super_area_n_people = np.array(super_area_n_people, dtype=np.int64)
    super_area_n_workers = np.array(super_area_n_workers, dtype=np.int64)
    super_area_n_pupils = np.array(super_area_n_pupils, dtype=np.int64)
    region_ids = np.array(region_ids, dtype=np.int64)
    region_names = np.array(region_names, dtype="S50")
    if len(np.unique(hospital_lengths)) == 1:
        closest_hospitals_ids = np.array(closest_hospitals_ids, dtype=np.int64)
        closest_hospitals_super_areas = np.array(
            closest_hospitals_super_areas, dtype=np.int64
        )
    else:
        closest_hospitals_ids = np.array(closest_hospitals_ids, dtype=int_vlen_type)
        closest_hospitals_super_areas = np.array(
            closest_hospitals_super_areas, dtype=int_vlen_type
        )
    super_area_city = np.array(super_area_city, dtype=np.int64)
    if len(np.unique(super_area_closest_stations_lengths)) == 1:
        super_area_closest_stations_cities = np.array(
            super_area_closest_stations_cities, dtype="S40"
        )
        super_area_closest_stations_stations = np.array(
            super_area_closest_stations_stations, dtype=np.int64
        )
    else:
        super_area_closest_stations_cities = np.array(
            super_area_closest_stations_cities, dtype=str_vlen_type
        )
        super_area_closest_stations_stations = np.array(
            super_area_closest_stations_stations, dtype=int_vlen_type
        )

    with h5py.File(file_path, "a") as f:
        geography_dset = f.create_group("geography")
        geography_dset.attrs["n_areas"] = n_areas
        geography_dset.attrs["n_super_areas"] = n_super_areas
        geography_dset.attrs["n_regions"] = n_regions
        geography_dset.create_dataset("area_id", data=area_ids)
        geography_dset.create_dataset("area_name", data=area_names)
        geography_dset.create_dataset("area_super_area", data=area_super_areas)
        geography_dset.create_dataset("area_coordinates", data=area_coordinates)
        geography_dset.create_dataset(
            "area_socioeconomic_indices", data=area_socioeconomic_indices
        )
        geography_dset.create_dataset("super_area_id", data=super_area_ids)
        geography_dset.create_dataset("super_area_name", data=super_area_names)
        geography_dset.create_dataset("super_area_region", data=super_area_regions)
        geography_dset.create_dataset("super_area_city", data=super_area_city)
        geography_dset.create_dataset("super_area_n_people", data=super_area_n_people)
        geography_dset.create_dataset("super_area_n_workers", data=super_area_n_workers)
        geography_dset.create_dataset("super_area_n_pupils", data=super_area_n_pupils)
        geography_dset.create_dataset(
            "super_area_closest_stations_cities",
            data=super_area_closest_stations_cities,
        )
        geography_dset.create_dataset(
            "super_area_closest_stations_stations",
            data=super_area_closest_stations_stations,
        )
        geography_dset.create_dataset(
            "super_area_coordinates", data=super_area_coordinates
        )
        geography_dset.create_dataset(
            "closest_hospitals_ids", data=closest_hospitals_ids
        )
        geography_dset.create_dataset(
            "closest_hospitals_super_areas", data=closest_hospitals_super_areas
        )
        geography_dset.create_dataset("region_id", data=region_ids)
        geography_dset.create_dataset("region_name", data=region_names)
        if social_venues_specs and social_venues_ids:
            geography_dset.create_dataset(
                "social_venues_specs",
                data=social_venues_specs_list,
            )
            geography_dset.create_dataset(
                "social_venues_ids",
                data=social_venues_ids_list,
            )
            geography_dset.create_dataset(
                "social_venues_super_areas",
                data=social_venues_super_areas,
            )


def load_geography_from_hdf5(file_path: str, chunk_size=50000, domain_super_areas=None):
    """
    Loads geography from an hdf5 file located at ``file_path``.
    Note that this object will not be ready to use, as the links to
    object instances of other classes need to be restored first.
    This function should be rarely be called oustide world.py
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        geography = f["geography"]
        n_areas = geography.attrs["n_areas"]
        area_list = []
        n_super_areas = geography.attrs["n_super_areas"]
        n_regions = geography.attrs["n_regions"]
        # areas
        n_chunks = int(np.ceil(n_areas / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_areas)
            length = idx2 - idx1
            area_ids = read_dataset(geography["area_id"], index1=idx1, index2=idx2)
            area_names = read_dataset(geography["area_name"], index1=idx1, index2=idx2)
            area_coordinates = read_dataset(geography["area_coordinates"], idx1, idx2)
            area_socioeconomic_indices = read_dataset(
                geography["area_socioeconomic_indices"], idx1, idx2
            )
            area_super_areas = read_dataset(geography["area_super_area"], idx1, idx2)
            for k in range(length):
                if domain_super_areas is not None:
                    super_area = area_super_areas[k]
                    if super_area == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area not in domain_super_areas:
                        continue
                area = Area(
                    name=area_names[k].decode(),
                    super_area=None,
                    coordinates=area_coordinates[k],
                    socioeconomic_index=area_socioeconomic_indices[k],
                )
                area.id = area_ids[k]
                area_list.append(area)
        # super areas
        super_area_list = []
        domain_regions = set()
        n_chunks = int(np.ceil(n_super_areas / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_super_areas)
            length = idx2 - idx1
            super_area_ids = read_dataset(geography["super_area_id"], idx1, idx2)
            super_area_names = read_dataset(geography["super_area_name"], idx1, idx2)
            super_area_regions = read_dataset(
                geography["super_area_region"], idx1, idx2
            )
            super_area_coordinates = read_dataset(
                geography["super_area_coordinates"], idx1, idx2
            )
            for k in range(idx2 - idx1):
                if domain_super_areas is not None:
                    super_area_id = super_area_ids[k]
                    if super_area_id == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area_id not in domain_super_areas:
                        continue
                super_area = SuperArea(
                    name=super_area_names[k].decode(),
                    areas=None,
                    coordinates=super_area_coordinates[k],
                )
                super_area.id = super_area_ids[k]
                super_area_list.append(super_area)
                domain_regions.add(super_area_regions[k])
        # regions
        region_list = []
        n_chunks = int(np.ceil(n_regions / chunk_size))
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_regions)
            length = idx2 - idx1
            region_ids = read_dataset(geography["region_id"], idx1, idx2)
            region_names = read_dataset(geography["region_name"], idx1, idx2)
            for k in range(idx2 - idx1):
                if domain_super_areas is not None:
                    region_id = region_ids[k]
                    if region_id == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones regions."
                        )
                    if region_id not in domain_regions:
                        continue
                region = Region(
                    name=region_names[k].decode(),
                    super_areas=None,
                )
                region.id = region_ids[k]
                region_list.append(region)

    areas = Areas(area_list)
    super_areas = SuperAreas(super_area_list)
    regions = Regions(region_list)
    return Geography(areas, super_areas, regions)


def restore_geography_properties_from_hdf5(
    world: World,
    file_path: str,
    chunk_size,
    domain_super_areas=None,
    super_areas_to_domain_dict: dict = None,
):
    """
    Long function to restore geographic attributes to the world's geography.
    The closest hospitals, commuting cities, stations, and social venues are restored
    to areas and super areas. For the cases that the super areas would be outside the
    simulated domain, the instances of cities,stations, etc. are substituted by
    external groups, which point to the domain where they are at.
    """
    with h5py.File(file_path, "r", libver="latest", swmr=True) as f:
        geography = f["geography"]
        n_areas = geography.attrs["n_areas"]
        n_chunks = int(np.ceil(n_areas / chunk_size))
        # areas
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_areas)
            length = idx2 - idx1
            areas_ids = read_dataset(geography["area_id"], idx1, idx2)
            super_areas = read_dataset(geography["area_super_area"], idx1, idx2)
            if "social_venues_specs" in geography and "social_venues_ids" in geography:
                social_venues_specs = read_dataset(
                    geography["social_venues_specs"], idx1, idx2
                )
                social_venues_ids = read_dataset(
                    geography["social_venues_ids"], idx1, idx2
                )
                # TODO:
                social_venues_super_areas = read_dataset(
                    geography["social_venues_super_areas"], idx1, idx2
                )
            for k in range(length):
                if domain_super_areas is not None:
                    super_area_id = super_areas[k]
                    if super_area_id == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area_id not in domain_super_areas:
                        continue
                super_area = world.super_areas.get_from_id(super_areas[k])
                area = world.areas.get_from_id(areas_ids[k])
                area.super_area = super_area
                area.super_area.areas.append(area)
                # social venues
                area.social_venues = defaultdict(tuple)
                if (
                    "social_venues_specs" in geography
                    and "social_venues_ids" in geography
                ):
                    for group_spec, group_id, group_super_area in zip(
                        social_venues_specs[k],
                        social_venues_ids[k],
                        social_venues_super_areas[k],
                    ):
                        spec = group_spec.decode()
                        spec_mapped = spec_to_supergroup_mapper[spec]
                        supergroup = getattr(world, spec_mapped)
                        if (
                            domain_super_areas is not None
                            and group_super_area not in domain_super_areas
                        ):

                            domain_of_group = super_areas_to_domain_dict[
                                group_super_area
                            ]
                            group = ExternalGroup(
                                id=group_id,
                                domain_id=domain_of_group,
                                spec=spec,
                            )
                        else:
                            group = supergroup.get_from_id(group_id)
                        area.social_venues[spec] = (
                            *area.social_venues[spec],
                            group,
                        )
        n_super_areas = geography.attrs["n_super_areas"]
        n_chunks = int(np.ceil(n_super_areas / chunk_size))
        # areas
        for chunk in range(n_chunks):
            idx1 = chunk * chunk_size
            idx2 = min((chunk + 1) * chunk_size, n_super_areas)
            length = idx2 - idx1
            super_area_ids = read_dataset(
                geography["super_area_id"], index1=idx1, index2=idx2
            )
            regions = read_dataset(
                geography["super_area_region"], index1=idx1, index2=idx2
            )
            for k in range(length):
                if domain_super_areas is not None:
                    super_area_id = super_area_ids[k]
                    if super_area_id == nan_integer:
                        raise ValueError(
                            "if ``domain_super_areas`` is True, I expect not Nones super areas."
                        )
                    if super_area_id not in domain_super_areas:
                        continue
                super_area = world.super_areas.get_from_id(super_area_ids[k])
                region = world.regions.get_from_id(regions[k])
                super_area.region = region
                region.super_areas.append(super_area)
