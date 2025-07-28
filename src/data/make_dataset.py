# -*- coding: utf-8 -*-
import geopandas as gpd
import os
import pandas as pd

from src.features.nested_functions import agol_to_gdf, get_gdf_from_zipped_link

#directory locations
datasets_dir = r'K:\DataServices\Datasets'
projects_dir = 'K:\\DataServices\\Projects\\Current_Projects'


#define variables
id_field = 'LOC_ID'
mass_mainland_crs = "EPSG:26986"

#once land parcel database is updated, update this file path. 
#needs to be a folder path where the folder contains a list of CSVs with town names
mapc_lpd_folder = os.path.join(datasets_dir, 'Parcel_DB\Data\LPDB_Municipal_Data\current')

bldg_val_p_sf = 'BLDGV_PSF'
bldg_land_value_ratio = 'BLDLND_RAT'
yr_built = 'YEAR_BUILT'
luc_adjusted = 'Min_LUC_Assign'
bldg_val = 'BLDG_VAL'
units = 'imputed_units'
far = 'FAR'
lu_description = 'L3_Description_M'

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


# boston_parcels_fp = os.path.join(projects_dir, r"PDAs_PPAs\I90_PPA_PDA\Data\boston_parcels\Parcels_(2024)\Parcels_(2024).shp")
# boston_parcels = gpd.read_file(boston_parcels_fp)

#excluded land 
excluded_land_gdb = os.path.join(projects_dir, "Housing\\Section_3A\\Analytical_Toolbox\\Project_Files\\3A_atlas_maps\\Default.gdb")
#excluded_land = gpd.read_file(excluded_land_gdb, layer='MAPC_ExcludedCombined_bytown_2')

# Zoning
zoning_gdb = os.path.join(datasets_dir, r"Zoning and Land Use\Town_Zoning\ZoningData\zoning_gdb.gdb")
zoning_layer = gpd.read_file(zoning_gdb, layer = 'mmc_zoning')

# ## TRANSIT ACCESSIBILITY ##

# #transit stations
# #combine mbta, commuter rail, and bus stops
# mbta_url = 'https://arcgisserver.digital.mass.gov/arcgisserver/rest/services/AGOL/MBTA_Rapid_Transit/FeatureServer/1'
# mbta_stops = agol_to_gdf(mbta_url)

# comm_rail_url = 'https://arcgisserver.digital.mass.gov/arcgisserver/rest/services/AGOL/MBTA_Commuter_Rail/FeatureServer/0'
# comm_rail_stations = agol_to_gdf(comm_rail_url)

# bus_stops_url = 'https://arcgisserver.digital.mass.gov/arcgisserver/rest/services/AGOL/MBTA_Bus/FeatureServer/2'
# bus_stops = agol_to_gdf(bus_stops_url)

# #commuter rail walkshed
# #look at mit raw data, if desired
# # walkshed_network_fp = os.path.join(projects_dir, 'Housing\\Section_3A\\Analytical_Toolbox\\Project_Files\\Walkshed_Bikeshed_MIT\\Polygons_w_Scenarios\\walk_NETWORK_POLYGON_w_data.shp')
# # walkshed_network = gpd.read_file(walkshed_network_fp)

# #number of jobs within 45 minutes by transit - switch to datasets later, not sure why it's erroring
# transit_data_raw = r"K:\DataServices\Datasets\Transportation\UMN_accessibility_observatory\2021\merged_shp\2021_MAPC_CT_45min.shp"
# jobs_within_45_mins_transit = gpd.read_file(transit_data_raw)
# jobs_count_field = 'wgtd_avg'

# #non auto commuter share of total commuters
# nonauto_fp = os.path.join(projects_dir, 'Housing\\Section_3A\\Analytical_Toolbox\\Project_Files\\commuting\\nonauto_commuters.shp')
# nonauto = gpd.read_file(nonauto_fp)
# nonauto_field = 'nonauto_p'

# ## WALKABLE COMMUNITIES ##

