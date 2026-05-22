import os
import pandas as pd
import mapc_suitability as mapc
import geopandas as gpd

from src.data.make_dataset import mass_mainland_crs


def get_zoning_data(muni, type = 'base'):
    '''
    input = muni name
    process = load zoning shapefile
              join zoning regs
    output = gdf with zoning data and regulations

    '''
    from src.data.make_dataset import zoning_layer, zoning_overlay_layer    
    zoning_project_dir = r'C:\Users\ziacovino\OneDrive - Metropolitan Area Planning Council\Metro Mayors Housing Task Force\Phase 2 Scope of Work\Rightsizing Zoning Project\Data'
    

    # regulation table (exported 4/10)
    if type == 'base':
        reg_table_fp = os.path.join(zoning_project_dir, "zoning-atlas-mmc.csv")
        # shapefile needs some data updating work
        zoning = zoning_layer[zoning_layer['muni'] == muni]
        zoning = zoning.to_crs(mass_mainland_crs)
    #zo_code = 'Zoning'


    elif type == 'overlay':
        print("importing overlay")
        reg_table_fp = os.path.join(zoning_project_dir, "zoning-atlas-overlay.csv")
        # shapefile needs some data updating work
        zoning = zoning_overlay_layer[zoning_overlay_layer['muni'] == muni]
        print(zoning.head())
        zoning = zoning.to_crs(mass_mainland_crs) 
    
    else:
        return print("invalid zoning type, please enter 'base' or 'overlay'")

    #original Newton table
    #reg_table_fp = os.path.join(zoning_project_dir, "zoning-regs-by_right.csv")
    reg_table = pd.read_csv(reg_table_fp)
    reg_table = reg_table[reg_table['MUNI'] == muni]
    print(reg_table.head())
    
    reg_table['PCTLOTCOV'] = pd.to_numeric(reg_table['PCTLOTCOV'].str.strip('%'))

    zoning_reg_table = pd.merge(zoning, reg_table, left_on= 'zo_code', right_on= "ZO_CODE", how = "inner")
    
    return zoning_reg_table

def condo_conversion(luc, units):
    '''
    takes condo parcels (102 and 998) and mainly residential mixed use (013) 
    and based on imputed units 
    converts them to 104, 105, 111 or 112

    ''' 
    if luc == "102" or luc == "998" or luc == '013' or pd.isna(luc) or luc == "" or luc == None: 
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
    par_zon_join = parcels_gdf.overlay(zoning_gdf, how = "intersection", keep_geom_type = False)
    print("Parcel Rows")
    print(len(parcels_gdf['LOC_ID']))
    print("Unique LOC_IDS")
    print(len(set(parcels_gdf['LOC_ID'])))
    print("Joined Parcel Length")
    print(len(par_zon_join['LOC_ID']))

    if len(par_zon_join['LOC_ID']) >  len(set(par_zon_join['LOC_ID'])):

        print ("Split Zoned Parcels Detected")

     # determine the proportion of the total parcel area
        par_zon_join['zone_area'] = par_zon_join['geometry'].area
        par_zon_join['zone_share'] = par_zon_join.apply(lambda row: row['zone_area']*10.7639/row['LOT_SIZE_G'], axis=1) #its a row
        

     # ID the index of the row with the largest share of a parcel in a zone for each unique LOCID, reset_index() makes into a df
        idx = par_zon_join.fillna('999999').groupby('LOC_ID')['zone_share'].idxmax().reset_index()
        
        #print(len(idx))

     # subset the original spatial join to the rows where the share is the largest for each unique LOC ID--should be one row for each LOCID again
        clean_join = par_zon_join.loc[idx['zone_share']]
        print("Clean Join successful?")
        print(len(idx) == len(clean_join))

     # cut that table to just the LOC ID and the ZO Code, confirm pd
        par_zon_xwalk = clean_join[['LOC_ID','ZO_CODE']]
        #print(par_zon_xwalk)

     # join the zone code onto the parcels, double check the join
        parcels_zone_rec = pd.merge(parcels_gdf, par_zon_xwalk, left_on= 'LOC_ID', right_on= "LOC_ID", how = "left")
        
        print("Any Parcels missing a Zone Code?")
        print(len(parcels_zone_rec[parcels_zone_rec['ZO_CODE'].isna()]['LOC_ID']))
        print("Same parcels we started with?")
        print(set(parcels_zone_rec['LOC_ID']) == set(parcels_gdf['LOC_ID']))
        print("Same number of parcels we started with?")
        print(len(parcels_zone_rec) == len(parcels_gdf['LOC_ID']))
        #print("Parcels with the Zoning Code")
        #print(parcels_zone_rec.info())

     # take the zoning input and get rid of the geometry so we can do non-spatial joins, reduce to just the table
        zoning_table = pd.DataFrame(zoning_gdf.drop(columns= ['geometry', 'shape_leng', 'Shape_Length', 'Shape_Area', 'EDITDATE']))
        print("Zoning Table pre-dedupe")
        print(len(zoning_table))
        zoning_table = zoning_table.drop_duplicates()
        print("Zoning Table post De-Dupe")
        print(len(zoning_table))

        
     # join the rest of the zoning table back to the parcels
        par_zon_join_fixed = pd.merge(parcels_zone_rec, zoning_table, left_on= 'ZO_CODE', right_on= 'ZO_CODE', how = "left")
        
        print("Parcels with Zoning Table Joined")
        #print(par_zon_join_fixed.info())
        print(len(par_zon_join_fixed['LOC_ID']))
        print("Zones assigned to Parcels by Largest Share")
        return par_zon_join_fixed

    else : 
        print("Parcels Sucessfully Overlayed")
        return par_zon_join


