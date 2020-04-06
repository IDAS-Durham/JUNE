import locale
import numpy as np
import pandas as pd
import json

region = "North East"
region_outlabel = "northeast"

# Load dictionary to translate: RGN -> LAD -> MSOA
dic = pd.read_csv(
    "PCD11_OA11_LSOA11_MSOA11_LAD11_RGN17_FID_EW_LU.csv",
    delimiter=',',
    delim_whitespace=False,
)
dic_sample = dic[["LAD11CD", "RGN17CD", "RGN17NM", "MSOA11CD", "MSOA11NM"]]
dic_sample = dic_sample.drop_duplicates(subset='MSOA11CD')
dic_sample = dic_sample.set_index('MSOA11CD')

# Because of line 570 in epimodel.cpp I need to change the regions ID to the number
# of regions there are
new_RGN17CD = np.arange(len(np.unique(dic_sample["RGN17CD"].values)))
RGN17CD_dict = {}
for c, rgn_id in enumerate(np.unique(dic_sample["RGN17CD"].values)):
    RGN17CD_dict[rgn_id] = new_RGN17CD[c]

new_LAD11CD = np.arange(len(np.unique(dic_sample["LAD11CD"].values)))
LAD11CD_dict = {}
for c, msoa_id in enumerate(np.unique(dic_sample["LAD11CD"].values)):
    LAD11CD_dict[msoa_id] = new_LAD11CD[c]

new_MSOA11CD = np.arange(len(np.unique(dic_sample.index.values)))
MSOA11CD_dict = {}
for c, msoa_id in enumerate(np.unique(dic_sample.index.values)):
    MSOA11CD_dict[msoa_id] = new_MSOA11CD[c]

# Filter areas in selected region
if region == " ":
    # simulate epidemic for the hole of england and wales
    pass
elif region == "North East":
    # simulate epidemic for selected region
    sel_rgn = np.unique(
        dic_sample[dic_sample["RGN17NM"] == "North East"][["RGN17CD", "LAD11CD"]]["RGN17CD"].values
    )
    # select RGN
    RGN17CD_sel_dict = {}
    for rgn in sel_rgn:
        RGN17CD_sel_dict[rgn] = RGN17CD_dict[rgn]
    RGN17CD_dict = RGN17CD_sel_dict
    sel_lad = np.unique(
        dic_sample[dic_sample["RGN17NM"] == "North East"][["RGN17CD", "LAD11CD"]]["LAD11CD"].values
    )
    pd.DataFrame(data=RGN17CD_dict, index=['flute id']).T.to_csv('RGN17CD_dict.csv', index=True)
    # select LAD
    LAD11CD_sel_dict = {}
    for lad in sel_lad:
        LAD11CD_sel_dict[lad] = LAD11CD_dict[lad]
    LAD11CD_dict = LAD11CD_sel_dict
    sel_msoa = dic_sample[dic_sample["RGN17NM"] == "North East"].index.values
    pd.DataFrame(data=LAD11CD_dict, index=['flute id']).T.to_csv('LAD11CD_dict.csv', index=True)
    # select MSOA
    MSOA11CD_sel_dict = {}
    for msoa in sel_msoa:
        MSOA11CD_sel_dict[msoa] = MSOA11CD_dict[msoa]
    MSOA11CD_dict = MSOA11CD_sel_dict
    pd.DataFrame(data=MSOA11CD_dict, index=['flute id']).T.to_csv('MSOA11CD_dict.csv', index=True)

    # rename RNG & LAD
    for key, value in RGN17CD_dict.items():
        dic_sample["RGN17CD"] = dic_sample["RGN17CD"].replace(key, value)
    for key, value in LAD11CD_dict.items():
        dic_sample["LAD11CD"] = dic_sample["LAD11CD"].replace(key, value)

    # filter dictionary
    dic_sample = dic_sample[dic_sample["RGN17NM"] == "North East"]
    dic_sample = dic_sample.drop(['RGN17NM'], axis=1)

# -------------------------------------------------------------------------------
# Tracts file: population estimate
pop = pd.read_csv(
    "population_in_msoa_sape21dt3a_2018.csv",
    skiprows=4,
    delimiter=',',
    delim_whitespace=False,
)
pop = pop[["Area Codes", "MSOA", "All Ages"]]
pop = pop.set_index('Area Codes')
flute_tracts = pop.merge(dic_sample, left_index=True, right_index=True)
flute_tracts = flute_tracts.reset_index()
flute_tracts = flute_tracts[["RGN17CD", "LAD11CD", "index", "All Ages"]]
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8' ) 
flute_tracts["All Ages"] = flute_tracts['All Ages'].apply(lambda x: locale.atoi(x))
flute_tracts = flute_tracts.rename(columns={"All Ages": "population"})
# find lat and lon of MSOA centres
geojson = "Middle_Layer_Super_Output_Areas_December_2011_Population_Weighted_Centroids.geojson"
with open(geojson) as f:
    data = json.load(f)
objects = []
geometry = []
for feature in data['features']:
    objects.append(feature['properties'])  #['properties']['features'])
    geometry.append(feature['geometry']['coordinates'])
