import geopandas as gpd
import os

def inspect_shapefile(shapefile_path: str):
    try:
        # Load the shapefile
        gdf = gpd.read_file(shapefile_path)
        
        # Print basic information about the shapefile
        print("=== Shapefile Overview ===")
        print(f"Number of features: {len(gdf)}")
        print(f"Coordinate Reference System (CRS): {gdf.crs}")
        print(f"Geometry types: {gdf.geom_type.unique()}")
        
        # Print the bounding box of the data
        print("\n=== Bounding Box ===")
        print(gdf.total_bounds)  # [minx, miny, maxx, maxy]
        
        # Print the first few rows to see the data
        print("\n=== First 5 Rows ===")
        print(gdf.head())
        
        # Print column names and their data types
        print("\n=== Columns and Data Types ===")
        print(gdf.dtypes)
        
        # Check for 'name' or 'NAME' column (case-insensitive)
        name_col = next((col for col in gdf.columns if col.lower() == 'name'), None)
        if name_col:
            print(f"\n=== Unique Values in '{name_col}' Column ===")
            print(gdf[name_col].unique())
        else:
            print("\nNo 'name' column found. Available columns:")
            print(list(gdf.columns))
        
    except Exception as e:
        print(f"Error loading shapefile: {e}")

def main():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    shapefile_path = os.path.join(project_dir, 'data', 'cb_2023_us_state_500k', 'cb_2023_us_state_500k.shp')
    
    inspect_shapefile(shapefile_path)

if __name__ == "__main__":
    main()