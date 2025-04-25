import os
import geopandas as gpd
import pandas as pd
import numpy as np

import sys
sys.path.append("..")

from src.data.make_dataset import mass_mainland_crs
from src.features.nested_functions import *



def if_overlap (layer_1, 
                layer_2,
                new_field_name:str,
                inverse:bool=False,
                point:bool=False
                ):
   
    '''
    For a given base layer (layer_1), identifies whether there is overlap (intersection) with a layer of interest (layer_2). If the layer of interest is a point layer, 
    identifies whether the point is within the base layer feature. 

    INPUTS: 
    - layer_1: (GeoDataFrame) The base layer being enriched  
    - layer_2: (GeoDataFrame) The overlap layer of interest 
    - new_field_name: (string)  Input a string to represent this layer in the output dataset

    OPTIONAL PARAMETER(S):
    - inverse: (bool, default False) When true, reverses the 0 and 1. This should be applied for layers in which overlap is unfavorable. 
    - point: (bool, default False) Select 'True' when layer_2 is a point layer. In these cases, the function looks for whether the base layer contains a point layer.  

    OUTPUT: 
    '[new_field_name]_ovlp' field added to layer_1 
        - Value of 1 if: 
            - There is overlap, and overlap is favorable (Inverse = 'False') 
            - There is no overlap, and overlap is unfavorable (Inverse = 'True') 
        - Value of 0 if: 
            - There is no overlap and overlap is favorable (Inverse = 'False') 
            - There is overlap is and overlap is unfavorable (Inverse = 'True') 
    '''

    #reproject all to mass mainland
    layer_1 = layer_1.to_crs(mass_mainland_crs)
    layer_2 = layer_2.to_crs(mass_mainland_crs)

    #determine predicate based on 'point' input
    if point:
        predicate = 'contains'
    else:
        predicate = 'intersects'


    overlap_only = gpd.sjoin(layer_1, 
                            layer_2,
                            predicate=predicate,
                            how='inner') #only keep geometry from layer_1


    
    ## MERGE BACK TO FULL DATASET ## 
    new_field_name = new_field_name + '_ovlp'

    #add a field for whether it overlaps or not. If inverse is not selected, a value of 1 indicates overlap. Reverse is true if inverse not selected.
    if inverse:
        overlap_only[new_field_name] = 0

        #join back to base layer 
        layer_1_with_overlap = layer_1.merge(overlap_only[new_field_name], 
                                            how='left', 
                                            left_index=True, 
                                            right_index=True).fillna(1).drop_duplicates()

    
    else:
        overlap_only[new_field_name] = 1

        #join back to base layer 
        layer_1_with_overlap = layer_1.merge(overlap_only[new_field_name], 
                                            how='left', 
                                            left_index=True, 
                                            right_index=True).fillna(0).drop_duplicates()

        
    return(layer_1_with_overlap)


