import os
import geopandas as gpd
import pandas as pd
import numpy as np
import arcpy
from arcgis import GIS
from arcgis.features import FeatureLayer, FeatureSet
import json
import zipfile36 as zipfile
from io import BytesIO
from urllib.request import urlopen
import shutil
import rasterio
import math 
from shapely.geometry.polygon import Polygon
from shapely.geometry import Polygon, box

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')


import sys
sys.path.append("..")

mass_mainland_crs = "EPSG:26986"

def agol_to_gdf(url):

    '''
    input: arcgis online feature service url
    output: feature service converted into a geopandas geodataframe
    '''
    gis = GIS() 
    layer = FeatureLayer(url, gis) 
    fset = layer.query() 
    gjson_string = fset.to_geojson
    gjson_dict = json.loads(gjson_string)
    #gdf = gpd.GeoDataFrame.from_features(gjson_dict['features'])
    gdf = gpd.read_file(gjson_string, driver='GeoJSON')
    gdf = gdf.to_crs(mass_mainland_crs)
    return gdf

def get_file(dir_name:str,
             muni:str=None,
             fileType:str=None):
    '''
    some town names are substrings of other town names (ex: Reading is a substring of North Reading,
        or Dover in Andover)
    this causes errors when trying to pull the right muni's file from a directory.
    this function pulls the correct matching file.
    can  also pull just the correct file type out (ie, a .shp from a whole shapefile)

    inputs:
    - dir_name: directory name to search through
    - muni(str): muni name, as seen in file paths (ie, with any included underscores). Not case sensitive.
    - filetype(str): optional, could be .shp, .csv, etc.

    output:
    correct file name to read from
    '''

    #search through all file names in the directory for those that include the muni name
    #outputs a list of file names
    

    if muni:
        list_of_files = []
        if fileType: #if there is a specified file type to draw from
            for dirpath, dirnames, filenames in os.walk(dir_name):
                for filename in filenames:
                    if muni.casefold() in filename.casefold(): #ignores case
                        if filename.endswith(fileType): #search for file type
                            list_of_files.append(filename)
        else:
            for dirpath, dirnames, filenames in os.walk(dir_name):
                for filename in filenames:
                    if muni.casefold() in filename.casefold(): #ignores case
                        list_of_files.append(filename)
        
        
        if len(list_of_files) == 1: #for towns that don't trigger multiple file names, can stop here
            file = os.path.join(dirpath, list_of_files[0])
        

        else: #otherwise, match muni prefix or name depending on type of substring conflict
            #start with names (cases where muni names are substrings of others, not related to prefix)
            non_prefix_munis = ['Lynn', 'Dover', 'Milton', 'Stow']
            if muni in non_prefix_munis:
                if muni.casefold() == 'Lynn'.casefold():
                   list_of_files = list(filter(lambda x: 'Lynnfield'.casefold() not in x.casefold(), list_of_files))
                   file = os.path.join(dirpath, list_of_files[0])  
                elif muni.casefold() == 'Dover'.casefold():
                    list_of_files = list(filter(lambda x: 'Andover'.casefold() not in x.casefold(), list_of_files))
                    file = os.path.join(dirpath, list_of_files[0])  
                elif muni.casefold() == 'Milton'.casefold():
                    list_of_files = list(filter(lambda x: 'Hamilton'.casefold() not in x.casefold(), list_of_files))
                    file = os.path.join(dirpath, list_of_files[0])  
                elif muni.casefold() == 'Stow'.casefold():
                    list_of_files = list(filter(lambda x: 'Williamstown'.casefold() not in x.casefold(), list_of_files))
                    file = os.path.join(dirpath, list_of_files[0])  
            else: #move on to prefixes
                prefixes = ['East', 'North', 'West', 'South', 'New']
                for prefix in prefixes: #loop through prefixes
                    #if a town has a prefix, find the matching prefix in the fle name
                    if prefix.casefold() in muni.casefold(): 
                        #search through list of files for that prefix
                        list_of_files = list(filter(lambda x: prefix.casefold() in x.casefold(), list_of_files))
                        file = os.path.join(dirpath, list_of_files[0]) 
                    #if no prefix in town name, find the file name without the prefix
                    else: 
                        list_of_files = list(filter(lambda x: prefix.casefold() not in x.casefold(), list_of_files))
                        file = os.path.join(dirpath, list_of_files[0]) 
    else:
        for dirpath, dirnames, filenames in os.walk(dir_name):
            for filename in filenames:
                if filename.endswith(fileType):
                    file = os.path.join(dirpath, filename)

    return(file)