def structure_merge(roofprints_gdf, parcels_gdf):
    #from src.features.indicator_functions import calculate_overlap
    #Roofprints filtered to primary structures
    print("Total Rows in Roofprints")
    print(len(roofprints_gdf['LOC_ID_bld']))
    print('Total Unique Parcel IDs')
    print(len(set(roofprints_gdf['LOC_ID_bld'])))

    # first step is consolidating multiple structure parcels to one value per LOC_ID
    def structure_consolidation(field_name, minmaxsum):

        if minmaxsum == 'max':
            # table of the loc_if idex of the max value of group
            idx = roofprints_gdf.fillna(999999).groupby('LOC_ID_bld')[field_name].idxmax().reset_index()
            # print(idx.info)
            #cuts the roofprints to the index of the max? 
            max_structure_values = roofprints_gdf.loc[idx[field_name]][['LOC_ID_bld', field_name]]

            return max_structure_values
        if minmaxsum == 'max':
            idx = roofprints_gdf.fillna(999999).groupby('LOC_ID_bld')[field_name].idxmin().reset_index()
            # print(idx.info)
            min_structure_values = roofprints_gdf.loc[idx[field_name]][['LOC_ID_bld', field_name]]
            return min_structure_values
        if minmaxsum == 'sum' :
           idx = roofprints_gdf.fillna(999999).groupby('LOC_ID_bld')[field_name].sum().reset_index()
           # print(idx.info)
           sum_structure_values = idx[['LOC_ID_bld', field_name]] 
           return sum_structure_values
        else :
            return print("please specificy max or min in minmax")
        
    floors = structure_consolidation('MEDIAN_stories', 'max')
    print(len(floors))
    height = structure_consolidation('MEDIAN', 'max')
    print(len(height))
    coverage = structure_consolidation('ftpt_area', 'sum')
    print(len(coverage))

    full_table = pd.merge(pd.merge(floors, height, on = 'LOC_ID_bld', how =  'outer'), coverage, 
                          on = 'LOC_ID_bld', how = 'outer')

    print('Rows in final join table for Building Structures')
    print(len(full_table))
    print('Unique Parcels in Building Structures')
    print(len(set(full_table['LOC_ID_bld'])))
    parcels_gdf = parcels_gdf.merge(full_table, left_on = 'LOC_ID', right_on = 'LOC_ID_bld', how = 'left')
    print('Rows in final parcel layer')
    print(len(parcels_gdf))
    print('Unique Parcels in Final Parcel Layer')
    print(len(set(parcels_gdf['LOC_ID'])))
    parcels_gdf = mapc.calculate_overlap(layer_1= parcels_gdf,
                                             layer_2 = roofprints_gdf,
                                             how = "percent",
                                             new_field_name = 'par_lot_cov',
                                             normalize= False,
                                             id_field= "LOC_ID")
    print('Rows in overlap calc parcel layer')
    print(len(parcels_gdf))
    print('Unique Parcels in overlap calc Parcel Layer')
    print(len(set(parcels_gdf['LOC_ID'])))

    return parcels_gdf