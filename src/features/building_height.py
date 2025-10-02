
import arcpy
from arcpy import env
#import pandas as pd
#from arcgis.features import GeoAccessor, GeoSeriesAccessor
from arcpy.sa import *
import os
import geopandas as gpd
import fiona
import pandas as pd


datasets_dir = r'K:\DataServices\datasets'

#from src.data.make_dataset import ma_towns
from src.features.nested_functions import get_landuse_data

munis_fp = os.path.join(datasets_dir, "Boundaries\Spatial\MA_TOWNS.shp")
#munis_fp = os.path.join(input_dir, 'TOWNSSURVEY_POLY.shp')
munis=gpd.read_file(munis_fp)
muni_field = 'TOWN'

project_gdb = r'\\Data-Sync\Public\DataServices\Projects\Current_Projects\Neighborhood_Planning_and_Zoning\Zoning_Projects\Rightsizing_Zoning_2025\Rightsizing_Zoning_2025.gdb'
ndsm_gdb = r'\\data-sync\public\DataServices\Projects\Current_Projects\Neighborhood_Planning_and_Zoning\Zoning_Projects\Rightsizing_Zoning_2025\Rightsizing_Zoning_ndsm.gdb'

#define variables



#project geodatabase
#env.workspace = project_gdb

sampling_value = .8 #can change this sampling value (it is in meters)


def create_las_dataset(town_name, las_folder):

    '''
    Creates a las dataset that covers a municipality of interest

    Inputs: 
    - town_name (str): Town Name (not case sensitive)
    - las_folder: location of las data

    Outputs: las dataset covering municipality

    '''
    #input variables

    env.overwriteOutput = True
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference("NAD 1983 StatePlane Massachusetts FIPS 2001 (Meters)")
    out_las_dataset = os.path.join(las_folder, (town_name + '_lasd.lasd'))
    out_slope_raster = os.path.join(project_gdb, (town_name + '_slope_buildings'))

    if arcpy.Exists(out_slope_raster): #an existing out_slope_raster would mean this town has already been processed, so skip
        pass

    else:

        ### get a list of las tiles that intersect with the muni ###

        muni_gdf = munis.loc[munis[muni_field].str.casefold() == town_name.casefold()]
        index_fp = r'I:\Imagery\MassGIS_LAS_files\goodies\goodies\indices\USGS_MA_CentralEastern_1_2021_TileIndex.shp'
        index = gpd.read_file(index_fp)

        #first, reproject all to mass mainland
        mass_mainland_crs = "EPSG:26986"

        index = index.to_crs(mass_mainland_crs)
        muni_gdf = muni_gdf.to_crs(mass_mainland_crs)

        #then, use spatial join to identify intersection between muni boundary and tiles 
        intersecting = index.sjoin(muni_gdf, how='inner')
        intersecting_list =  intersecting['Tile_ID'].tolist()
        #create list of tiles
        las_list = []

        for item in intersecting_list:
            for dirpath, dirnames, filenames in os.walk(las_folder):
                for filename in filenames:
                    if item in filename: #ignores case
                        if filename.endswith('.las') : #search for file type
                            las_list.append(os.path.join(dirpath,filename))

        #finally, create las dataset based on list of indexed tiles
        arcpy.CreateLasDataset_management(input=las_list,
                                          out_las_dataset=out_las_dataset,
                                        compute_stats='COMPUTE_STATS')
    
    return out_las_dataset