def normalize_field(df, col:str):
    
    '''
    removes outliers then rescales column to a value from 0-1

    input = data frame, column name that you are normalizing
    output = normalized value btwn 0 and 1 

    we can play around with methods layer. for now, it's min max scaling 
    https://towardsdatascience.com/data-normalization-with-pandas-and-scikit-learn-7c1cc6ed6475

    '''
    
    #cap outliers at Q1 - 1.5*IQR and Q3 + 1.5*IQR
    Q1=df[col].quantile(0.25) 
    Q3=df[col].quantile(0.75)
    IQR=Q3-Q1

    low_limit=Q1-1.5*IQR
    high_limit=Q3+1.5*IQR

    #trim outliers
    def trim_outliers(row):
        if (row[col] <= low_limit).any():
            return low_limit
        elif (row[col] >= high_limit).any():
            return high_limit
        else:
            return row[col]
        
    df_norm = df.copy()

    df_norm[col] = df_norm.apply(lambda row: trim_outliers(row), axis=1)

    #df_norm=df[col][~((df[col]<(Q1-1.5*IQR)) | (df[col]>(Q3+1.5*IQR)))]
    
    # apply min-max scaling to capped values
    df_norm = (df_norm[col] - df_norm[col].min()) / (df_norm[col].max() - df_norm[col].min())
        
    return df_norm

def get_landuse_data(muni):
    
    '''
    input = muni name
    process = picks out the right shapefile from the state's municipal land use database;
             makes a subdirectory in intermediate folder w town name and exports land use shapefile to it
             reads that shapefile in as a geodataframe
             merges with mapc land parcel database 
    output = state detailed parcel layer, merged with mapc land parcel database
    '''

    from src.data.make_dataset import mapc_lpd_folder, boston_parcels, mass_mainland_crs    
    project_dir = r'C:\Users\ziacovino\Desktop\temp_muni'

    def get_most_updated_state_assessors_data(muni):

        '''
        pulls parcel data from the state's assessors website (with an exception for Boston who hosts separately)
        '''

        
        if muni == 'Boston':
            #get shapefile from boston's open data portal and download
            #change in make_dataset.py

            parcel_layer = boston_parcels.copy()

            parcel_layer = parcel_layer.loc[parcel_layer['POLY_TYPE']=='FEE']
            return(parcel_layer)
        

        else:

            #get shapefile from a massgis link
            shapefile_excel = 'https://www.mass.gov/doc/massgis-parcel-data-download-links-table/download'
            shapefile_lookup = pd.read_excel(shapefile_excel)

            town_shp_lookup_link = shapefile_lookup.loc[shapefile_lookup['Town Name'] == muni.upper()]

            #extract into a temporary folder for use
            
            path = os.path.join(project_dir, 'Data', muni) #make a subdirectory in ortho folder w town name
            os.makedirs(path, exist_ok=True) 

            for url in town_shp_lookup_link['Shapefile Download URL'].tolist():
                with urlopen(url) as zipresp:
                    with zipfile.ZipFile(BytesIO(zipresp.read())) as zfile:
                        zfile.extractall(path)


            layer = get_file(path, 'TaxPar', '.shp')
            parcel_layer = gpd.read_file(layer)

            parcel_layer = parcel_layer.loc[parcel_layer['POLY_TYPE']=='FEE']
            return(parcel_layer)
        

    #get the most updated parcel data from massgis
    muni_state_parcels = get_most_updated_state_assessors_data(muni)

    #now delete the temporary folder that was made for that layer
    if muni == 'Boston':
        pass
    else:
        path = os.path.join(project_dir, 'Data', muni)
        shutil.rmtree(path)

    #read in land parcel database
    file_name = get_file(dir_name=mapc_lpd_folder, 
                         muni=muni)

    #file_name = lpd_prefix + muni + lpd_suffix
    muni_lpd_path = os.path.join(mapc_lpd_folder, file_name)
    mapc_lpd = pd.read_csv(muni_lpd_path)  

    #merge land parcel database with state muni parcels
    #only keep the loc_id from state parcel database because we only want the MAPC lpd fields
    muni_lpd_preprocess = muni_state_parcels[['LOC_ID', 'geometry']].merge(mapc_lpd, 
                                                                           on='LOC_ID', 
                                                                           how='inner')
    
    muni_lpd_preprocess = muni_lpd_preprocess.to_crs(mass_mainland_crs)

    return(muni_lpd_preprocess)  