# #pedestrian facilities, read in w muni mask  in scripts
# ped_facilities_fp = os.path.join(datasets_dir, "Transportation\MassDOT\MassDOT_pedestrianfacilities\Pedestrian_Facilities.shp")

# #school walkshed, read in w muni mask in scripts
# school_walkshed_fp = os.path.join(projects_dir, "Digital_Projects\\MySchoolCommute_Website\\Output\\MA_SRTS_GridIndexIntensity.shp")

# #walkscore, read in w muni mask in scripts
# walkscore_fp = os.path.join(datasets_dir, "Transportation\\WalkScore\\Walkscore_grid.shp")

# #town centers
# town_center_fp = os.path.join(projects_dir, "Housing\\Section_3A\\Analytical_Toolbox\\Project_Files\\City_TownCenters\\city_towncenters.shp")
# town_center = gpd.read_file(town_center_fp)

# #bike facilities
# bike_facilities_url = 'https://datacommon.mapc.org/shapefile?table=gisdata.mapc.trans_bike_facilities&database=gisdata'
# bike_facilities = get_gdf_from_zipped_link(url=bike_facilities_url, 
#                                            topic='bike')

# #shared use trails
# shared_use_trails_url = 'https://datacommon.mapc.org/shapefile?table=gisdata.mapc.trans_shared_use_paths&database=gisdata'
# shared_use_trails = get_gdf_from_zipped_link(url=shared_use_trails_url, 
#                                            topic='trails')

# #walking trails
# walking_trails_url = 'https://datacommon.mapc.org/shapefile?table=gisdata.mapc.trans_walking_trails&database=gisdata'
# walking_trails = get_gdf_from_zipped_link(url=walking_trails_url,
#                                           topic='walking')

# #major roads
# major_roads_gdb = os.path.join(projects_dir, 'PDAs_PPAs\I90_PPA_PDA\Data\massdot_roads\MassDOT_Roads.gdb')

# ## DEVELOPMENT FEASIBILITY ## 
# #datasets

# #retail sites
# retail_sites_fp = os.path.join(projects_dir, "Housing\Section_3A\Analytical_Toolbox\Project_Files\Retrofitting Suburbia\export-gisdata.mapc.rethinking_retail_sites.shp")
# retail_sites = gpd.read_file(retail_sites_fp)

# #historic sites
# ##filtered to include only important designations (from https://mapc365.sharepoint.com/:w:/s/ArtsandCulture/EWPpsFj5mx1KogCRzE6Zt0wBDm9hod9GDIXrfH1-zBen0g?rtime=uXOpbckY20g)
# historic_sites_fp = os.path.join(projects_dir, "Housing\\Section_3A\\Analytical_Toolbox\\Project_Files\\3A_atlas_maps\\Default.gdb")
# historic_sites = gpd.read_file(historic_sites_fp, layer='MHCHistoricInv_Selection')


# ## FLOOD RISK ## 

# #fema
# fema_nfhl_fp = os.path.join(projects_dir, "PDAs_PPAs\\I90_PPA_PDA\\Data\\nfhl\\FEMA_NFHL_POLY.shp")

# #mcfrm
# mcfrm_fp = os.path.join(datasets_dir, "Environment and Energy\MCFRM\Extent_1pct\Extent_1pct_2pt4ftslr.shp")

# #wellhead protection areas
# zone2_wpa_fp = os.path.join(datasets_dir, 'Environment and Energy\Wellhead_Protection_Areas\ZONE2_POLY.shp')
# zone2_wpa = gpd.read_file(zone2_wpa_fp)

