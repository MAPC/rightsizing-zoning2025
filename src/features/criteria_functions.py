import pandas as pd
import geopandas as gpd
from functools import reduce

def get_criteria_score(criteria_table, 
                        weights: dict,
                        criteria_name:str):

    '''
    Pulls from a list of dfs and a "weights" dictionary to perform a weighted average of desired indicators.

    Inputs:
    dfs = list of data frames to include 
    weights = dictionary of variables and associated weights
    category name = a field name for the score variable 

    Outputs:
    A weighted sum (category name) and percentile ranking ('rnk_categoryname') for 
    each row based on given indicators and weights.

    Example:
    Define inputs
    local_accessibility_df = [schools, 
                            walkscore, 
                            towncenter]

    local_accessibility_weights = {
                                'nrm_schls': 1,     #school walksheds
                                'nrm_wlkscr': 2,    #walkscore
                                'nrm_twncntr': 2,   #within a town center
                                }

    Run function
    local_accessibility = category_merge(local_accessibility_df, local_accessibility_weights, 'lcl_acc')

    '''

    #get weighted sum based on variable weights
    criteria_table[criteria_name] = (criteria_table[weights.keys()] * weights).sum(1) / sum(weights.values())

    #get percentile ranking for weighted sum value
    criteria_table[('CR_' + criteria_name)] = criteria_table[criteria_name].rank(method='min', pct=True)

   
    return(criteria_table)


def get_final_score(final_suitability_table, 
                    weights: dict,
                    suitability_name:str):

    '''
    Pulls from a list of dfs and a "weights" dictionary to perform a weighted average of desired indicators.

    Inputs:
    dfs = list of data frames to include 
    weights = dictionary of variables and associated weights
    category name = a field name for the score variable 

    Outputs:
    A weighted sum (category name) and percentile ranking ('rnk_categoryname') for 
    each row based on given indicators and weights.

    Example:
    Define inputs
    local_accessibility_df = [schools, 
                            walkscore, 
                            towncenter]

    local_accessibility_weights = {
                                'nrm_schls': 1,     #school walksheds
                                'nrm_wlkscr': 2,    #walkscore
                                'nrm_twncntr': 2,   #within a town center
                                }

    Run function
    local_accessibility = category_merge(local_accessibility_df, local_accessibility_weights, 'lcl_acc')

    '''


    #get weighted sum based on variable weights
    final_suitability_table[suitability_name] = (final_suitability_table[weights.keys()] * weights).sum(1) / sum(weights.values())

    #get percentile ranking for weighted sum value
    final_suitability_table[('FNL_' + suitability_name)] = final_suitability_table[suitability_name].rank(method='min', pct=True)


    return(final_suitability_table)