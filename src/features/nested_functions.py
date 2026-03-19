import os
import geopandas as gpd
import pandas as pd
import numpy as np
#import arcpy
#from arcgis import GIS
#from arcgis.features import FeatureLayer, FeatureSet
import json
import io
from io import BytesIO
import zipfile36 as zipfile
from io import BytesIO
from urllib.request import urlopen
import shutil
import tempfile
import requests
import rasterio
import math 
from shapely.geometry.polygon import Polygon
from shapely.geometry import Polygon, box

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# from src.data.make_dataset import mapc_lpd_folder

import sys
sys.path.append("..")

mass_mainland_crs = "EPSG:26986"

def agol_to_gdf(url):

    #input: arcgis online feature service url
    #output: feature service converted into a geopandas geodataframe

    gis = GIS() 
    layer = FeatureLayer(url, gis) 
    fset = layer.query() 
    gjson_string = fset.to_geojson
    gjson_dict = json.loads(gjson_string)
    #gdf = gpd.GeoDataFrame.from_features(gjson_dict['features'])
    gdf = gpd.read_file(gjson_string, driver='GeoJSON')
    gdf = gdf.to_crs(mass_mainland_crs)
    return gdf

def download_and_extract_zip_to_temp(url):
    """
    Downloads a zipped file from a URL, extracts it to a temporary directory,
    and returns the path to the temporary directory.

    Args:
        url (str): The URL of the zipped file.

    Returns:
        str: The path to the temporary directory where the files are extracted.
             Returns None if an error occurs during download or extraction.
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()

    # Define the path for the downloaded zip file within the temporary directory
    zip_file_path = os.path.join(temp_dir, "downloaded_archive.zip")

    # Download the zip file
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Raise an exception for bad status codes

    with open(zip_file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    # Extract the zip file
    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    return temp_dir

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

    return file

def get_gdf_from_zipped_link(url, file_type:str, shapefile_name=None, layer_name=None, mask_gdf=None):
    """
    mostly built for MassGIS direct downloads, bypassing the K drive.

    input: a URL that downloads a zipped shapefile, with file type (geojson, gdb, shp). if gdb, include layer name.
    output: a gdf of the download, with the shapefile download deleted (no storage need)

    INPUTS:
    - url:(string) URL for the download link (right click "download" button)
    - file_type: (string) 'shp', 'gdb', 'geojson'. Do not include "."
    
    OPTIONAL PARAMETERS:
    - shapefile_name: (string) for some MassGIS downloads, there are multiple shapefiles. Use this argument to 
    specify the shapefile to read. Do not include .shp
    - layer_name: (string) for GeoDatabase downloads, specifies which layer from the gdb to read in.
    - mask_gdf: (gdf) a GeoDataFrame of a mask to read in 
    """
    path = download_and_extract_zip_to_temp(url)

    # pull out just the file type of choice
    
    if shapefile_name is not None:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                if filename.endswith('shp'):
                    if shapefile_name in filename:
                        file = os.path.join(dirpath, filename)
        #assume it's a shapefile
        if mask_gdf is not None:
            gdf = gpd.read_file(file, mask=mask_gdf)
        else:
            gdf = gpd.read_file(file)

    elif file_type in ['shp', 'geojson']:
        shapefile = get_file(dir_name=path, fileType= ("." + file_type))
        # read gdf from shapefile
        if mask_gdf is not None:
            gdf = gpd.read_file(shapefile, mask=mask_gdf)
        else:
            gdf = gpd.read_file(shapefile)

    elif file_type == 'gdb':
        for dirpath, dirnames, filenames in os.walk(path):
            for dirname in dirnames:
                if "gdb" in dirname:
                    gdb = os.path.join(path, dirname)
        if mask_gdf is not None:
            gdf = gpd.read_file(gdb, layer=layer_name, mask=mask_gdf)
        else:
            gdf = gpd.read_file(gdb, layer=layer_name)

    gdf = gdf.to_crs(mass_mainland_crs)

    # delete file after extracted
    shutil.rmtree(path)

    return gdf


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

def get_most_updated_state_assessors_data(muni, path=None, include_row=False):
    """
    pulls parcel data from the state's assessors website (with an exception for Boston who hosts separately)
    """

    if not path:
        path = tempfile.mkdtemp()

    if muni == "Boston":
        print("reading Boston data from ", boston_parcels_url, ". Update if necessary.")
        # get geojson from boston's open data portal and download

        # unzip to temp folder
        boston_parcels_gdf = get_gdf_from_zipped_link(boston_parcels_url, file_type="shp")

        # download csv
        s = requests.get(boston_assessors_csv).content
        boston_assessors = pd.read_csv(io.StringIO(s.decode("utf-8")), dtype={'GIS_ID': str})
        #boston_assessors["GIS_ID"] = boston_assessors["GIS_ID"].astype(str)

        # merge gdf to assessor's data
        parcel_layer = boston_parcels_gdf.merge(
            boston_assessors, how="inner", left_on="MAP_PAR_ID", right_on="GIS_ID"
        )

        if include_row:
            pass
        else:
            parcel_layer = parcel_layer.loc[parcel_layer["POLY_TYPE"].isin(["FEE", "TAX"])]
        return parcel_layer

    else:
        # get shapefile from a massgis link
        shapefile_excel = (
            "https://www.mass.gov/doc/massgis-parcel-data-download-links-table/download"
        )
        shapefile_lookup = pd.read_excel(shapefile_excel)

        town_shp_lookup_link = shapefile_lookup.loc[
            shapefile_lookup["Town Name"] == muni.upper()
        ]

        # extract into a temporary folder for use

        # path = os.path.join(project_dir, 'Data', muni) #make a subdirectory in ortho folder w town name
        # os.makedirs(path, exist_ok=True)

        for url in town_shp_lookup_link["Shapefile Download URL"].tolist():
            with urlopen(url) as zipresp:
                with zipfile.ZipFile(BytesIO(zipresp.read())) as zfile:
                    zfile.extractall(path)

        layer = get_file(path, "TaxPar", ".shp")
        parcel_layer = gpd.read_file(layer)
        if include_row:
            pass
        else:
            parcel_layer = parcel_layer.loc[parcel_layer["POLY_TYPE"].isin(["FEE", "TAX"])]

        # delete temporary directory
        shutil.rmtree(path)

        parcel_layer = parcel_layer.to_crs(mass_mainland_crs)

        return parcel_layer

def get_landuse_data(muni):
    """
    input = muni name
    process = picks out the right shapefile from the state's municipal land use database;
             makes a subdirectory in intermediate folder w town name and exports land use shapefile to it
             reads that shapefile in as a geodataframe
             merges with mapc land parcel database
    output = state detailed parcel layer, merged with mapc land parcel database
    """

    # get the most updated parcel data from massgis
    muni_state_parcels = get_most_updated_state_assessors_data(muni)

    # read in land parcel database
    file_name = get_file(dir_name=mapc_lpd_folder, muni=muni)

    # file_name = lpd_prefix + muni + lpd_suffix
    muni_lpd_path = os.path.join(mapc_lpd_folder, file_name)
    mapc_lpd = pd.read_csv(muni_lpd_path)

    # merge land parcel database with state muni parcels
    # only keep the loc_id from state parcel database because we only want the MAPC lpd fields
    muni_lpd_preprocess = muni_state_parcels[["LOC_ID", "geometry"]].merge(
        mapc_lpd, on="LOC_ID", how="left"
    )

    muni_lpd_preprocess = muni_lpd_preprocess.to_crs(mass_mainland_crs)

    return muni_lpd_preprocess


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
  

