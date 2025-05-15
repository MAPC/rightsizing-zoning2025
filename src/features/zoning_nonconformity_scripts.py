#scripts for running various pda and ppa analyses

import geopandas as gpd
import pandas as pd
import numpy as np

import sys
sys.path.append("..")

from src.data.make_dataset import *
from src.features.nested_functions import *
from src.features.indicator_functions import *
from src.features.criteria_functions import *
from src.data.weights import *

########### Zoning Residential
def run_zoning_nonconformity(town_name):
    '''
    runs zoning_nonconformity analysis

    Scores closer to 1: More non-conformity
    Scores closer to 0: Closer to zoning conformity
    
    '''
    #get most updated parcels from muni, combine with MAPC land parcel database

    muni_parcels = get_landuse_data(town_name)

    # Calculate necessary fields 
    muni_parcels['DUA'] = muni_parcels[units]/(muni_parcels['LOT_SIZE_GIS']/43560)
    muni_parcels['LPU'] = (muni_parcels['LOT_SIZE_GIS']/43560)/muni_parcels[units]

    #stop gap for analysis
    muni_parcels['floors'] = -99
    muni_parcels['height'] = -99

    ## will soon join in key fields from LIDAR analysis
        # Height
        # Floors (if sloped roof subtract 0.5 from floors?)
        # Gross Floor Area? 

    #get muni boundary + buffer
    #muni_gdf = ma_towns.loc[ma_towns['TOWN'].str.casefold() == town_name.casefold()].to_crs(mass_mainland_crs)
    #muni_gdf_w_buffer = buffer_gdf(muni_gdf, 800)

    ## PREPROCESSING ## 

    #create the zoning layer
    res_zoning = get_zoning_data(town_name)

    muni_w_zoning = zoning_merge(zoning_gdf= res_zoning,
                                 parcels_gdf= muni_parcels)
    
    # building foot print geometry
    bld_footprint = ldr_bld[ldr_bld['CITY'] == town_name]



    # TO WRITE: Lot Size Unit Check


    #### CRITERIA 1: Parcel Size ####

    # Min Lot Size
    # Percent Lot Coverage
    # Land Area Per Unit

    ## RUN INDICATOR SCORING ## 

    parcel_size_criteria = muni_w_zoning

    # min lot size
    def label_lotsize (row):
        if row['LOT_SIZE'] > row['MINLOTSIZE']: #original min_lot_area. All in SF. Do i need to change to LOTSIZE GIS ? 
            return 0
        else:
            return 1
        
    parcel_size_criteria['ls_conf'] =  muni_w_zoning.apply(lambda row: 
                                                     label_lotsize(row), 
                                                     axis=1) #its a row
    
    # pct lot coverage
    # calculate the percent of the parcer covered by the building structures
    parcel_size_criteria = calculate_overlap(layer_1= parcel_size_criteria,
                                                        layer_2 = bld_footprint,
                                                        how = "percent",
                                                        new_field_name = 'par_lot_cov')
    # return 1 if there is more building than the regulated percent lot coverage allows
    def label_lotcov (row):
        if row['par_lot_cov_pct']*100 > row['PCTLOTCOV']:
            return 1
        else: 
            return 0
         
        
    parcel_size_criteria['lc_conf'] = parcel_size_criteria.apply(lambda row:
                                                                 label_lotcov(row),
                                                                 axis = 1)

    # Land area Per dwelling unit
    def label_lapdu (row):
        if row['LPU']< row['LApDU']:
          return 1
        else:
            return 0                     

    parcel_size_criteria['ld_conf'] = parcel_size_criteria.apply(lambda row:
                                                                 label_lapdu(row),
                                                                 axis = 1)

    # parcel size criteria scoring
    parcel_size_criteria = get_criteria_score(criteria_table = parcel_size_criteria,
                                              weights = c1_weights,
                                              criteria_name = 'pcl_size')

     #### CRITERIA 2: Building Shape ####

    blg_shape_criteria = parcel_size_criteria

    # Allowed Residetnial Use
    # Height/Floors (Including sloped roofs)
    # Gross Floor Area

    # allowed uses
    luc_res_type = {
                'Single Family' : {'101': True},
                'Two Family' : {'101' : True, 
                                '104': True},
                'Three Family' : {'101' : True, 
                                '104': True,
                                '105' : True},
                'Four to Eight Units' : {'101' : True, 
                                '104': True,
                                '105' : True,
                                '111': True,
                                '013': True},
                'More than Eight Units' : {'101' : True, 
                                '104': True,
                                '105' : True,
                                '111': True,
                                '112': True,
                                '013': True}
                                 }
    
    # converts the condominiums to a land use code that resembles the allowed use
    blg_shape_criteria['luc_test'] = blg_shape_criteria.apply(lambda row:condo_conversion(luc = row[luc_adjusted],
                                                                                         units = row[units]),
                                                                                         axis = 1)
    
    #print(blg_shape_criteria['luc_test'][1])

    def lu_dict_test (res_type, luc) :
        if res_type == 'No Residential Uses Allowed' and (luc.startswith("1") or luc == "013") :
            return 1 
        elif res_type == 'No Residential Uses Allowed' :
            return 0
        elif luc not in  luc_res_type[res_type].keys():
            return 1
        elif luc_res_type[res_type][luc] == True:
            return 0
        else:
            return 1 

    blg_shape_criteria['lu_conf'] = blg_shape_criteria.apply(lambda row: 
                                                       lu_dict_test(res_type= row['ZO_AldUse'], #original: zo_use_type
                                                                    luc = row['luc_test']), 
                                                                    axis = 1)
    
    # Gross Floor Area
    def label_gfa (row):
        if row['BLD_AREA'] > row['MAX_GFA']:
            return 1
        else: 
            return 0
        
    blg_shape_criteria['gfa_conf'] = blg_shape_criteria.apply(lambda row:
                                                                 label_gfa(row),
                                                                 axis = 1)
    
    def label_height (row):
        if row['height'] > row['MAXHEIGHT']:
            return 1
        else: 
            return 0
        
    blg_shape_criteria['ht_conf'] = blg_shape_criteria.apply(lambda row:
                                                                 label_height(row),
                                                                 axis = 1)
    
    ## Criteria Scoring ## 
    
    blg_shape_criteria = get_criteria_score(criteria_table = blg_shape_criteria,
                                              weights = c2_weights,
                                              criteria_name = 'blg_shpe')
    

    
     #### CRITERIA 3: Residential Density ####

    density_criteria = blg_shape_criteria
    # Total Dwelling Units
    # Dwelling Units per Acre
    # FAR

    ## Indicator Scoring ##
    # units
    def label_units (row):
        if row[units] > row['MAXDU']: #original max_du
            return 1
        else:
            return 0
        
    density_criteria['du_conf'] = density_criteria.apply(lambda row: 
                                                     label_units(row), 
                                                     axis=1) #its a row

    # dua
    def label_dua (row):
        if row['DUA'] > row['DUpAC']: 
            return 1
        else:
            return 0
        
    density_criteria['dua_conf'] = density_criteria.apply(lambda row: 
                                                     label_dua(row), 
                                                     axis=1)
    
    #FAR Confomrity
    def label_far (row):
        if row['MAXFAR'] > row['FAR']:
            return 1
        else: 
            return 0
    
    density_criteria['far_conf'] = density_criteria.apply(lambda row:
                                                                  label_far(row),
                                                                  axis = 1)

    ## CRITERIA SCORING ## 
    density_criteria = get_criteria_score(criteria_table=density_criteria, 
                                                weights=c3_weights,
                                                criteria_name='res_dnsy')
   
    conformity_scores = get_final_score(final_suitability_table= density_criteria,
                                       weights= cr_weights,
                                        suitability_name = "conf"
                                       )
    return conformity_scores

#def run_zoning_district_scoring():