def create_ndsm_raster(town_name, las_dataset):
    '''
    Creates a dsm raster covering the municipality of interest. The DSM depicts the difference between the 
    digital surface model (DSM)—which reflects the highest points of objects (tops of structures, vegetation)—
    and the digital terrain model (DTM), which reflects the underlying “bare earth" (State of Vermont).
    In this function, both DSM and DTM are created and used to define a final nDSM.

    Inputs:
    - town_name (str): Town Name (not case sensitive)
    - las_dataset: las dataset created in create_las_dataset()

    Output:
    - ndsm raster covering buildings in municipality

    '''

    ### DEFINE VARIABLES ###

    env.workspace = ndsm_gdb
    #env.overwriteOutput = True
    arcpy.env.outputCoordinateSystem = arcpy.SpatialReference("NAD 1983 StatePlane Massachusetts FIPS 2001 (Meters)")
    

    #DTM
    ground_layer = town_name + '_ground_layer'
    ground_code = [1]
    ground_return_values = ['LAST', 'LAST_OF_MANY']
    out_dtm_raster = r"memory\dtm_surface" #+ town_name + '_dtm_surface'


    #DSM
    surface_layer = town_name + '_surface_layer'
    surface_return_values = [1, 'FIRST_OF_MANY']
    out_dsm_raster = r"memory\dsm_surface" #town_name + '_building_dsm_surface'
    building_code = [6]

    #NDSM
    in_raster1 = out_dsm_raster
    in_raster2 = out_dtm_raster
    out_ndsm_raster =  os.path.join(ndsm_gdb, (town_name + '_ndsm_buildings'))

 
    ## DIGITAL TERRAIN MODEL (DTM) ##

    print('dtm layer creation')

    #create a las dataset layer for ground return values (last/last of many), on ground code
    dtm_layer = arcpy.management.MakeLasDatasetLayer(in_las_dataset=las_dataset, 
                                                    out_layer = ground_layer, 
                                                    class_code = ground_code,
                                                    return_values = ground_return_values)

    #convert to raster, of resolution sampling_value (defined at top of script)
    arcpy.conversion.LasDatasetToRaster(in_las_dataset=dtm_layer, 
                                            out_raster=out_dtm_raster, 
                                            value_field='ELEVATION', 
                                            interpolation_type = 'BINNING AVERAGE LINEAR',
                                            sampling_type='CELLSIZE', 
                                            sampling_value=sampling_value)
    
    
    ## DIGITAL SURFACE MODEL (DSM) ##

    print('dsm layer creation')

    #create a las dataset layer for surface return values (first/first of many), only on building code
    dsm_layer = arcpy.management.MakeLasDatasetLayer(in_las_dataset=las_dataset, 
                                                    out_layer = surface_layer, 
                                                    class_code = building_code,
                                                    return_values = surface_return_values)

    #convert to raster, of resolution sampling_value (defined at top of script)
    arcpy.conversion.LasDatasetToRaster(in_las_dataset=dsm_layer, 
                                        out_raster=out_dsm_raster, 
                                        value_field='ELEVATION',
                                        interpolation_type = 'BINNING MAXIMUM NONE',
                                        sampling_type='CELLSIZE', 
                                        sampling_value=sampling_value)
    
    

    

    ## NORMALIZED DIGITAL SURFACE MODEL (NDSM) FROM DSM AND DTM ##

    print('ndsm layer creation')
    # nDSM is the DSM - DTM, so run raster calculator to do so
    # Execute RasterCalculator(Minus) function
    ndsm_raster = RasterCalculator(rasters= [in_raster1, in_raster2], 
                                        input_names = ["x", "y"],
                                        expression="x-y")
    
    ndsm_raster.save(out_ndsm_raster)

    #Delete dsm and dtm 
    arcpy.Delete_management(out_dsm_raster)
    arcpy.Delete_management(out_dtm_raster)

    return out_ndsm_raster

