import arcpy

def edit_zoningatlas(muni, new_data):
    arcpy.management.Append(
    inputs="zn178",
    target="mmc_zoning",
    schema_type="NO_TEST",
    field_mapping=r'oid_ "oid_" true true false 8 Double 0 0,First,#;zo_code "zo_code" true true false 80 Text 0 0,First,#,zn178,ZONECODE,0,12;muni_id "muni_id" true true false 8 Double 0 0,First,#,zn178,TOWN_ID,-1,-1;muni "muni" true true false 80 Text 0 0,First,#;zo_abbr "zo_abbr" true true false 80 Text 0 0,First,#,zn178,ZCODE,0,49;zo_name "zo_name" true true false 114 Text 0 0,First,#,zn178,PRIM_USE,0,1;shape_leng "shape_leng" true true false 8 Double 0 0,First,#,K:\DataServices\Projects\Current_Projects\Housing\Zoning-to-Built-Form\Rightsizing Zoning\Muni Downloads\Zoning\zn178.shp,Shape_Leng,-1,-1',
    subtype="",
    expression="",
    match_fields=None,
    update_geometry="NOT_UPDATE_GEOMETRY",
    enforce_domains="NO_ENFORCE_DOMAINS"
)