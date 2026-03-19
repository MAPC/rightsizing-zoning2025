# -*- coding: utf-8 -*-
import geopandas as gpd
import os
import pandas as pd

#directory locations
datasets_dir = r'K:\DataServices\Datasets'
projects_dir = 'K:\\DataServices\\Projects\\Current_Projects'


#define variables
id_field = 'LOC_ID'
mass_mainland_crs = "EPSG:26986"

#once land parcel database is updated, update this file path. 
#needs to be a folder path where the folder contains a list of CSVs with town names
mapc_lpd_folder = os.path.join(datasets_dir, 'Parcel_DB\Data\LPDB.Q2_2025\parcels_by_muni')

bldg_val_p_sf = 'BLDGV_PSF'
bldg_land_value_ratio = 'BLDLND_RAT'
yr_built = 'YEAR_BUILT'
luc_adjusted = 'MIN_LUCA'
bldg_val = 'BLDG_VAL'
#units = 'IMP_UNITS'

far = 'FAR'
lu_description = 'LUC_DES_L'

lidar_path = os.path.join(projects_dir, 'Neighborhood_Planning_and_Zoning\\Zoning_Projects\\Rightsizing_Zoning_2025\\RightsizingZoning_2025.gdb')
#"K:\DataServices\Projects\Current_Projects\Neighborhood_Planning_and_Zoning\Zoning_Projects\Rightsizing_Zoning_2025\RightsizingZoning_2025.gdb"
lidar_layer_name = '_00_mmc_enriched_structures_1'
ldr_bld = gpd.read_file(lidar_path, layer= lidar_layer_name)
ldr_bld = ldr_bld.rename(columns= {'LOC_ID':'LOC_ID_bld'})
#Just the primary structure
ldr_bld = ldr_bld[ldr_bld['primary_structure'] == 1]

# need to move these

ma_towns_fp = os.path.join(projects_dir, r"PDAs_PPAs\I90_PPA_PDA\Data\town_boundary\TOWNSSURVEY_POLYM.shp")
ma_towns = gpd.read_file(ma_towns_fp)

boston_parcels_url = r'https://data.boston.gov/dataset/9ef4ed7e-f35c-4821-a27c-fd38a54a78ce/resource/142a423a-f715-458d-9784-1664541bf389/download/parcels__2024_.zip'
boston_assessors_csv = r'http://data.boston.gov/dataset/e02c44d2-3c64-459c-8fe2-e1ce5f38a035/resource/6b7e460e-33f6-4e61-80bc-1bef2e73ac54/download/fy2025-property-assessment-data_12_30_2024.csv'


# boston_parcels_fp = os.path.join(projects_dir, r"PDAs_PPAs\I90_PPA_PDA\Data\boston_parcels\Parcels_(2024)\Parcels_(2024).shp")
# boston_parcels = gpd.read_file(boston_parcels_fp)

#excluded land 
excluded_land_gdb = os.path.join(projects_dir, "Housing\\Section_3A\\Analytical_Toolbox\\Project_Files\\3A_atlas_maps\\Default.gdb")
#excluded_land = gpd.read_file(excluded_land_gdb, layer='MAPC_ExcludedCombined_bytown_2')

# Zoning
zoning_gdb = os.path.join(datasets_dir, r"Zoning and Land Use\Town_Zoning\ZoningData\zoning_gdb.gdb")
zoning_layer = gpd.read_file(zoning_gdb, layer = 'mmc_zoning')
zoning_overlay_layer = gpd.read_file(zoning_gdb, layer = 'mmc_overlays')