def  get_building_heights_from_ndsm(town_name):

    '''
    runs zonal statistics on ndsm layers to provide summary statistics for building height across each structure in input town.
    summar statistics = 'MAX', 'RANGE', 'MEAN', 'STD', 'MEDIAN', 'PCT90', 'PCT75', 'PCT25'

    '''

    path = r"\\data-sync\public\DataServices\Projects\Current_Projects"
    structures_dir = os.path.join(path, r"Climate_Change\MVP_MMC_CoolRoofs_MVP\Data\Analysis_Data\Data_Cool_Roofs\0_Input\structures.gdb")
    building_structures_fp = os.path.join(structures_dir, 'STRUCTURES_POLY')
    building_structures_layer = 'STRUCTURES_POLY'
    munis_fp = os.path.join(datasets_dir, "Boundaries\Spatial\MA_TOWNS.shp")

  
    ndsm_gdb = os.path.join(path, "Neighborhood_Planning_and_Zoning\Zoning_Projects\Rightsizing_Zoning_2025\Rightsizing_Zoning_ndsm.gdb")
    project_gdb = os.path.join(path, 'Neighborhood_Planning_and_Zoning\Zoning_Projects\Rightsizing_Zoning_2025\RightsizingZoning_2025.gdb')

    clipped_footprints = os.path.join(project_gdb, (town_name + '_footprints'))

    out_ndsm_raster =  os.path.join(ndsm_gdb, (town_name + '_ndsm_buildings'))
    zonal_stats_name = os.path.join(project_gdb, (town_name + '_zonal_stats'))

    env.overwriteOutput = True

    #get footprints from muni

    town_boundary = arcpy.management.SelectLayerByAttribute(
                                            in_layer_or_view=munis_fp,
                                            selection_type="NEW_SELECTION",
                                            where_clause="TOWN = '{}'".format(town_name.upper()),
                                            invert_where_clause=None)
    
    selection = arcpy.management.SelectLayerByLocation(
                                            in_layer=building_structures_fp,
                                            overlap_type="INTERSECT",
                                            select_features=town_boundary,
                                            search_distance=None,
                                            selection_type="NEW_SELECTION",
                                            invert_spatial_relationship="NOT_INVERT"
                                        )


    arcpy.management.CopyFeatures(selection, clipped_footprints)


    #clip height raster to town boundary
    town_ndsm_raster = ExtractByMask(out_ndsm_raster, 
                                    town_boundary,
                                        "INSIDE")
    
    
    ## ZONAL STATISTICS AS TABLE ##
    with arcpy.EnvManager(snapRaster=town_ndsm_raster, 
                        #extent=town_boundary, 
                        cellSize=out_ndsm_raster):
        ZonalStatisticsAsTable(
                        in_zone_data=clipped_footprints,
                        zone_field="STRUCT_ID",
                        in_value_raster=town_ndsm_raster,
                        out_table= zonal_stats_name,
                        ignore_nodata="DATA",
                        statistics_type="ALL",
                        percentile_values=[90,75,25]
                        )
        
        
    stats_fields = ['MAX', 'RANGE', 'MEAN', 'STD', 'MEDIAN', 'PCT90', 'PCT75', 'PCT25']
    
        
    # join new field with footprints
    arcpy.management.JoinField(
                                in_data=clipped_footprints,
                                in_field='STRUCT_ID',
                                join_table=zonal_stats_name,
                                join_field="STRUCT_ID",
                                fields=stats_fields
    )


    #delete intermediate steps 
    arcpy.Delete_management(zonal_stats_name)


    #reading that layer into geopandas to add "stories" field
    enriched_footprints_gdf = gpd.read_file(project_gdb, layer=(town_name + '_footprints'))

    
    
    
    enriched_footprints_gdf.to_file(project_gdb, layer=(town_name + '_footprints'), driver='OpenFileGDB')