obj = pd.DataFrame(objects)
geo = pd.DataFrame(geometry)
geo = geo.rename(columns={0: "lon", 1: "lat"})
geo = obj.join(geo)
geo = geo.set_index('msoa11cd')
geo['lon'] = geo['lon'].apply(lambda x: round(x, 6))
geo['lat'] = geo['lat'].apply(lambda x: round(x, 6))
geo = geo.merge(flute_tracts.set_index('index'), left_index=True, right_index=True)
geo = geo.reset_index()
geo = geo[["RGN17CD", "LAD11CD", "index", "population", "lon", "lat"]]
# replace regions ID with input that FluTe can handle
for key, value in MSOA11CD_dict.items():
    geo["index"] = geo["index"].replace(key, value)
print("test tracts:", geo[geo["population"].isnull()].index)
geo.to_csv(
    "./%s-tracts.dat" % region_outlabel,
    index=False,
    sep=",",
    header=False,
)
del geo, flute_tracts, obj, pop

# -------------------------------------------------------------------------------
# WF file:  work flow commute
flow = pd.read_csv(
    "flow_in_msoa_wu01ew_2011.csv",
    delimiter=',',
    delim_whitespace=False,
    skiprows=1,
    usecols=[0,1,2],
    names=["home_msoa11cd", "work_msoa11cd", "n_people"],
)
# match MSOA of home and work seperatly with LAD and RGN
# first home MSOA
flow = flow.set_index('home_msoa11cd')
#flow = flow.join(dic_sample, how='left', lsuffix='_caller', rsuffix='_other')
flow = flow.merge(dic_sample, left_index=True, right_index=True)
flow = flow.rename(columns={
    "RGN17CD": "home_RGN17CD",
    "LAD11CD": "home_LAD11CD",
})
flow = flow.reset_index()
flow = flow.rename(columns={"index": "home_msoa11cd"})
# second work MSOA
flow = flow.set_index('work_msoa11cd')
#flow = flow.join(dic_sample, how='left', lsuffix='_caller', rsuffix='_other')
flow = flow.merge(dic_sample, left_index=True, right_index=True)
flow = flow.rename(columns={
    "RGN17CD": "work_RGN17CD",
    "LAD11CD": "work_LAD11CD",
})
flow = flow.reset_index()
flow = flow.rename(columns={"index": "work_msoa11cd"})
flow = flow[[
    "home_RGN17CD", "home_LAD11CD", "home_msoa11cd",
    "work_RGN17CD", "work_LAD11CD", "work_msoa11cd",
    "n_people"
]]
flow = flow[~flow["work_RGN17CD"].isna()]
print(len(flow.index.values))
for key, value in MSOA11CD_dict.items():
    flow["home_msoa11cd"] = flow["home_msoa11cd"].replace(key, value)
    flow["work_msoa11cd"] = flow["work_msoa11cd"].replace(key, value)
print("test wf:", flow[flow["n_people"].isnull()].index)
flow = flow.astype('int32')
flow.to_csv(
    "./%s-wf.dat" % region_outlabel,
    index=False,
    sep=" ",
    header=False
)
del flow

# -------------------------------------------------------------------------------
# Employment file
pop = pd.read_csv(
    "population_in_msoa_sape21dt3a_2018.csv",
    skiprows=4,
    delimiter=',',
    delim_whitespace=False,
)
pop = pop.set_index('Area Codes')
msoa11nm = pop["MSOA"]
pop = pop.drop([
    'LA (2019 boundaries)','MSOA',
    'All Ages','0','1','2','3','4','5','6','7','8','9','10','11','12','13','14','15',
    '75','76','77','78','79','80','81','82','83','84','85','86','87','88','89','90+'
], axis=1)
locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
for col in pop.columns:
    pop[col] = pop[col].apply(lambda x: locale.atoi(x))
work_pop = pop.sum(axis=1)
work_pop = pd.concat([msoa11nm, work_pop], axis=1)
work_pop = work_pop.rename(columns={
    0: "n_work_pop",
})
#All usual residents aged 16 to 74 in employment in the area the week before the census
emp = pd.read_csv(
    "employment_status_in_msoa_wp601ew_2011.csv",
    delimiter=',',
    delim_whitespace=False,
)
emp = emp.rename(columns={
    "geography": "msoa11nm",
    "geography code": "msoa11cd",
    "Employment Status: All categories: Employment status; measures: Value": "n_employed",
})
emp = emp[["msoa11nm", "msoa11cd", "n_employed"]]
emp = emp.set_index('msoa11cd')
emp = emp.merge(work_pop, left_index=True, right_index=True)
emp = emp.drop(['MSOA'], axis=1)
# deal with more employees than people
indx = np.where(emp["n_employed"].values > emp["n_work_pop"].values)[0]
values = emp["n_work_pop"].values
values[indx] = emp.iloc[indx]["n_employed"].values
emp["n_work_pop"] = values

emp = emp.merge(dic_sample, left_index=True, right_index=True)
emp = emp.reset_index()
emp = emp[["RGN17CD", "LAD11CD", "index", "n_employed", "n_work_pop"]]
for key, value in MSOA11CD_dict.items():
    emp["index"] = emp["index"].replace(key, value)
print("test employments:", emp[emp["n_employed"].isnull()].index, emp[emp["n_employed"].isnull()].index)
emp.to_csv(
    "./%s-employment.dat" % region_outlabel,
    index=False,
    sep=" ",
    header=False,
)