# mcfrm_town_names = [
#             'HULL', 'COHASSET', 'HINGHAM', 'SCITUATE', 'BRAINTREE', 'ARLINGTON', 'BELMONT', 
#             'BEVERLY', 'BOSTON', 'BRAINTREE', 'BROOKLINE', 'CAMBRIDGE', 'CHELSEA', 'DANVERS',
#             'DUXBURY', 'ESSEX', 'EVERETT', 'GLOUCESTER', 'HANOVER', 'HINGHAM', 'IPSWICH', 
#             'LYNN', 'MALDEN', 'MANCHESTER', 'MARSHFIELD', 'MEDFORD', 'MILTON', 'NEWTON', 
#             'NORWELL', 'PEABODY', 'PEMBROKE', 'QUINCY', 'REVERE', 'ROCKPORT', 'SALEM', 'SAUGUS',
#             'SCITUATE', 'SOMERVILLE', 'SWAMPSCOTT', 'WATERTOWN', 'WEYMOUTH', 'WINCHESTER', 'WINTHROP'
#             ]


# ## FAVORABLE DEV ##

# #census block groups
# census_bg_fp = os.path.join(datasets_dir, "U.S. Census and Demographics\\Census 2020\\Data\\Processed\\Spatial\\bg20_2010xw_shp\\bg20_2010xw.shp")
# census_bg = gpd.read_file(census_bg_fp)


# census_bl_fp = os.path.join(datasets_dir, "U.S. Census and Demographics\\Census 2020\\Data\\Processed\\Spatial\\bl20_2010xw_shp\\bl20_2010xw.shp")
# census_bl = gpd.read_file(census_bl_fp)


# #census tract
# census_ct_fp = os.path.join(datasets_dir, "U.S. Census and Demographics\\Census 2020\\Data\\Processed\\Spatial\\ct20_2010xw_shp\\ct20_2010xw.shp")
# census_ct = gpd.read_file(census_ct_fp)

# #heat
# heat_fp = os.path.join(datasets_dir, "Environment and Energy\Land_Surface_Temperature\Shapefile_LSTIndex\LSTindex.tif")


# #read in labor force data
# labor_force_fp = os.path.join(projects_dir, "PDAs_PPAs\I90_PPA_PDA\Data\laborforce\laborforce_ct_acs_2018_2022.csv")
# labor_force = pd.read_csv(labor_force_fp)
# labor_force['ct20_id'] = labor_force['ct20_id'].astype(str)



# #business density: derived from notebooks/00-pda-ppa-pre-work.ipynb
# business_density_fp = os.path.join(projects_dir, "PDAs_PPAs\\I90_PPA_PDA\\Data\\business_density\\2023_data_axle_density.shp")

# #spatialize
# labor_force_gdf = census_ct.merge(labor_force, on='ct20_id')


# ## HABITAT ## 

# ## BIOMAP2 - CORE HABITAT ## 
# aquatic_core_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\biomap\\BM3_CH_AQUATIC_CORE.shp')
# wetland_core_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\biomap\\BM3_CH_WETLAND_CORE.shp')
# priority_natural_communities_core_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\biomap\\BM3_CH_PRIORITY_NATURAL_COMMS.shp')
# forest_core_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\biomap\\BM3_CH_FOREST_CORE.shp')
# vernalpool_core_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\biomap\\BM3_CH_VERNAL_POOLS_CORE.shp')
# rarespecies_core_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\biomap\\BM3_CH_RARE_SPECIES_CORE.shp')

# #put together
# core_habitat_components = [aquatic_core_fp, wetland_core_fp, priority_natural_communities_core_fp,
#                     vernalpool_core_fp, rarespecies_core_fp, forest_core_fp]


# ## BIOMAP2 - CRITICAL NATURAL LANDSCAPES ## 
# aquatic_core__buffer_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\biomap\\BM3_CNL_AQUATIC_BUFFER.shp')
# coastal_adapt_buffer_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\biomap\\BM3_CNL_COASTAL_ADAPT.shp')
# wetland_core_buffer_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\biomap\\BM3_CNL_WETLAND_BUFFER.shp')
# tern_foraging_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\biomap\\BM3_CNL_TERN_FORAGING.shp')
# landscape_blocks_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\biomap\\BM3_CNL_LANDSCAPE_BLOCKS.shp')

# #put together 
# critical_nat_landscapes_components = [aquatic_core__buffer_fp, coastal_adapt_buffer_fp, wetland_core_buffer_fp,
#                                         tern_foraging_fp, landscape_blocks_fp]