def buffer_gdf(gdf, 
               buffer_size,
               point=False):
    '''
    function that buffers an input gdf. returns input gdf, but with buffered geometry.
    If the input gdf is a point layer, point=True
    '''
    if point:
        gdf_buffer = gdf.to_crs(mass_mainland_crs)
        gdf_buffer['geometry'] = gdf_buffer['geometry'].buffer(buffer_size) 
    
    else:
        #perform buffer, returns geoseries
        gdf_buffer = gpd.GeoDataFrame(geometry=(gdf.buffer(distance=buffer_size))) #transform to gdf to merge back to og gdf
        gdf_buffer= gdf.drop(columns='geometry').merge(gdf_buffer, left_index=True, right_index=True) #merge back to gdf, returns df

        #finally, create a gdf out of df
        gdf_buffer = gpd.GeoDataFrame(data=gdf_buffer, 
                                    geometry=gdf_buffer['geometry'], 
                                    crs=mass_mainland_crs)
    
    return gdf_buffer


#function to download from a link
def get_gdf_from_zipped_link(url, topic:str):

    '''

    input: a URL that downloads a zipped shapefile
    output: a gdf of the download, with the shapefile download deleted (no storage need)

    '''

    path = os.path.join('K:\DataServices\Projects\Current_Projects\PDAs_PPAs\I90_PPA_PDA\Data', topic)
    os.makedirs(path, exist_ok=True) 

    #extract zipped folder to path
    with urlopen(url) as zipresp:
        with zipfile.ZipFile(BytesIO(zipresp.read())) as zfile:
            zfile.extractall(path)


    #pull out just the .shp file
    shapefile = get_file(dir_name=path, 
                         fileType='.shp')
    
    #read gdf from shapefile
    gdf = gpd.read_file(shapefile)
    gdf = gdf.to_crs(mass_mainland_crs)

    #delete file after extracted
    shutil.rmtree(path)

    return(gdf)

