import pandas as pd
from june import paths

raw_path = paths.data_path  
processed_path = paths.data_path / "input/hospitals/"

hospitals_df = pd.read_csv(raw_path / "hospital_data/option1_trusts.csv") 
area_translation_df = pd.read_csv(raw_path / 'census_data/area_code_translations/areas_mapping.csv')
area_translation_df = area_translation_df[['postcode','oa', 'msoa']]
area_translation_df.set_index('postcode', inplace=True)
postcodes_coord = pd.read_csv(raw_path / 'geographical_data/ukpostcodes_coordinates.csv')
postcodes_coord.set_index('postcode', inplace=True)
hospitals_df = hospitals_df[['Code', 'Regular beds', 'Intensive care beds (MV+ITU+IDU)', 'Postcode']]
hospitals_df.set_index('Postcode', inplace=True)
hospitals_df.columns = ['code', 'beds', 'icu_beds']

hospitals_df = hospitals_df.join(area_translation_df)
hospitals_df.columns = ['code', 'beds', 'icu_beds', 'area', 'super_area']
hospitals_df = hospitals_df.join(postcodes_coord)
hospitals_df.set_index('super_area', inplace=True)
hospitals_df.to_csv(processed_path / 'trusts.csv')

