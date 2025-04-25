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

    #get muni boundary + buffer
    #muni_gdf = ma_towns.loc[ma_towns['TOWN'].str.casefold() == town_name.casefold()].to_crs(mass_mainland_crs)
    #muni_gdf_w_buffer = buffer_gdf(muni_gdf, 800)


    #### CRITERIA 1: Basic Conformity ####

    ## PREPROCESSING ## 

    #create the zoning layer
    res_zoning = get_zoning_data(town_name)

    muni_w_zoning = muni_parcels.sjoin(res_zoning, how = "inner")



    ## RUN INDICATOR SCORING ## 

    land_use_criteria = muni_w_zoning

    # units
    def label_units (row):
        if row[units] > row['MAXDU']: #original max_du
            return 1
        else:
            return 0
        
    land_use_criteria['du_conf'] = land_use_criteria.apply(lambda row: 
                                                     label_units(row), 
                                                     axis=1) #its a row

    # allowed uses
    luc_res_type = {
                'Single Residence' : {'101': True},
                'Multi-Residence District' : {'101' : True, 
                                       '104': True},
                'Business District' : {'013': True},
                'Mixed-Use' : {'105': True,
                                 '111': True,
                                 '112': True,
                                 '013': True}
                                 }
    
    # converts the condominiums to a land use code that resembles the allowed use
    land_use_criteria['luc_test'] = land_use_criteria.apply(lambda row:condo_conversion(luc = row[luc_adjusted],
                                                                                         units = row[units]),
                                                                                         axis = 1)
    
    print(land_use_criteria['luc_test'][1])

    def lu_dict_test (res_type, luc) :
        if luc not in  luc_res_type[res_type].keys():
            return 1
        elif luc_res_type[res_type][luc] == True:
            return 0
        else:
            return 1 

    land_use_criteria['lu_conf'] = land_use_criteria.apply(lambda row: 
                                                       lu_dict_test(res_type= row['ZO_AldUse'], #original: zo_use_type
                                                                    luc = row['luc_test']), 
                                                                    axis = 1)
    
    # min lot size
    def label_lotsize (row):
        if row['LOT_SIZE'] > row['MINLOTSIZE']: #original min_lot_area. All in SF. Do i need to change to LOTSIZE GIS ? 
            return 0
        else:
            return 1
        
    land_use_criteria['ls_conf'] =  muni_w_zoning.apply(lambda row: 
                                                     label_lotsize(row), 
                                                     axis=1) #its a row
    
    ## CRITERIA SCORING ## 
    #### while we only have 3 indicators we're going to treat each of them as criteria and run the final score 
    # land_use_criteria = get_criteria_score(criteria_table=land_use_criteria, 
    #                                             weights=lu_weights,
    #                                             criteria_name='conf_scr')
   
    conformity_scores = get_final_score(final_suitability_table= land_use_criteria,
                                       weights= lu_weights,
                                        suitability_name = "conf"
                                       )
    return conformity_scores