def create_grid(feature, shape, side_length):
    '''Create a grid consisting of either rectangles or hexagons with a specified side length that covers the extent of input feature.'''

    # Slightly displace the minimum and maximum values of the feature extent by creating a buffer
    # This decreases likelihood that a feature will fall directly on a cell boundary (in between two cells)
    # Buffer is projection dependent (due to units)
    feature = feature.buffer(20)

    # Get extent of buffered input feature
    min_x, min_y, max_x, max_y = feature.total_bounds


    # Create empty list to hold individual cells that will make up the grid
    cells_list = []

    # Create grid of squares if specified
    if shape in ["square", "rectangle", "box"]:

        # Adapted from https://james-brennan.github.io/posts/fast_gridding_geopandas/
        # Create and iterate through list of x values that will define column positions with specified side length
        for x in np.arange(min_x - side_length, max_x + side_length, side_length):

            # Create and iterate through list of y values that will define row positions with specified side length
            for y in np.arange(min_y - side_length, max_y + side_length, side_length):

                # Create a box with specified side length and append to list
                cells_list.append(box(x, y, x + side_length, y + side_length))


    # Otherwise, create grid of hexagons
    elif shape == "hexagon":

        # Set horizontal displacement that will define column positions with specified side length (based on normal hexagon)
        x_step = 1.5 * side_length

        # Set vertical displacement that will define row positions with specified side length (based on normal hexagon)
        # This is the distance between the centers of two hexagons stacked on top of each other (vertically)
        y_step = math.sqrt(3) * side_length

        # Get apothem (distance between center and midpoint of a side, based on normal hexagon)
        apothem = (math.sqrt(3) * side_length / 2)

        # Set column number
        column_number = 0

        # Create and iterate through list of x values that will define column positions with vertical displacement
        for x in np.arange(min_x, max_x + x_step, x_step):

            # Create and iterate through list of y values that will define column positions with horizontal displacement
            for y in np.arange(min_y, max_y + y_step, y_step):

                # Create hexagon with specified side length
                hexagon = [[x + math.cos(math.radians(angle)) * side_length, y + math.sin(math.radians(angle)) * side_length] for angle in range(0, 360, 60)]

                # Append hexagon to list
                cells_list.append(Polygon(hexagon))

            # Check if column number is even
            if column_number % 2 == 0:

                # If even, expand minimum and maximum y values by apothem value to vertically displace next row
                # Expand values so as to not miss any features near the feature extent
                min_y -= apothem
                max_y += apothem

            # Else, odd
            else:

                # Revert minimum and maximum y values back to original
                min_y += apothem
                max_y -= apothem

            # Increase column number by 1
            column_number += 1

    # Else, raise error
    else:
        raise Exception("Specify a rectangle or hexagon as the grid shape.")

    # Create grid from list of cells
    grid = gpd.GeoDataFrame(cells_list, columns = ['geometry'], crs = mass_mainland_crs)

    # Create a column that assigns each grid a number. Call it LOC_ID for other functions
    grid["LOC_ID"] = np.arange(len(grid))
    grid = grid.clip(feature)


    # Return grid
    return grid

def get_heat_score(heat_index_fp, muni_gdf):


    '''
    For each census block  in the municipality, determines the relative heat index score compared to all other 
    block groups. Parcels within those block groups can then be prioritized higher.

    Inputs: Muni boundary (gdf), heat index raster (geotiff), comparitive geography

    '''
    from rasterstats import zonal_stats
    from src.data.make_dataset import census_bl

    with rasterio.open(heat_index_fp) as raster:
        transform = raster.transform
        lst = raster.read(1).astype('float64')

    
    #retain census blocks within MUNI
    census_bl['og_area'] = census_bl['geometry'].area #get original area to do sliver analysis

    muni_blocks = census_bl.clip(muni_gdf)
    muni_blocks['pct_bg'] = ((muni_blocks['geometry'].area) / (muni_blocks['og_area'])) * 100
    muni_blocks['pct_bg'] = ((muni_blocks['geometry'].area) / (muni_blocks['og_area'])) * 100
    muni_blocks = muni_blocks.loc[muni_blocks['pct_bg'] > 5].reset_index()    #only keep block groups where 5% or more of the bg remains. Reset index for zonal stats

    ## ZONAL STATS ## 
    #run zonal stats on heat index for mmc - what is the mean lst index score across census block?
    lst_stats = pd.DataFrame(zonal_stats(muni_blocks, 
                                        lst, 
                                        affine=transform, 
                                        stats='mean'))
    
    #join back to blocks, rename field
    muni_blocks_heat = muni_blocks[['geoid20', 'geometry']].join(lst_stats)
    muni_blocks_heat = muni_blocks_heat.rename(columns={'mean':'lst_mean'})


    return muni_blocks_heat

