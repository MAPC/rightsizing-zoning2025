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
def run_zoning_nonconformity(town_name, zone_type, score = True):
    '''
    runs zoning_nonconformity analysis

    Scores closer to 1: More non-conformity
    Scores closer to 0: Closer to zoning conformity
    
    '''
    #get most updated parcels from muni, combine with MAPC land parcel database

    muni_parcels = get_landuse_data(town_name)
    
    ## For Test Report
    og_parcels = len(set(muni_parcels['LOC_ID']))

    # Calculate necessary fields 
    muni_parcels['DUA'] = muni_parcels[units]/(muni_parcels['LOT_SIZE_GIS']/43560)
    muni_parcels['LPU'] = (muni_parcels['LOT_SIZE_GIS']/43560)/muni_parcels[units]

    #Joining Building Data from LIDAR 
    ldr_bld['ftpt_area'] = ldr_bld.area
    ldr_bld_join = ldr_bld[['LOC_ID_bld', 'MEDIAN', 'MEDIAN_stories', 'ftpt_area']]
    #outer join for footprint so we don't lose parcels that don't have one? 
    muni_parcels = structure_merge(ldr_bld_join, muni_parcels)
    muni_parcels['floors'] = round(muni_parcels['MEDIAN_stories']*4)/4 #rounds to quarter story baed on median height
    muni_parcels['height'] = muni_parcels['MEDIAN']*3.8084
    #moving the filter around
    muni_parcels = muni_parcels[muni_parcels[units]> 2]

    ## For Test Report
    bld_parcels = len(set(muni_parcels['LOC_ID']))

    ## will soon join in key fields from LIDAR analysis
        # Height
        # Floors (if sloped roof subtract 0.5 from floors?)
        # Gross Floor Area? 

    #get muni boundary + buffer
    #muni_gdf = ma_towns.loc[ma_towns['TOWN'].str.casefold() == town_name.casefold()].to_crs(mass_mainland_crs)
    #muni_gdf_w_buffer = buffer_gdf(muni_gdf, 800)

    ## PREPROCESSING ## 

    #create the zoning layer
    res_zoning = get_zoning_data(town_name, type = zone_type)

    ## For Test Report
    og_zones = len(set(res_zoning['ZO_CODE']))
    #print("Number of Zones")
    #print(og_zones)

    muni_w_zoning = zoning_merge(zoning_gdf= res_zoning,
                                 parcels_gdf= muni_parcels)
    
    ## For Test Report
    zj_parcels = len(set(muni_w_zoning['LOC_ID']))
    #print("Parcels with Zoning" )
    #print(zj_parcels)
    no_zone_parcels = len(set(muni_w_zoning[muni_w_zoning['ZO_CODE'].isna()]['LOC_ID']))
    #print("Parcels without Zoning")
    #print(no_zone_parcels)
    
    # building foot print geometry
    bld_footprint = ldr_bld[ldr_bld['CITY'] == town_name]


    #### CRITERIA 1: Parcel Size ####

    # Min Lot Size
    # Percent Lot Coverage
    # Land Area Per Unit

    ## RUN INDICATOR SCORING ## 

    parcel_size_criteria = muni_w_zoning

    # min lot size
    def label_lotsize (row):
        if np.isnan(row['MINLOTSIZE']):
            return np.nan
        elif row['LOT_SIZE'] > row['MINLOTSIZE']: #original min_lot_area. All in SF. Do i need to change to LOTSIZE GIS ? 
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
    
    ## For Test Report 
    ovlp_parcels = len(set(parcel_size_criteria['LOC_ID']))


    # return 1 if there is more building than the regulated percent lot coverage allows
    def label_lotcov (row):
        if np.isnan(row['PCTLOTCOV']):
            return np.nan
        elif row['par_lot_cov_pct']*100 > row['PCTLOTCOV']:
            return 1
        else: 
            return 0
         
        
    parcel_size_criteria['lc_conf'] = parcel_size_criteria.apply(lambda row:
                                                                 label_lotcov(row),
                                                                 axis = 1)

    # Land area Per dwelling unit
    def label_lapdu (row):
        if np.isnan(row['LApDU']):
            return np.nan
        elif row['LPU']< row['LApDU']:
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

    # Allowed Residetnial Use
    # Height/Floors (Including sloped roofs)
    # Gross Floor Area

    blg_shape_criteria = parcel_size_criteria

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
    #print(blg_shape_criteria[blg_shape_criteria['luc_test'].isna()]['LOC_ID'])
    #print(blg_shape_criteria['luc_test'][1])

    def lu_dict_test (LOC_ID, res_type, luc) :
        #print(LOC_ID, luc, res_type)
        if res_type == 'No Residential Uses Allowed' and (luc.startswith("1") or luc == "013") :
            return 1 
        elif res_type == 'No Residential Uses Allowed':
            return np.nan
        elif luc not in luc_res_type[res_type].keys():
            return 1
        elif luc_res_type[res_type][luc] == True:
            return 0
        else:
            return 1 

    print(set(blg_shape_criteria['luc_test']))
    blg_shape_criteria['lu_conf'] = blg_shape_criteria.apply(lambda row: 
                                                       lu_dict_test(res_type= row['ZO_AldUse'], #original: zo_use_type
                                                                    luc = row['luc_test'],
                                                                    LOC_ID= row["LOC_ID"]), 
                                                                    axis = 1)
    
    # Gross Floor Area
    def label_gfa (row):
        if np.isnan(row['MAX_GFA']):
            return np.nan
        elif row['BLD_AREA'] > row['MAX_GFA']:
            return 1
        else: 
            return 0
        
    blg_shape_criteria['gfa_conf'] = blg_shape_criteria.apply(lambda row:
                                                                 label_gfa(row),
                                                                 axis = 1)
    # Height of Structure
    def label_height (row):
        if np.isnan(row['MAXHEIGHT']):
            return np.nan
        elif row['height'] > row['MAXHEIGHT']:
            return 1
        else: 
            return 0
        
    blg_shape_criteria['ht_conf'] = blg_shape_criteria.apply(lambda row:
                                                                 label_height(row),
                                                                 axis = 1)
    
     # Estimated Stories of Structure
    def label_stories (row):
        if np.isnan(row['MAXFLRS']):
            return np.nan
        elif row['floors'] > row['MAXFLRS']:
            return 1
        else: 
            return 0
        
    blg_shape_criteria['fl_conf'] = blg_shape_criteria.apply(lambda row:
                                                                 label_stories(row),
                                                                 axis = 1)
    
    #FAR Confomrity
    def label_far (row):
        if np.isnan(row['FAR']):
            return np.nan
        elif row['MAXFAR'] > row['FAR']:
            return 1
        else: 
            return 0
    
    blg_shape_criteria['far_conf'] = blg_shape_criteria.apply(lambda row:
                                                                  label_far(row),
                                                                  axis = 1)
    
    ## Criteria Scoring ## 
    
    blg_shape_criteria = get_criteria_score(criteria_table = blg_shape_criteria,
                                              weights = c2_weights,
                                              criteria_name = 'blg_shpe')
    

    
     #### CRITERIA 3: Residential Density ####

    # Total Dwelling Units
    # Dwelling Units per Acre
    # FAR

    density_criteria = blg_shape_criteria
    ## Indicator Scoring ##
    # units
    def label_units (row):
        if np.isnan(row['MAXDU']):
            return np.nan
        elif row[units] > row['MAXDU']: #original max_du
            return 1
        else:
            return 0
        
    density_criteria['du_conf'] = density_criteria.apply(lambda row: 
                                                     label_units(row), 
                                                     axis=1) #its a row

    # dua
    def label_dua (row):
        if np.isnan(row['DUpAC']):
            return np.nan
        elif row['DUA'] > row['DUpAC']: 
            return 1
        else:
            return 0
        
    density_criteria['dua_conf'] = density_criteria.apply(lambda row: 
                                                     label_dua(row), 
                                                     axis=1)
    

    ## CRITERIA SCORING ## 
    density_criteria = get_criteria_score(criteria_table=density_criteria, 
                                                weights=c3_weights,
                                                criteria_name='res_dnsy')
   
    conformity_scores = get_final_score(final_suitability_table= density_criteria,
                                       weights= cr_weights,
                                        suitability_name = "conf"
                                       )
    
    ## For Test Report
    ot_parcels = len(set(conformity_scores['LOC_ID']))
    output_zones = len(set(conformity_scores['ZO_CODE']))
    
    all_conf_fields = ['ls_conf', 'lc_conf', 'ld_conf', 'lu_conf', 'fl_conf', 'ht_conf', 'gfa_conf', 'du_conf', 'dua_conf', 'far_conf']

    conformity_scores['size_sum'] = conformity_scores[['ls_conf', 'lc_conf', 'ld_conf']].sum(axis = 1)
    conformity_scores['shape_sum'] = conformity_scores[['lu_conf', 'fl_conf', 'ht_conf', 'gfa_conf', 'far_conf']].sum(axis = 1)
    conformity_scores['dense_sum'] = conformity_scores[['du_conf', 'dua_conf' ]].sum(axis = 1)
    conformity_scores['size_count'] = conformity_scores[['ls_conf', 'lc_conf', 'ld_conf']].count(axis = 1)
    conformity_scores['shape_count'] = conformity_scores[['lu_conf', 'fl_conf', 'ht_conf', 'gfa_conf', 'far_conf']].count(axis = 1)
    conformity_scores['dense_count'] = conformity_scores[['du_conf', 'dua_conf' ]].count(axis = 1)
    conformity_scores['Total'] = conformity_scores[['size_sum', 'shape_sum', 'dense_sum']].sum(axis = 1)
    conformity_scores['Measures'] = conformity_scores[all_conf_fields].count(axis = 1)
 
    if score == True:
        return conformity_scores
    else:
        analysis_report = {
            'Test': ['Original Parcel Count', 'LIDAR Join Parcel Count', 'Zoning Join Parcel Count', 'Overlap Test Parcels', 'Output Parcel Count','Parcels without Zoning', 'Original Zones', 'Zones in Parcel Output'],
            'Value': [og_parcels, bld_parcels, zj_parcels,  ovlp_parcels, ot_parcels, no_zone_parcels, og_zones, output_zones]}
        
        analysis_report = pd.DataFrame(analysis_report)
        return analysis_report