def calculate_overlap (layer_1,
                       layer_2, 
                       how:str,
                       new_field_name:str, 
                       normalize:bool=True,
                       inverse:bool=False,
                       buffer=None):

    '''
    For a given polygon base layer, calculates either 
    1) the total area of overlap (in meters squared) with a polygon layer of interest;
    2) the percentage of the base layer that is overlapped by a polygon layer of interest; OR 
    3) the total length of a line layer of interest that is contained by the base layer [need to do this]


    INPUTS: 
    - layer_1: (GeoDataFrame, polygon) The base layer being enriched 
    - layer_2: (GeoDataFrame, polygon or line) The overlap layer of interest 
    - how: (string, default 'area') the type of calculation: 
        - 'area' = calculates the area of overlap in meters squared 
        - 'percent' = calculate the percentage of the base layer  
        - 'length' = calculate the length (in m) of an overlapping line layer within a chosen distance from layer_1
    - new_field_name: (string)  Input a string to represent this layer in the output dataset 

    OPTIONAL PARAMETER(S):
    - normalize: (bool, default True) When True, adds an additional field containing a normalized value (0-1 scale) of the area/percentage of overlap. 
    - inverse: (bool, default False) When True, normalized values are scored in the inverse. This implies that greater overlap = less suitability.  
    - buffer: (int, default None) For calculating length, specify a buffer distance around layer_1 to search

    OUTPUT:
    Fields added to layer_1: 
    - Overlap values:  
        - '[new_field_name]_sqm' or '[new_field_name]_pct' or '[new_field_name]_m'
    - Normalized overlap values (with inverse applied if selected):  
        - '[new_field_name]_sqm_n' or '[new_field_name]_pct_n' or '[new_field_name]_m_n'

    '''
    from src.data.make_dataset import id_field
    if not how:
        how = 'area'
    
    valid = {'area', 'percent', 'length'}
    if how not in valid:
        raise ValueError("how must be one of %r." % valid)

    #reproject all to mass mainland
    mass_mainland_crs = "EPSG:26986"
    layer_1 = layer_1.to_crs(mass_mainland_crs)
    layer_2 = layer_2.to_crs(mass_mainland_crs)

    #make a list of original columns for later
    layer_1_fields = layer_1.columns.tolist()

    if how in ['area' , 'percent']:

        #only keep parts of layer 1 that intersects with layer 2
        intersection_layer = layer_1.overlay(layer_2, how='intersection', keep_geom_type=False)
        
        #get area of overlap for the area of intersection
        intersection_layer[new_field_name + '_sqm'] = intersection_layer['geometry'].area  
        intersection_layer = intersection_layer.groupby(by=id_field).agg({(new_field_name + '_sqm'):'sum'}).reset_index()
        

        #join back to parcels data, remove additional rows with groupby
        layer_1_enriched = layer_1.merge(intersection_layer[[id_field, (new_field_name + '_sqm')]], 
                                        on=id_field, 
                                        how='left')
        
        #try a fillna() to account for np.nan in overlap values
        layer_1_enriched[new_field_name + '_sqm'] = layer_1_enriched[new_field_name + '_sqm'].fillna(0)

        #get percent of overlap for each feature in the base layer
        layer_1_enriched[new_field_name + '_pct'] = (layer_1_enriched[new_field_name + '_sqm'] / (layer_1_enriched['geometry'].area)) 

        #final output defined by input and optional parameters
        if how == 'area':
            if normalize: 
                layer_1_enriched[(new_field_name + '_sqm_n')] = normalize_field(layer_1_enriched, (new_field_name + '_sqm'))
                if inverse:
                    layer_1_enriched[(new_field_name + '_sqm_n')] = 1 - layer_1_enriched[(new_field_name + '_sqm_n')] 
                layer_1_enriched = layer_1_enriched[layer_1_fields + [(new_field_name + '_sqm'), (new_field_name + '_sqm_n')]]
            else:
                layer_1_enriched = layer_1_enriched[layer_1_fields + [(new_field_name + '_sqm')]]

        elif how == 'percent':
            if normalize: 
                layer_1_enriched[(new_field_name + '_pct_n')] = normalize_field(layer_1_enriched, [(new_field_name + '_pct')])
                if inverse:
                    layer_1_enriched[(new_field_name + '_pct_n')] = 1 - layer_1_enriched[(new_field_name + '_pct_n')] 
                layer_1_enriched = layer_1_enriched[layer_1_fields + [(new_field_name + '_pct'), (new_field_name + '_pct_n')]]
            else:
                layer_1_enriched = layer_1_enriched[layer_1_fields + [(new_field_name + '_pct')]]

    else: #for line length overlaps
        layer_1_buffer = buffer_gdf(layer_1, buffer)

        #Intersect buffered parcels with lines - returns line segments that intersect with each parcel
        intersection_layer = gpd.overlay(df1=layer_1_buffer, 
                                        df2=layer_2, 
                                        how="intersection", 
                                        keep_geom_type=False)

        #sum line length per unique ID
        intersection_layer[new_field_name + '_m'] = intersection_layer['geometry'].length 
        intersection_layer[new_field_name + '_m'] = intersection_layer.groupby(id_field)[new_field_name + '_m'].transform("sum")

        #merge length field back to layer_1
        layer_1_enriched = layer_1.merge(intersection_layer[[id_field, (new_field_name + '_m')]], 
                                         on=id_field,
                                         how='left').fillna(0).drop_duplicates()

        if normalize: 
            layer_1_enriched[(new_field_name + '_m_n')] = normalize_field(layer_1_enriched, (new_field_name + '_m'))
            if inverse:
                layer_1_enriched[(new_field_name + '_m_n')] = 1 - layer_1_enriched[(new_field_name + '_m_n')] 
            layer_1_enriched = layer_1_enriched[layer_1_fields + [(new_field_name + '_m'), (new_field_name + '_m_n')]]
        else:
            layer_1_enriched = layer_1_enriched[layer_1_fields + [(new_field_name + '_m')]]

    return layer_1_enriched