def run_building_height_process(gdb_path, 
                                list_of_town_names,
                                output_layer_name,
                                cool_roofs_gdf):
    '''
    Adds stories, parcel data, and roof shape (from cool roofs) to the building footprints created in
    get_building_height_from_ndsm().
    
    Inputs: 
        - location of town ndsm rasters from step 1 (and where final layer will be outputted)
        - list of town names for processing
        - name of output layer 
        - input gdf with cool roofs info (for "flat_roof" field)
    Output: added fields to the structures layer from running get_building_height_from_ndsm()
        - flat_roof (from cool_roofs_gdf)
        - "stories" added to 
        - parcel info from MAPC parcel database
    '''

    print('Reading in and merging footprints with building heights, created from NDSM')

    # MERGE FOOTPRINT LAYERS, ADD 'STORIES' FIELDS # 
    mass_mainland_crs = "EPSG:26986"

    #concatonate all of the roofprint layers in the gdb
    layer_list = fiona.listlayers(gdb_path)

    #only keep footprint layers
    filtered_layers = [layer for layer in layer_list if 'footprints' in layer]

    all_towns_footprints_height = gpd.GeoDataFrame(pd.concat([gpd.read_file(gdb_path, layer=layer_name) for layer_name in filtered_layers], 
                                            ignore_index=True), crs=mass_mainland_crs).drop_duplicates()

    #drop null structures (mostly structures built since lidar flyover)
    all_towns_footprints_height = all_towns_footprints_height.dropna(subset=['MEDIAN'])

    #add 'stories' fields
    height_stats_fields = ['MAX',  'MEAN', 'RANGE', 'MEDIAN', 'PCT90', 'PCT75', 'PCT25']

    for stats_field in height_stats_fields:
        field_name = stats_field + '_stories'
        all_towns_footprints_height[field_name] = (all_towns_footprints_height[stats_field] - .75) / 3.3 #subtract a meter as an (arbitrary) amount of raised-ness as an estimate for meters in a story

    ### LAND PARCEL DF FOR ALL OF MMC ### (customizing this for this analysis)
    print('Reading in parcel database')

    #create blank gdf
    parcel_db_fields = ['LOC_ID', 'MIN_LUCA', 'CITY', 'SITE_ADR_L', 'geometry']
    all_towns_parcels = gpd.GeoDataFrame(columns=parcel_db_fields, geometry='geometry')

    #add parcel data to blank gdf
    for town_name in list_of_town_names:
        muni_parcels = get_landuse_data(town_name)[parcel_db_fields]
        all_towns_parcels = pd.concat([all_towns_parcels, muni_parcels])


    #join footprints to parcels
    # intersection
    print('Joining roofprints with parcels')
    structures_w_parcels_overlay = gpd.overlay(all_towns_footprints_height, all_towns_parcels, how='intersection')

    #only keep structure-parcel pairs for the parcel the structure is majority on 
    structures_w_parcels_overlay['area'] = structures_w_parcels_overlay.geometry.area
    structures_w_parcels_overlay = structures_w_parcels_overlay.sort_values(
        by='area').drop_duplicates(subset='STRUCT_ID', keep='last') #Drop duplicates, keep last/largest


    structures_w_parcels = all_towns_footprints_height[['STRUCT_ID', 'geometry']].merge(structures_w_parcels_overlay.drop(columns='geometry'), 
                                                                    on='STRUCT_ID',
                                                                    how='left').drop_duplicates()

    #now add sqm field, drop area field above (that was just for intersection parts)
    structures_w_parcels['roof_sqm'] = structures_w_parcels.geometry.area
    
    print('Joining with cool roofs data')
    #add cool roofs "flat_roof" field
    #merge back to roofprints
    fields_to_keep = ['STRUCT_ID', 'LOC_ID', 'MIN_LUCA', 'SITE_ADR_L', 'CITY', 'MAX',  'MEAN', 'MEDIAN', 'PCT90', 'PCT75', 'PCT25', 
                    'MAX_stories', 'MEAN_stories', 'MEDIAN_stories', 'PCT75_stories', 'PCT25_stories',
                    'geometry', 'roof_sqm']

    #join  to cool roofs to add "flat roof" field
    structures_w_parcels = structures_w_parcels[fields_to_keep].merge( cool_roofs_gdf[['STRUCT_ID', 'flat_roof']].drop_duplicates(), 
                                                                        on='STRUCT_ID', 
                                                                        how='left').drop_duplicates()

    ## at some point will go back to cool roofs to update code and remove duplicate building issue ##
    print('Calculating primary structure')
    #add primary structure field
    structures_w_parcels['primary_structure'] = 0

    #structures without a loc_id get a 
    #first identify largest structure per parcel
    structures_w_parcels.loc[structures_w_parcels.groupby('LOC_ID')['roof_sqm'].idxmax(),'primary_structure'] = 1

    #if condo or housing authority, overwrite (all are "primary structures")
    structures_w_parcels.loc[(structures_w_parcels['MIN_LUCA'] == '102') | #condos
                            (structures_w_parcels['MIN_LUCA'] == '114') | #affordable housing
                            (structures_w_parcels['MIN_LUCA'] == '970') | #housing authorities
                            (structures_w_parcels['MIN_LUCA'] == '908'), #housing authority (Boston)
                            'primary_structure'] = 1
    
    print('Exporting to project geodatabase')
    #export to gdb
    structures_w_parcels.to_file(gdb_path, layer=(output_layer_name), driver='OpenFileGDB')

    #return
    return structures_w_parcels