# #prime forest land
# prime_forest_land_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\primeforest\\PRIMEFOREST_POLY.shp')


# #certified vernal pools
# cvp_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\certified_vernal_pools\\GISDATA_CVP_PTPoint.shp')
# cvp = gpd.read_file(cvp_fp)

# #river protection zones - streams (ARC_CODE=4) from Hydro25K, buffered to 150ft
# hydro_25k_fp = os.path.join(datasets_dir, 'hydro25k_201704\HYDRO25K_ARC.shp')

# #protected open space
# open_space_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\openspace\\OPENSPACE_POLY.shp')

# #primary habitat of rare species
# rare_species_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\primaryhabitatsofrarespecies\\PRIHAB_POLY.shp')
# nhesp_rare_species = gpd.read_file(rare_species_fp)

# #outstanding resource waters
# outstanding_resource_waters_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\outstandingwaterresources\\ORW_POLY.shp')
# outstanding_resource_waters = gpd.read_file(outstanding_resource_waters_fp)

# #DRINKING WATER PROTECTION 

# #interim wpa
# interim_wpa_fp = os.path.join(projects_dir, 'PDAs_PPAs\\I90_PPA_PDA\\Data\\wellheadprotection\\IWPA_POLY.shp')
# interim_wpa = gpd.read_file(interim_wpa_fp)

# #sole source aquifers
# sole_source_aquifers_fp = os.path.join(projects_dir, 'PDAs_PPAs\I90_PPA_PDA\Data\solesourceaquifers\AQSOLE_POLY.shp')
# sole_source_aquifers = gpd.read_file(sole_source_aquifers_fp)

# #surface water protection areas
# swp_zones_fp = os.path.join(projects_dir, 'PDAs_PPAs\I90_PPA_PDA\Data\surfacewaterprotectionareas\SWP_ZONES_POLY.shp')

# #drinkwing water supply
# water_supply_fp = os.path.join(projects_dir, "PDAs_PPAs\I90_PPA_PDA\Data\publicwatersupplies\PWSDEP_PT.shp")
# water_supply = gpd.read_file(water_supply_fp)

# ## PRESERVING FARMLAND ##

# lclu_gdb = os.path.join(datasets_dir, "MassGIS\LULC_2016\MA_LCLU2016.gdb")
# soils_fp = os.path.join(projects_dir, "PDAs_PPAs\I90_PPA_PDA\Data\soils\SOILS_MUPOLYGON_TOP20.shp")

# ## UNFAVORABLE DEV ## 
# wetlands_fp = os.path.join(projects_dir, "PDAs_PPAs\I90_PPA_PDA\Data\wetlands\wetlandsdep\WETLANDSDEP_POLY.shp")

# acec_fp = os.path.join(projects_dir, "PDAs_PPAs\\I90_PPA_PDA\\Data\\acecs\\acecs_poly.shp")
# acec = gpd.read_file(acec_fp)

# CRWA_gdb  = os.path.join(projects_dir, 'Environment\\Stormwater_Flooding_Analysis\\ProjectFiles\CRWA_models.gdb')
# charles_model = gpd.read_file(CRWA_gdb, layer='charles_model_2070_10yr')


# ## OPEN SPACE AND REC DATASETS
# ## DATA INPUTS (move to make_dataset.py) ## 

# parkserve_gdb = os.path.join(projects_dir, r"PDAs_PPAs\I90_PPA_PDA\Data\parkserve\Parkserve_Download_2024.gdb")

# #ej
# ej_fp = os.path.join(projects_dir, r"PDAs_PPAs\I90_PPA_PDA\Data\ej2020\EJ_POLY.shp")
# ej = gpd.read_file(ej_fp)

#ejscreen for air pollution data
# ejscreen_gdb = os.path.join(projects_dir, r'PDAs_PPAs\I90_PPA_PDA\Data\ejscreen\EJScreen_2024_BG_StatePct_with_AS_CNMI_GU_VI.gdb')