def overlap_stats (layer_1, 
                   layer_2, 
                   new_field_name:str,
                   stats:str='maj',
                   normalize:bool=True,
                   inverse:bool=False,
                   stats_field:str=None,
                   nan_value=None
                   ):
                   
    '''
    Assigns the base layer with the (max, min, mean, median, maj (majority), count, sum) value from an overlapping geography that may have multiple 
    values overlapping the parcel. Best suited for an overlapping geography that may have multiple values within the parcel. 

    INPUT PARAMETERS: 
    - layer_1: (GeoDataFrame) The base layer being enriched  
    - layer_2: (GeoDataFrame) The overlap layer of interest 
    - new_field_name: (string) Input a string to represent this layer in the output dataset 
    
    OPTIONAL PARAMETERS:
    - stats_field: (string) The field of interest for getting statistics
    - stats: (string, default 'mean') 'max', 'min', 'mean', 'median', 'majority', 'count', 'sum'
    - nan_value: Input a nan value for performing stats or normalizing. Will replace with np.nan so it isn't calculated in stats
    - normalize: (bool, default True) When True, adds an additional field containing a normalized value (0-1 scale) of the associated value. Can only be used with continuous variables.
    - inverse: (bool, default False) When True, the normalized or ranked value is returned as an inverse so that values closer to 1  

    OUTPUT:
    Fields added to layer_1: 
    - [new_field_name]_['stat'] 
    - If normalize: '[new_field_name']_['stat']_n 
    '''
    from src.data.make_dataset import id_field

    
    valid = {'max', 'min', 'mean', 'median', 'maj', 'count', 'sum'}
    if stats not in valid:
        raise ValueError("stats must be one of %r." % valid)

    #if there is a nan_value in the stats field, replace here with np.nan
    if nan_value:
        layer_2[stats_field] = layer_2.replace(nan_value, np.NaN).copy()
    
    #make a list of original columns for later
    layer_1_fields = layer_1.columns.tolist()
        
    #reproject all to mass mainland
    mass_mainland_crs = "EPSG:26986"
    layer_1 = layer_1.to_crs(mass_mainland_crs)
    layer_2 = layer_2.to_crs(mass_mainland_crs)


    if stats == 'maj':  #first, if majority, sort by area than drop everything except the largest
        
        # this can only be done with two polygon features currently because limited to 'overlay'
        layers_joined = layer_1.overlay(layer_2, how='intersection')

        #Sort by area so largest area is last
        layers_joined['area'] = layers_joined.geometry.area
        layers_joined = layers_joined.sort_values(by='area')
        layers_joined = layers_joined.drop_duplicates(subset=id_field, keep='last') #Drop duplicates, keep last/largest

        layers_joined[(new_field_name + '_' + stats)] = layers_joined[stats_field] #rename


    if stats == 'count': #if count, get the number of overlapping features
        #first, perform a spatial join
        layers_joined = gpd.sjoin(layer_1, layer_2, how='inner') #spatial join so can be for features beyond polygons. inner to just get intersecting layers.
        
        layers_joined[stats] = 1 
        layers_joined = layers_joined.groupby(by=[id_field]).agg({stats:'sum'}).reset_index()
        layers_joined[(new_field_name + '_' + stats)] = layers_joined[stats].fillna(0) #rename

    
    if stats in {'max', 'min', 'mean', 'median', 'sum'}:
        #first, perform a spatial join
        layers_joined = gpd.sjoin(layer_1, layer_2, how='inner')

        #then do a groupby with the stats field and stats
        layers_joined = layers_joined.groupby(by=id_field).agg({stats_field:stats}).reset_index()

        layers_joined[new_field_name + '_' + stats] = layers_joined[stats_field]

    
    layer_1_enriched = layer_1.merge(layers_joined[[id_field, (new_field_name + '_' + stats)]], on=id_field, how='left').fillna(np.nan)

    if normalize: 
        layer_1_enriched[(new_field_name + '_' + stats + '_n')] = normalize_field(layer_1_enriched, (new_field_name + '_' + stats))
        if inverse:
            layer_1_enriched[(new_field_name + '_' + stats + '_n')] = 1 - layer_1_enriched[(new_field_name + '_' + stats + '_n')] 
        layer_1_enriched = layer_1_enriched[layer_1_fields + [(new_field_name + '_' + stats), (new_field_name + '_' + stats + '_n')]]
    
    else:
        layer_1_enriched = layer_1_enriched[layer_1_fields + [(new_field_name + '_' + stats)]]


    return layer_1_enriched