#def run_zoning_district_scoring():
def test_merge(town_name, zone_type):

    muni_parcels = get_landuse_data(town_name)
    ldr_bld['ftpt_area'] = ldr_bld.area
    ldr_bld_join = ldr_bld[['LOC_ID_bld', 'MEDIAN', 'MEDIAN_stories', 'ftpt_area']]
    #outer join for footprint so we don't lose parcels that don't have one? 
    muni_parcels = structure_merge(ldr_bld_join, muni_parcels)
    muni_parcels = muni_parcels[muni_parcels[units]> 2]

    res_zoning = get_zoning_data(town_name, type = zone_type)
    print(set(res_zoning['ZO_AldUse']))
    muni_w_zoning = zoning_merge(zoning_gdf= res_zoning,
                                 parcels_gdf= muni_parcels)
    
    print("LOCIDs of Parcels without Zoning")
    print(set(muni_w_zoning[muni_w_zoning['ZO_CODE'].isna()]['LOC_ID']))
    allowed_uses = set(muni_w_zoning['ZO_AldUse'])

    print(allowed_uses)

    return muni_w_zoning

    # if len(allowed_uses == True )>0 :
    #     print("Missing Allowed Use")
    # else :
    #     print ("Allowed Uses All Good")


def analysis_outputs(town_name):

    # base_zone_summary = readzonesummary
    # overlay_zone_summary = readzonesummary
    # parcel_summary = readparceloutputs
    #1 Which Zoning Standards lead to the most non-conformity?
    #analysis_1 = #normalize average non-conformity?

    #2 Difference between base zoning and overlay
    #analysis_2 = #overlay base and overlay, do math on scores base-overlay, average effect of overlay zoning on non-conformity


    # By Right vs Special permit? ?

    #3 Nonconformity Score (total and subcategories) correlation with year built 
    #analysis_3 = df['A'].corr(df['B'])

    #4 Nonconfomirty Score correlation (total and subcategories) with lot size
    #analysis_4 = df['A'].corr(df['B'])

    analysis_output = {
        'Analysis Concept': {'Zoning Standard with most Nonconformity', 'Average Effect of Overlay Zoning', 'Correlation Score: Year Built', 'Correlation Score: Lot Size'},
        'Overall Conformity': {},
        'Lot Size': {},
        'Building Shape': {},
        'Unit Density': {}
    }

    analysis_output = pd.DataFrame(analysis_output)

    return(analysis_output)

def zone_comparisons():

    '''
    Are there any zones that are clearly copy-paste situations? how do their non-conformities compare?

    '''

    print("TBD")



    



