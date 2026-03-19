#scripts for running various pda and ppa analyses
import mapc_suitability as mapc
import geopandas as gpd
import pandas as pd
import numpy as np

import sys
sys.path.append("..")

from src.data.make_dataset import *
from src.features.zoning_process_functions import *
#from src.features.indicator_functions import *
#from src.features.criteria_functions import *
#from src.data.weights import *

########### Zoning Residential
def run_zoning_nonconformity(town_name, zone_type, score = True):
    '''
    runs zoning_nonconformity analysis

    Scores closer to 1: More non-conformity
    Scores closer to 0: Closer to zoning conformity
    
    '''
    # function to format the luc
    def strsubset(value, start, end):
       return value[start:end]

    #get most updated parcels from muni, combine with MAPC land parcel database
    muni_parcels = mapc.get_landuse_data(town_name)
    
    muni_parcels = muni_parcels.fillna(value = {
        'MIN_LUC' : "",
        'MAX_LUC' : ""
    })
    
    ## For Test Report
    og_parcels = len(set(muni_parcels['LOC_ID']))
    og_parcels_len = len(muni_parcels['LOC_ID'])


    #moving the filter around
    muni_parcels = muni_parcels[muni_parcels['EST_UNITS']> 2]
    # Fill NAs in MIN_LUCA
    muni_parcels['MIN_LUC2'] = muni_parcels.apply(lambda row: strsubset(value = row['MIN_LUC'],
                                                                       start = 0,
                                                                       end = 3), 
                                                 axis = 1)
    muni_parcels['MAX_LUC2'] = muni_parcels.apply(lambda row: strsubset(value = row['MAX_LUC'],
                                                                       start = 0,
                                                                       end = 3), 
                                                 axis = 1)
    muni_parcels = muni_parcels.fillna(value = {
        'MIN_LUCA': muni_parcels['MIN_LUC2'],
        'MAX_LUCA': muni_parcels['MAX_LUC2']
    })
    
    
    print(type(muni_parcels))
    # remove commercial parcels 
    muni_parcels[luc_adjusted] = muni_parcels[luc_adjusted].str.startswith(("0", "1", "9"))

    # Calculate necessary fields 
    muni_parcels['DUA'] = muni_parcels['EST_UNITS']/(muni_parcels['LOT_SIZE_G']/43560)
    muni_parcels['LPU'] = (muni_parcels['LOT_SIZE_G']/43560)/muni_parcels['EST_UNITS']

    #Joining Building Data from LIDAR
    # building foot print geometry
    
    ldr_bld_muni = ldr_bld[ldr_bld['CITY'] == town_name].copy() #ensures pandas knows this is a new object
    ldr_bld_muni['ftpt_area'] = ldr_bld_muni.area
    # ldr_bld_join = ldr_bld_muni[['LOC_ID_bld', 'MEDIAN', 'MEDIAN_stories', 'ftpt_area']]
    #outer join for footprint so we don't lose parcels that don't have one? 
    muni_parcels = structure_merge(ldr_bld_muni, muni_parcels)
    muni_parcels['floors'] = round(muni_parcels['MEDIAN_stories']*4)/4 #rounds to quarter story baed on median height
    muni_parcels['height'] = muni_parcels['MEDIAN']*3.8084 #meters to feet
   

    ## For Test Report
    bld_parcels = len(set(muni_parcels['LOC_ID']))
    bld_parcels_len = len(muni_parcels['LOC_ID'])

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
    
    if zone_type == "overlay":
        muni_w_zoning = muni_w_zoning.dropna(subset = 'ZO_CODE')
    else:
        muni_w_zoning  = muni_w_zoning

    if len(muni_w_zoning) == 0:
        print("No Multifamily Parcels in Overlay Zones")
        return muni_w_zoning
    else:
        print("Multifamily Parcels Detected in Overlay Zones")
    
    ## For Test Report
    zj_parcels = len(set(muni_w_zoning['LOC_ID']))
    zj_parcels_len = len(muni_w_zoning['LOC_ID'])
    #print("Parcels with Zoning" )
    #print(zj_parcels)
    no_zone_parcels = len(set(muni_w_zoning[muni_w_zoning['ZO_CODE'].isna()]['LOC_ID']))
    #print("Parcels without Zoning")
    #print(no_zone_parcels)
    
    # # building foot print geometry
    # bld_footprint = ldr_bld[ldr_bld['CITY'] == town_name]


    #### CRITERIA 1: Parcel Size ####

    # Min Lot Size
    # Percent Lot Coverage
    # Land Area Per Unit

    ## RUN SCORING ## 

    parcel_size_criteria = muni_w_zoning

    # min lot size
    def label_lotsize (row):
        if np.isnan(row['MINLOTSIZE']):
            return np.nan
        elif row['LOT_SIZE_G'] > row['MINLOTSIZE']: #all in SF
            return 0
        else:
            return 1
        
    parcel_size_criteria['ls_conf'] =  muni_w_zoning.apply(lambda row: 
                                                     label_lotsize(row), 
                                                     axis=1) #its a row
    
    # pct lot coverage
    # calculate the percent of the parcer covered by the building structures
    # parcel_size_criteria = calculate_overlap(layer_1= parcel_size_criteria,
    #                                          layer_2 = ldr_bld_muni,
    #                                          how = "percent",
    #                                          new_field_name = 'par_lot_cov')
    
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
    # parcel_size_criteria = mapc.get_criteria_score(criteria_table = parcel_size_criteria,
    #                                           weights = c1_weights,
    #                                           criteria_name = 'pcl_size')

    
    #### CRITERIA 2: Building Shape ####

    # Allowed Residetnial Use
    # Height/Floors (Including sloped roofs)
    # Gross Floor Area
    # FAR

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
                                                                                         units = row['EST_UNITS']),
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
                                                       lu_dict_test(res_type= row['ZO_ AldUse'], 
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
        if np.isnan(row['MAXFAR']):
            return np.nan
        elif row['MAXFAR'] < row['FAR']:
            return 1
        else: 
            return 0
    
    blg_shape_criteria['far_conf'] = blg_shape_criteria.apply(lambda row:
                                                                  label_far(row),
                                                                  axis = 1)
    
    # ## Criteria Scoring ## 
    
    # blg_shape_criteria = mapc.get_criteria_score(criteria_table = blg_shape_criteria,
    #                                           weights = c2_weights,
    #                                           criteria_name = 'blg_shpe')
    

    
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
        elif row['EST_UNITS'] > row['MAXDU']: #original max_du
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
    

    # ## CRITERIA SCORING ## 
    # density_criteria = mapc.get_criteria_score(criteria_table=density_criteria, 
    #                                             weights=c3_weights,
    #                                             criteria_name='res_dnsy')
   
    # conformity_scores = mapc.get_final_score(final_suitability_table= density_criteria,
    #                                    weights= cr_weights,
    #                                     suitability_name = "conf"
    #                                    )
    conformity_scores = density_criteria

    ## For Test Report
    ot_parcels = len(set(conformity_scores['LOC_ID']))
    output_zones = len(set(conformity_scores['ZO_CODE']))
    output_length = len(conformity_scores)
    
    all_conf_fields = ['ls_conf', 'lc_conf', 'ld_conf', 'lu_conf', 'fl_conf', 'ht_conf', 'gfa_conf', 'du_conf', 'dua_conf', 'far_conf']
    all_measure_fields = res_zoning.columns.to_list()[18:27]
    all_measure_fields.insert(3, "ZO_AldUse")

    conformity_scores['size_sum'] = conformity_scores[['ls_conf', 'lc_conf', 'ld_conf']].sum(axis = 1, skipna = True)
    conformity_scores['shape_sum'] = conformity_scores[['lu_conf', 'fl_conf', 'ht_conf', 'gfa_conf', 'far_conf']].sum(axis = 1, skipna = True)
    conformity_scores['dense_sum'] = conformity_scores[['du_conf', 'dua_conf' ]].sum(axis = 1, skipna = True)
    conformity_scores['size_count'] = conformity_scores[['ls_conf', 'lc_conf', 'ld_conf']].count(axis = 1)
    conformity_scores['shape_count'] = conformity_scores[['lu_conf', 'fl_conf', 'ht_conf', 'gfa_conf', 'far_conf']].count(axis = 1)
    conformity_scores['dense_count'] = conformity_scores[['du_conf', 'dua_conf' ]].count(axis = 1)
    conformity_scores['Total'] = conformity_scores[['size_sum', 'shape_sum', 'dense_sum']].sum(axis = 1, skipna = True)
    conformity_scores['Measures'] = conformity_scores[all_measure_fields].count(axis = 1)
    conformity_scores['Tested Measures'] = conformity_scores[all_conf_fields].count(axis = 1)
 
    if score == True:
        return conformity_scores
    else:
        analysis_report = {
            'Test': ['Original Parcel Count', 'Parcel Layer Length', 'LIDAR Join Parcel Count', 'LIDAR Join Length', 'Zoning Join Parcel Count', 'Zoning Join Length','Overlap Test Parcels', 'Output Parcel Count','Parcels without Zoning', 'Original Zones', 'Zones in Parcel Output', 'Total Rows'],
            'Value': [og_parcels, og_parcels_len, bld_parcels, bld_parcels_len, zj_parcels, zj_parcels_len, ovlp_parcels, ot_parcels, no_zone_parcels, og_zones, output_zones, output_length]}
        
        analysis_report = pd.DataFrame(analysis_report)
        return analysis_report

#def run_zoning_district_scoring():
def test_merge(town_name, zone_type, zoning_check):

    muni_parcels = mapc.get_landuse_data(town_name)
    # print(len(muni_parcels))

    ldr_bld_muni = ldr_bld[ldr_bld['CITY'] == town_name].copy() #ensures pandas knows this is a new object
    # print(len(ldr_bld_muni))
    ldr_bld_muni['ftpt_area'] = ldr_bld_muni.area
    # ldr_bld_join = ldr_bld_muni[['LOC_ID_bld', 'MEDIAN', 'MEDIAN_stories', 'ftpt_area']]
    #outer join for footprint so we don't lose parcels that don't have one? 
    muni_parcels = structure_merge(ldr_bld_muni, muni_parcels)
    # print(len(muni_parcels))
    muni_parcels = muni_parcels[muni_parcels['EST_UNITS']> 2]
    # print(len(muni_parcels))
    # print(len(muni_parcels['LOC_ID_bld'].isna()))

    muni_parcels['DUA'] = muni_parcels['EST_UNITS']/(muni_parcels['LOT_SIZE_G']/43560)
    muni_parcels['LPU'] = (muni_parcels['LOT_SIZE_G']/43560)/muni_parcels['EST_UNITS']

    res_zoning = get_zoning_data(town_name, type = zone_type)
    print(set(res_zoning['ZO_AldUse']))
    muni_w_zoning = zoning_merge(zoning_gdf= res_zoning,
                                parcels_gdf= muni_parcels)
    
    print("LOCIDs of Parcels without Zoning")
    print(set(muni_w_zoning[muni_w_zoning['ZO_CODE'].isna()]['LOC_ID']))
    allowed_uses = set(muni_w_zoning['ZO_AldUse'])
    print(allowed_uses)
    if zoning_check == True :
        return muni_w_zoning
    
    else: 


        # muni_w_zoning = calculate_overlap(layer_1= muni_w_zoning,
        #                                          layer_2 = ldr_bld_muni,
        #                                          how = "percent",
        #                                          new_field_name = 'par_lot_cov')

        print(muni_w_zoning.columns)
        print(len(muni_w_zoning[muni_w_zoning['par_lot_cov_pct'].isna()]))

        all_conf_fields = ['ls_conf', 'lc_conf', 'ld_conf', 'lu_conf', 'fl_conf', 'ht_conf', 'du_conf', 'dua_conf', 'far_conf','gfa_conf']
        all_measure_fields = res_zoning.columns.to_list()[18:27]
        all_measure_fields.insert(3, "ZO_AldUse")
        all_req_cond_fields = ['LOT_SIZE', 'par_lot_cov_pct', 'LOT_SIZE_G', luc_adjusted, 'MEDIAN_stories', 'MEDIAN',  'EST_UNITS', 'DUA', 'FAR', 'BLD_AREA']


        
        missing_count = []
        for ex_cond in all_req_cond_fields:
            print(ex_cond)
            na_fields = len(muni_w_zoning[muni_w_zoning[ex_cond].isna()])
            missing_count.append(na_fields)

            
        column_report = {
            'Conformity Field' : all_conf_fields,
            'Zoning Measures' : all_measure_fields,
            'Existing Conditions' : all_req_cond_fields,
            'Missing Count' : missing_count
        }

        column_report = pd.DataFrame(column_report)
        column_report['Municipality'] = town_name
        print(column_report)

        return column_report
    # if len(allowed_uses == True )>0 :
    #     print("Missing Allowed Use")
    # else :
    #     print ("Allowed Uses All Good")


def analysis_outputs(town_name, conf_summary = True):

    all_conf_fields = ['ls_conf', 'lc_conf', 'ld_conf', 'lu_conf', 'fl_conf', 'ht_conf', 'far_conf','gfa_conf', 'du_conf', 'dua_conf']
    size_conf_fields = ['ls_conf', 'lc_conf', 'ld_conf']
    shape_conf_fields = ['lu_conf', 'fl_conf', 'ht_conf', 'gfa_conf', 'far_conf']
    density_conf_fields = ['du_conf', 'dua_conf']

    d1 = dict.fromkeys(all_conf_fields, (lambda x: x.sum(skipna = False)))
    d2 = dict.fromkeys(['LOC_ID'], 'count')
    d3 = dict.fromkeys(['IMP_UNITS', 'floors', 'height'], 'mean')
    d = d1 | d2 | d3


    rz_gdb = r"\\Data-Sync\Public\DataServices\Projects\Current_Projects\Housing\Zoning-to-Built-Form\Rightsizing Zoning\Rightsizing Zoning.gdb"
    # base_zone_summary = gpd.read_file(rz_gdb, layer= "mmc_base_zone_scores")
    # base_zone_summary_muni = base_zone_summary[base_zone_summary['CITY'] == town_name]

    layer_name = town_name + "_conformityscores_base"

    base_parcel_scores = gpd.read_file(rz_gdb, layer= layer_name).fillna(value={'MIN_LUCA': "xxx"})
    base_parcel_scores = base_parcel_scores[base_parcel_scores['MIN_LUCA'].str.startswith(("1", "0", "9"))]
    
    # overlay_zone_summary = readzonesummary
    # parcel_summary = readparceloutputs

    #1 Which Zoning Standards lead to the most non-conformity?
    analysis_1 = base_parcel_scores[all_conf_fields + ['LOC_ID'] + ['ZO_CODE'] + ['IMP_UNITS'] + ['height'] + ['floors']]

    summary = analysis_1.groupby('ZO_CODE').agg(d)
    summary['Municipality'] = town_name


    for col in all_conf_fields:
        summary[col] = round(summary[col]/summary['LOC_ID'], 2)
    
    analysis1_total = summary[all_conf_fields].max(skipna = True).idxmax() #returns the first max value column--we will need the full table somewhere
    analysis1_size = summary[size_conf_fields].max(skipna = True).idxmax()
    analysis1_shape = summary[shape_conf_fields].max(skipna = True).idxmax()
    analysis1_density = summary[density_conf_fields].max(skipna = True).idxmax()


    #2 Difference between base zoning and overlay
    #analysis_2 = #overlay base and overlay, do math on scores base-overlay, average effect of overlay zoning on non-conformity


    # By Right vs Special permit? ?

    #3 Nonconformity Score (total and subcategories) correlation with year built 
    analysis_3 = base_parcel_scores['Total'].corr(base_parcel_scores['YEAR_BUILT'])
    analysis_3_size =base_parcel_scores['size_sum'].corr(base_parcel_scores['YEAR_BUILT'])
    analysis_3_shpe =base_parcel_scores['shape_sum'].corr(base_parcel_scores['YEAR_BUILT'])
    analysis_3_dens =base_parcel_scores['dense_sum'].corr(base_parcel_scores['YEAR_BUILT']) 

    #return analysis_3

    #4 Nonconfomirty Score correlation (total and subcategories) with lot size
    analysis_4 = base_parcel_scores['Total'].corr(base_parcel_scores['LOT_SIZE_G'])
    analysis_4_size = base_parcel_scores['size_sum'].corr(base_parcel_scores['LOT_SIZE_G'])
    analysis_4_shpe = base_parcel_scores['shape_sum'].corr(base_parcel_scores['LOT_SIZE_G'])
    analysis_4_dens = base_parcel_scores['dense_sum'].corr(base_parcel_scores['LOT_SIZE_G']) 

    #return analysis_4

    analysis_output = {
         'Analysis Concept': ['Zoning Standard with most Nonconformity', 'Average Effect of Overlay Zoning', 'Correlation Score: Year Built', 'Correlation Score: Lot Size'],
         'Total Conformity': [analysis1_total, np.nan, analysis_3, analysis_4],
         'Lot Size': [analysis1_size, np.nan, analysis_3_size, analysis_4_size],
         'Building Shape': [analysis1_shape, np.nan, analysis_3_shpe,analysis_4_shpe],
         'Unit Density': [analysis1_density, np.nan, analysis_3_dens, analysis_4_dens]
     }

    analysis_output_df = pd.DataFrame.from_dict(analysis_output)
    analysis_output_df['Municipality'] = town_name
    analysis_output_df = analysis_output_df.set_index('Analysis Concept')

    if conf_summary == True:
        return summary
    else :
        return analysis_output_df

def zone_comparisons():

    '''
    Are there any zones that are clearly copy-paste situations? how do their non-conformities compare?

    '''

    print("TBD")

def get_popular_building_styles(muni):

    '''
    Task 1.3 What are the 5 most common residential building styles?
    '''
    parcels = mapc.get_landuse_data(muni)

    parcels = parcels[parcels['MIN_LUCA'].str.startswith("1")]
    parcels = parcels[parcels['EST_UNITS']> 2]

    # d1 = dict.fromkeys([])
    d2 = dict.fromkeys(['LOC_ID'], 'count')
    # d = d1 | d2

    parcels_style = parcels.groupby('STYLE').agg(d2)

    return parcels_style


def zoning_stats(muni):

    zoning_dissolved = gpd.read_file(r"\\Data-Sync\Public\DataServices\Projects\Current_Projects\Housing\Zoning-to-Built-Form\Rightsizing Zoning\Rightsizing Zoning.gdb", 
                                     layer = 'mmc_zoning_dissolved_joined')
    
    zoning_dissolved_muni = zoning_dissolved[zoning_dissolved['MUNI']==muni]

    ar_d = dict.fromkeys(['Shape_Area'], 'sum')

    zone_ald_use_share = zoning_dissolved_muni.groupby('ZO_AldUse').agg(ar_d)
    total_area = sum(zone_ald_use_share['Shape_Area'])
    zone_ald_use_share['pct'] = zone_ald_use_share['Shape_Area']/total_area

    return zone_ald_use_share
    