def get_zoning_data(muni):
    '''
    input = muni name
    process = load zoning shapefile
              join zoning regs
    output = gdf with zoning data and regulations

    '''
    from src.data.make_dataset import zoning_layer    
    zoning_project_dir = r'C:\Users\ziacovino\OneDrive - Metropolitan Area Planning Council\Metro Mayors Housing Task Force\Phase 2 Scope of Work\Rightsizing Zoning Project\Data'
    


    # shapefile needs some data updating work
    zoning = zoning_layer[zoning_layer['muni'] == muni]
    zoning = zoning.to_crs(mass_mainland_crs)
    #zo_code = 'Zoning'


    # regulation table (exported 4/10)
    reg_table_fp = os.path.join(zoning_project_dir, "zoning-atlas-mmc.csv")
    #original Newton table
    #reg_table_fp = os.path.join(zoning_project_dir, "zoning-regs-by_right.csv")
    reg_table = pd.read_csv(reg_table_fp)

    zoning_reg_table = pd.merge(zoning, reg_table, left_on= 'zo_code', right_on= "ZO_CODE", how = "inner")

    return zoning_reg_table

def condo_conversion(luc, units):
    '''
    takes condo parcels (102 and 998) and based on imputed units 
    converts them to 104, 105, 111 or 112

    ''' 
    if luc == "102" or luc == "998": 
        if units == 2:
            return "104"
        elif units == 3:
            return "105"
        elif units >= 4 and units < 8:
            return "111"
        elif units >= 8:
            return "112"
    else:
        return luc 
    

def zoning_merge(zoning_gdf, parcels_gdf):

    # join the parcels to the zoning, potentially cutting up parcels in split zones
    par_zon_join = parcels_gdf.overlay(zoning_gdf, how = "intersection", keep_geom_type = True)

    if len(par_zon_join['LOC_ID']) >  len(set(par_zon_join['LOC_ID'])):

        print ("Split Zoned Parcels Detected")       
        # determine the proportion of the total parcel area
        par_zon_join['zone_area'] = par_zon_join['geometry'].area
        par_zon_join['zone_share'] = par_zon_join.apply(lambda row: row['zone_area']*10.7639/row['LOT_SIZE_GIS'], axis=1) #its a row

        # ID the index of the row with the largest share of a parcel in a zone for each unique LOCID, reset_index() makes into a df
        idx = par_zon_join.fillna(999999).groupby('LOC_ID')['zone_share'].idxmax().reset_index()

        # subset the original spatial join to the rows where the share is the largest for each unique LOC ID--should be one row for each LOCID again
        clean_join = par_zon_join.loc[idx['zone_share']]
        print("Clean Join successful?")
        print(len(idx) == len(clean_join))
        # cut that table to just the LOC ID and the ZO Code, confirm pd
        par_zon_xwalk = clean_join[['LOC_ID','ZO_CODE']]
        # join the zone code onto the parcels, double check the join
        parcels_zone_rec = pd.merge(parcels_gdf, par_zon_xwalk, left_on= 'LOC_ID', right_on= "LOC_ID", how = "left")
        print("Zone Code succesfully joined?")
        print(len(parcels_zone_rec['LOC_ID']) == len(clean_join))
        print(parcels_zone_rec.info())
        # take the zoning input and get rid of the geometry so we can do non-spatial joins
        zoning_table = pd.DataFrame(zoning_gdf.drop(columns= 'geometry'))
        # join the rest of the zoning table back to the parcels
        par_zon_join_fixed = pd.merge(parcels_zone_rec, zoning_table, left_on= 'ZO_CODE', right_on= 'ZO_CODE', how = "inner")
        print("Zones assigned to Parcels by Largest Share")
        return par_zon_join_fixed

    else : 
        print("Parcels Sucessfully Overlayed")
        return par_zon_join