def proximity (layer_1, 
                layer_2, 
                new_field_name:str,
                normalize:bool=True,
                inverse:bool=False,
                unit:str='m',
                fields:list=None,
                ):
                   
    '''
    For a given base layer, calculates the distance to the nearest part of a layer of interest. Can also provide information
    about the nearest part. 

    INPUT PARAMETERS: 
    - layer_1: (GeoDataFrame) The base layer being enriched  
    - layer_2: (GeoDataFrame) The layer of interest for proximity 
    - new_field_name:(string) Input a string to represent this layer in the output dataset 
    

    - normalize: (bool, default True) When True, adds an additional field containing a normalized value (0-1 scale) of distance to layer_2.  
    - inverse: (bool, default True) When true, normalized values are scored in the inverse, implying that greater distances to layer_2 are less favorable, or in other words that proximity is favorable. This is the default. Set to false if greater distances are favorable. 
    - unit: (string, default 'meters') 'meters' ('m'), 'miles' ('mi'), 'kilometers' ('km') 
    - fields: (list, default None) When a list of field names from layer_2 are provided, those fields will also be added to layer_1
    
    OUTPUT:
    Fields added to layer_1: 
    - '[new_field_name]_['unit'] 
    - If normalize:  
        - '[new_field_name]_['unit']_n, where values closer to 1 indicate greater proximity/shorter distances (unless inverse is False) 
    - If fields list provided, those fields will also
    '''

    from src.data.make_dataset import id_field

    #first make sure units are correct. default to meters.
    if not unit:
        unit = 'm'

    valid = {'m', 'mi', 'km', 'ft'}
    if unit not in valid:
        raise ValueError("unit must be one of %r." % valid)

    new_field_name = new_field_name + ('_') + unit

    #convert all to mass mainlan
    mass_mainland_crs = "EPSG:26986"
    layer_1 = layer_1.to_crs(mass_mainland_crs)
    layer_2 = layer_2.to_crs(mass_mainland_crs)

    #make a list of original columns for later
    layer_1_fields = layer_1.columns.tolist()

    #run sjoin_nearest, will join layer_1 with closest feature of layer_2 and add all fields
    layers_joined = gpd.sjoin_nearest(layer_1, layer_2, how='left', distance_col = new_field_name)

    if unit == 'm':
        layers_joined[new_field_name] = layers_joined[new_field_name]
    elif unit == 'mi':
        layers_joined[new_field_name] = layers_joined[new_field_name] / 1609
    elif unit == 'km':
        layers_joined[new_field_name] = layers_joined[new_field_name] / 1000
    elif unit == 'ft':
        layers_joined[new_field_name] = layers_joined[new_field_name] * 3.281

    layers_joined = layers_joined.groupby(layers_joined.index).agg('first') #do this just in case 

    #what fields do bring in from layers_joined? Start with the join field and distance field
    fields_list = [new_field_name] 

    #then add any other fields listed in input
    if fields:
        for field in fields:
            fields_list.append(field) 

    #then add normalized values
    if normalize: #for proximity, we assume we want to be CLOSER to layer_2, so we inverse automatically.
        layers_joined[(new_field_name + '_n')] = 1 - normalize_field(layers_joined, new_field_name)
        if inverse:
            layers_joined[(new_field_name + '_n')] = 1 + layers_joined[(new_field_name + '_n')] 
        fields_list.append((new_field_name + '_n'))   
        #define final table
    
    #join only desired fields to layer_1
    layer_1_enriched = layer_1.merge(layers_joined[fields_list + [id_field]], on=id_field, how='left').fillna(np.nan)
    
    #ensure only original fields + additional field list
    layer_1_enriched = layer_1_enriched[layer_1_fields + fields_list]

    return layer_1_enriched                


def field_stats(layer_1, 
                stats_field:str,
                new_field_name:str,
                inverse:bool=False,
                nan_value=None):
                    
    '''
    Assigns the base layer with the normalized value for an existing field in an input dataset. 

    INPUT PARAMETERS: 
    - layer_1: (GeoDataFrame) The base layer being enriched  
    - new_field_name: (string)  Input a string to represent this layer in the output dataset 
    - stats_field: (string) The field you are interested in normalizing

    OPTIONAL PARAMETERS
    - nan_value: Input a nan value for normalizing. Will replace with np.nan. 
    - inverse: (bool, default False) When True, the normalized or ranked value is returned as an inverse so that values closer to 1  
    
    OUTPUT
    Fields added to layer_1: 
    - '[new_field_name']_n (inversed if inverse)
    
    '''
    #first, replace nan value    
    layer_1_enriched = layer_1.copy()

    #get field names for later 
    layer_1_fields = layer_1_enriched.columns.tolist()
    
    if nan_value:
        layer_1_enriched[stats_field] = layer_1_enriched[stats_field].replace(nan_value, np.NaN).copy()

    #get normalized value for field
    layer_1_enriched[(new_field_name + '_n')] = normalize_field(layer_1_enriched, stats_field)

    #inverse if desired
    if inverse:
        layer_1_enriched[(new_field_name + '_n')] = 1 - layer_1_enriched[(new_field_name + '_n')] 

    layer_1_enriched = layer_1_enriched[layer_1_fields + [(new_field_name + '_n')]]

    return layer_1_enriched

 

 
def calculate_indicator_score(function:str,
                               layer_1,
                               layer_2=None,
                               new_field_name=None,
                               normalize=None, #set normalize to True automatically?
                               how=None,
                               inverse=None,
                               nan_value=None,
                               stats=None,
                               stats_field=None,
                               point=None,
                               unit=None,
                               fields=None,
                               buffer=None,
                               layer_2_buffer=None
                              ):
                            

    '''
    Functions: 'if_overlap', 'calculate_overlap', 'overlap_stats', 'proximity', 'field_stats'  

    Rachel to fill in
    A function that fits in all other functions to calculate indicator scores

    Added 'layer_2_buffer' parameter to buffer layer_2 for running all functions

    '''
    
    valid = {
            'if_overlap', 
            'calculate_overlap', 
            'overlap_stats', 
            'proximity', 
            'field_stats'         
            }
    
    if layer_2_buffer:
        layer_2 = buffer_gdf(gdf=layer_2, 
                             buffer_size=layer_2_buffer)

    if function not in valid:
        raise ValueError("function must be one of %r." % valid)

    if function == 'if_overlap':
        return if_overlap(layer_1=layer_1, 
                        layer_2=layer_2, 
                        new_field_name=new_field_name, 
                        inverse=inverse, 
                        point=point)

    elif function == 'calculate_overlap':

        if not normalize:
            normalize=True
            
        return calculate_overlap(layer_1=layer_1, 
                                layer_2=layer_2,
                                how=how, 
                                new_field_name=new_field_name, 
                                normalize=normalize,
                                inverse=inverse,
                                buffer=buffer)       
        
    elif function == 'overlap_stats':

        if not stats:
            stats = 'maj'
            normalize = False
        
        else: 
            if not normalize:
                normalize=True

        return overlap_stats(layer_1=layer_1, 
                            layer_2=layer_2, 
                            stats_field=stats_field,
                            new_field_name=new_field_name,
                            stats=stats,
                            normalize=normalize,
                            inverse=inverse,
                            nan_value=nan_value
                            )

    elif function == 'proximity':
        
        if not normalize:
            normalize=True

        return proximity(layer_1=layer_1, 
                        layer_2=layer_2, 
                        new_field_name=new_field_name,
                        normalize=normalize,
                        inverse=inverse,
                        unit=unit,
                        fields=fields
                        )
                        

    elif function == 'field_stats':
        return field_stats(layer_1=layer_1, 
                        stats_field=stats_field, 
                        new_field_name=new_field_name, 
                        inverse=inverse, 
                        nan_value=nan_value)