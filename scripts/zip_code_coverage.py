import pandas as pd
import geopandas as gpd
from typing import List
import math
from shapely.geometry import Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
import folium
from folium import GeoJson, Marker
from sklearn.cluster import DBSCAN
from sqlalchemy.exc import SQLAlchemyError
import numpy as np
import logging
import os
import sys

project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_dir = os.path.join(project_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'zip_code_coverage.log')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Add the project directory to the system path
sys.path.insert(0, project_dir)
from app.schemas import CoverageZipListSchema
from app.models import CoverageZipList
from app.dependencies import get_db_conn

class ZipCodeCoverage:
    def __init__(self, zip_csv_path: str, boundary_shapefile_path: str):
        # Load zip code data
        self.zip_df = pd.read_csv(zip_csv_path)
        
        # Rename columns for consistency and clarity
        self.zip_df = self.zip_df.rename(columns={
            'postal code': 'zip',
            'latitude': 'lat',
            'longitude': 'lon',
            'admin name1': 'state'
        })
        
        # Convert zip codes to strings and pad to 5 digits
        self.zip_df['zip'] = self.zip_df['zip'].astype(str).str.zfill(5)
        
        # Create geometry column from lat/lon
        self.zip_df['geometry'] = self.zip_df.apply(
            lambda row: Point(row['lon'], row['lat']), axis=1
        )
        
        # Load boundary data
        self.boundary_gdf = gpd.read_file(boundary_shapefile_path)
        self.boundary_gdf = self.boundary_gdf.to_crs(epsg=4326)  # Ensure WGS84 coordinate system
        
        # Convert zip data to GeoDataFrame
        self.zip_gdf = gpd.GeoDataFrame(
            self.zip_df, geometry='geometry', crs='EPSG:4326'
        )
        
        # UTM Zone matrix for states
        self.utm_zones = {
            'alabama': 'EPSG:32616',
            'alaska': 'EPSG:32606',
            'arizona': 'EPSG:32612',
            'arkansas': 'EPSG:32615',
            'california': 'EPSG:32611',
            'colorado': 'EPSG:32613',
            'connecticut': 'EPSG:32618',
            'delaware': 'EPSG:32618',
            'district of columbia': 'EPSG:32618',
            'florida': 'EPSG:32617',
            'georgia': 'EPSG:32617',
            'hawaii': 'EPSG:32604',
            'idaho': 'EPSG:32611',
            'illinois': 'EPSG:32616',
            'indiana': 'EPSG:32616',
            'iowa': 'EPSG:32615',
            'kansas': 'EPSG:32614',
            'kentucky': 'EPSG:32616',
            'louisiana': 'EPSG:32615',
            'maine': 'EPSG:32619',
            'maryland': 'EPSG:32618',
            'massachusetts': 'EPSG:32619',
            'michigan': 'EPSG:32616',
            'minnesota': 'EPSG:32615',
            'mississippi': 'EPSG:32616',
            'missouri': 'EPSG:32615',
            'montana': 'EPSG:32612',
            'nebraska': 'EPSG:32614',
            'nevada': 'EPSG:32611',
            'new hampshire': 'EPSG:32619',
            'new jersey': 'EPSG:32618',
            'new mexico': 'EPSG:32613',
            'new york': 'EPSG:32618',
            'north carolina': 'EPSG:32617',
            'north dakota': 'EPSG:32614',
            'ohio': 'EPSG:32617',
            'oklahoma': 'EPSG:32614',
            'oregon': 'EPSG:32610',
            'pennsylvania': 'EPSG:32617',
            'rhode island': 'EPSG:32619',
            'south carolina': 'EPSG:32617',
            'south dakota': 'EPSG:32614',
            'tennessee': 'EPSG:32616',
            'texas': 'EPSG:32614',
            'utah': 'EPSG:32612',
            'vermont': 'EPSG:32619',
            'virginia': 'EPSG:32617',
            'washington': 'EPSG:32610',
            'west virginia': 'EPSG:32617',
            'wisconsin': 'EPSG:32616',
            'wyoming': 'EPSG:32613'
        }

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in miles using Haversine formula"""
        R = 3958.8  # Earth's radius in miles
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    def get_coverage_points(self, area_name: str, radius: float) -> tuple[List[str], gpd.GeoDataFrame, gpd.GeoSeries, gpd.GeoSeries]:
        """Generate list of zip codes to cover the specified area with a fixed radius, return data for visualization"""
        # Define non-contiguous states and territories to exclude for CONUS
        non_conus_areas = [
            'Alaska', 'Hawaii', 'Puerto Rico', 'Guam', 'American Samoa',
            'United States Virgin Islands', 'Commonwealth of the Northern Mariana Islands'
        ]
        
        # Filter boundary for specified area
        if area_name.lower() == 'conus':
            area_boundary = self.boundary_gdf[~self.boundary_gdf['NAME'].isin(non_conus_areas)]
        elif area_name.lower() == 'united states':
            area_boundary = self.boundary_gdf
        else:
            area_boundary = self.boundary_gdf[self.boundary_gdf['NAME'].str.lower() == area_name.lower()]
            if area_boundary.empty:
                return [f"No boundary found for {area_name}"], None, None, None
        
        # Union of all boundaries for the area
        area_geom = unary_union(area_boundary.geometry)
        
        # Filter zip codes based on area_name
        potential_zips = self.zip_gdf
        if area_name.lower() == 'conus':
            potential_zips = potential_zips[~potential_zips['state'].isin(non_conus_areas)]
        elif area_name.lower() != 'united states':
            potential_zips = potential_zips[potential_zips['state'].str.lower() == area_name.lower()]
        
        # Further filter zip codes within or near the area using a bounding box
        minx, miny, maxx, maxy = area_geom.bounds
        potential_zips = potential_zips[
            (potential_zips['lon'].between(minx - 1.0, maxx + 1.0)) &
            (potential_zips['lat'].between(miny - 1.0, maxy + 1.0))
        ]
        
        if potential_zips.empty:
            return ["No zip codes found within the bounding box"], None, None, None
        
        # Convert to GeoDataFrame for spatial operations
        potential_zips = gpd.GeoDataFrame(
            potential_zips, geometry='geometry', crs='EPSG:4326'
        )
        
        # Determine appropriate projected CRS based on area
        if area_name.lower() in ['conus', 'united states']:
            projected_crs = 'EPSG:5070'  # Albers Equal Area Conic for CONUS or USA
        else:
            projected_crs = self.utm_zones.get(area_name.lower(), 'EPSG:5070')
        
        # Reproject data to the projected CRS for all spatial operations
        potential_zips_projected = potential_zips.to_crs(projected_crs)
        area_geom_projected = gpd.GeoSeries([area_geom], crs='EPSG:4326').to_crs(projected_crs).iloc[0]
        
        # Calculate density to prioritize rural zip codes early
        search_radius_miles = 50  # Radius to calculate density
        search_radius_meters = search_radius_miles * 1609.34
        potential_zips_projected['buffer_density'] = potential_zips_projected.geometry.buffer(search_radius_meters)
        
        # Convert buffer_density to a GeoSeries and set its CRS
        potential_zips_projected['buffer_density'] = gpd.GeoSeries(
            potential_zips_projected['buffer_density'], crs=projected_crs
        )
        
        # Build an STRtree for density calculation
        density_buffers = potential_zips_projected['buffer_density'].tolist()
        density_index = STRtree(density_buffers)
        
        # Calculate density for each zip code
        density_counts = []
        for idx, row in potential_zips_projected.iterrows():
            nearby_indices = density_index.query(row['buffer_density'])
            count = len(set(nearby_indices)) - 1  # Subtract 1 to exclude the zip code itself
            density_counts.append(count)
        
        potential_zips_projected['density'] = density_counts
        
        # Sort potential_zips_projected by density (ascending) to prioritize rural zip codes
        potential_zips_projected = potential_zips_projected.sort_values(by='density', ascending=True)
        # Reset indices to ensure consecutive indices after sorting
        potential_zips_projected = potential_zips_projected.reset_index(drop=True)
        
        # Create buffer circles around each zip code with a fixed radius (radius in meters)
        radius_meters = radius * 1609.34  # Convert miles to meters
        potential_zips_projected['buffer'] = potential_zips_projected.geometry.buffer(radius_meters)
        potential_zips_projected['buffer'] = gpd.GeoSeries(
            potential_zips_projected['buffer'], crs=projected_crs
        )
        
        # Calculate the area of each buffer in the projected CRS for the minimum coverage constraint
        buffer_areas = potential_zips_projected['buffer'].area
        buffer_areas.index = potential_zips_projected.index
        
        # Build an STRtree spatial index for the buffers (in projected CRS)
        buffer_geometries = potential_zips_projected['buffer'].tolist()
        buffer_index = STRtree(buffer_geometries)
        
        selected_zips = []
        selected_zips_gdf = gpd.GeoDataFrame(columns=['zip', 'geometry', 'buffer'], crs=projected_crs)
        uncovered_area = area_geom_projected
        covered_area = None
        
        # Greedy algorithm with increased overlap penalty and minimum coverage constraint
        overlap_penalty = 2.0  # Increased penalty to reduce overlap
        min_coverage_fraction = 0.05  # Minimum fraction of buffer area that must be new coverage
        
        while not potential_zips_projected.empty and uncovered_area.area > 0:
            best_zip = None
            best_effective_coverage = float('-inf')
            best_new_coverage_area = 0
            best_buffer = None
            best_geometry = None
            
            # Use STRtree to find indices of buffers that potentially intersect with uncovered_area
            candidate_indices = buffer_index.query(uncovered_area)
            
            if len(candidate_indices) == 0:
                pass
            else:
                # Filter potential_zips_projected to only the candidates
                candidates = potential_zips_projected.iloc[candidate_indices]
                
                for idx, row in candidates.iterrows():
                    new_coverage = uncovered_area.intersection(row['buffer'])
                    new_coverage_area = new_coverage.area
                    
                    if new_coverage_area == 0:
                        continue
                    
                    # Access buffer_area using the DataFrame's index
                    buffer_area = buffer_areas.loc[row.name]
                    coverage_fraction = new_coverage_area / buffer_area
                    if coverage_fraction < min_coverage_fraction:
                        continue
                    
                    if covered_area is not None:
                        overlap_area = row['buffer'].intersection(covered_area).area
                        effective_coverage = new_coverage_area - (overlap_penalty * overlap_area)
                    else:
                        effective_coverage = new_coverage_area
                    
                    if effective_coverage > best_effective_coverage or (effective_coverage == best_effective_coverage and new_coverage_area > best_new_coverage_area):
                        best_zip = row['zip']
                        best_effective_coverage = effective_coverage
                        best_new_coverage_area = new_coverage_area
                        best_buffer = row['buffer']
                        best_geometry = row['geometry']
            
            # Fallback: find the nearest zip code if no direct coverage
            if best_zip is None and uncovered_area.area > 0:
                centroid = uncovered_area.centroid
                
                best_effective_coverage = float('-inf')
                best_distance = float('inf')
                
                candidate_indices = buffer_index.query(uncovered_area)
                if len(candidate_indices) == 0:
                    # Use all zip codes for fallback
                    candidate_indices = list(range(len(potential_zips_projected)))
                
                candidates = potential_zips_projected.iloc[candidate_indices]
                
                for idx, row in candidates.iterrows():
                    new_coverage = uncovered_area.intersection(row['buffer'])
                    new_coverage_area = new_coverage.area
                    
                    if new_coverage_area == 0:
                        continue
                    
                    # Access buffer_area using the DataFrame's index
                    buffer_area = buffer_areas.loc[row.name]
                    coverage_fraction = new_coverage_area / buffer_area
                    if coverage_fraction < min_coverage_fraction:
                        continue
                    
                    if covered_area is not None:
                        overlap_area = row['buffer'].intersection(covered_area).area
                        effective_coverage = new_coverage_area - (overlap_penalty * overlap_area)
                    else:
                        effective_coverage = new_coverage_area
                    
                    distance = row['geometry'].distance(centroid)
                    
                    if effective_coverage > best_effective_coverage or (effective_coverage == best_effective_coverage and distance < best_distance):
                        best_zip = row['zip']
                        best_effective_coverage = effective_coverage
                        best_new_coverage_area = new_coverage_area
                        best_buffer = row['buffer']
                        best_geometry = row['geometry']
                        best_distance = distance
                
                if best_zip is None:
                    break
            
            if best_zip is None:
                break
            
            selected_zips.append(best_zip)
            new_row = gpd.GeoDataFrame(
                {'zip': [best_zip], 'geometry': [best_geometry], 'buffer': [best_buffer]},
                crs=projected_crs
            )
            selected_zips_gdf = pd.concat([selected_zips_gdf, new_row], ignore_index=True)
            uncovered_area = uncovered_area.difference(best_buffer)
            if covered_area is None:
                covered_area = best_buffer
            else:
                covered_area = unary_union([covered_area, best_buffer])
            
            # Remove the selected zip from potential_zips_projected
            selected_idx = potential_zips_projected[potential_zips_projected['zip'] == best_zip].index[0]
            potential_zips_projected = potential_zips_projected.drop(index=selected_idx)
            buffer_areas = buffer_areas.drop(index=selected_idx)
            
            # Reset indices to ensure alignment
            potential_zips_projected = potential_zips_projected.reset_index(drop=True)
            buffer_areas = buffer_areas.reset_index(drop=True)
            
            # Rebuild the STRtree with the remaining buffers
            buffer_geometries = potential_zips_projected['buffer'].tolist()
            buffer_index = STRtree(buffer_geometries)
        
        # Post-selection: cluster selected zip codes and replace clusters with fewer zip codes
        if not selected_zips_gdf.empty:
            # Reproject to EPSG:4326 for clustering (DBSCAN uses degrees)
            selected_zips_gdf_4326 = selected_zips_gdf.to_crs('EPSG:4326')
            coords = np.array([[row['geometry'].x, row['geometry'].y] for _, row in selected_zips_gdf_4326.iterrows()])
            
            # Use DBSCAN to cluster zip codes (eps=25 miles, converted to degrees for EPSG:4326)
            eps_miles = 25
            eps_degrees = eps_miles / 69
            clustering = DBSCAN(eps=eps_degrees, min_samples=2).fit(coords)
            selected_zips_gdf['cluster'] = clustering.labels_
            
            # Process each cluster
            new_selected_zips = []
            new_selected_zips_gdf = gpd.GeoDataFrame(columns=['zip', 'geometry', 'buffer'], crs=projected_crs)
            
            # Handle non-clustered zip codes (cluster label -1)
            non_clustered = selected_zips_gdf[selected_zips_gdf['cluster'] == -1]
            if not non_clustered.empty:
                new_selected_zips.extend(non_clustered['zip'].tolist())
                new_selected_zips_gdf = pd.concat([new_selected_zips_gdf, non_clustered[['zip', 'geometry', 'buffer']]], ignore_index=True)
            
            # Process each cluster
            for cluster_label in set(clustering.labels_):
                if cluster_label == -1:
                    continue
                cluster_gdf = selected_zips_gdf[selected_zips_gdf['cluster'] == cluster_label]
                if len(cluster_gdf) <= 1:
                    new_selected_zips.extend(cluster_gdf['zip'].tolist())
                    new_selected_zips_gdf = pd.concat([new_selected_zips_gdf, cluster_gdf[['zip', 'geometry', 'buffer']]], ignore_index=True)
                    continue
                
                # Find the centroid of the cluster
                centroid = unary_union(cluster_gdf['geometry']).centroid
                
                # Find the zip code closest to the centroid from the original potential_zips
                potential_zips_projected = potential_zips.to_crs(projected_crs)
                potential_zips_projected['distance'] = potential_zips_projected.geometry.distance(centroid)
                closest_zip = potential_zips_projected.loc[potential_zips_projected['distance'].idxmin()]
                
                # Create a buffer for the closest zip code
                closest_buffer = closest_zip.geometry.buffer(radius_meters)
                
                # Add the closest zip code to the new selection
                new_row = gpd.GeoDataFrame(
                    {'zip': [closest_zip['zip']], 'geometry': [closest_zip.geometry], 'buffer': [closest_buffer]},
                    crs=projected_crs
                )
                new_selected_zips.append(closest_zip['zip'])
                new_selected_zips_gdf = pd.concat([new_selected_zips_gdf, new_row], ignore_index=True)
            
            # Verify coverage after clustering
            selected_zips_gdf = new_selected_zips_gdf
            selected_zips = new_selected_zips
            
            # Recompute uncovered area
            if not selected_zips_gdf.empty:
                covered_area = unary_union(selected_zips_gdf['buffer'])
                uncovered_area = area_geom_projected.difference(covered_area)
                
                # If there are uncovered areas, run the greedy algorithm again to fill gaps
                if uncovered_area.area > 0:
                    potential_zips_projected = potential_zips.to_crs(projected_crs)
                    potential_zips_projected['buffer'] = potential_zips_projected.geometry.buffer(radius_meters)
                    potential_zips_projected['buffer'] = gpd.GeoSeries(
                        potential_zips_projected['buffer'], crs=projected_crs
                    )
                    potential_zips_projected = potential_zips_projected[~potential_zips_projected['zip'].isin(selected_zips)]
                    potential_zips_projected = potential_zips_projected.reset_index(drop=True)
                    
                    buffer_geometries = potential_zips_projected['buffer'].tolist()
                    buffer_index = STRtree(buffer_geometries)
                    buffer_areas = potential_zips_projected['buffer'].area
                    buffer_areas.index = potential_zips_projected.index
                    
                    while not potential_zips_projected.empty and uncovered_area.area > 0:
                        best_zip = None
                        best_effective_coverage = float('-inf')
                        best_new_coverage_area = 0
                        best_buffer = None
                        best_geometry = None
                        
                        candidate_indices = buffer_index.query(uncovered_area)
                        if len(candidate_indices) == 0:
                            break
                        
                        candidates = potential_zips_projected.iloc[candidate_indices]
                        
                        for idx, row in candidates.iterrows():
                            new_coverage = uncovered_area.intersection(row['buffer'])
                            new_coverage_area = new_coverage.area
                            
                            if new_coverage_area == 0:
                                continue
                            
                            buffer_area = buffer_areas.loc[row.name]
                            coverage_fraction = new_coverage_area / buffer_area
                            if coverage_fraction < min_coverage_fraction:
                                continue
                            
                            if covered_area is not None:
                                overlap_area = row['buffer'].intersection(covered_area).area
                                effective_coverage = new_coverage_area - (overlap_penalty * overlap_area)
                            else:
                                effective_coverage = new_coverage_area
                            
                            if effective_coverage > best_effective_coverage or (effective_coverage == best_effective_coverage and new_coverage_area > best_new_coverage_area):
                                best_zip = row['zip']
                                best_effective_coverage = effective_coverage
                                best_new_coverage_area = new_coverage_area
                                best_buffer = row['buffer']
                                best_geometry = row['geometry']
                        
                        if best_zip is None:
                            break
                        
                        selected_zips.append(best_zip)
                        new_row = gpd.GeoDataFrame(
                            {'zip': [best_zip], 'geometry': [best_geometry], 'buffer': [best_buffer]},
                            crs=projected_crs
                        )
                        selected_zips_gdf = pd.concat([selected_zips_gdf, new_row], ignore_index=True)
                        uncovered_area = uncovered_area.difference(best_buffer)
                        covered_area = unary_union(selected_zips_gdf['buffer'])
                        
                        selected_idx = potential_zips_projected[potential_zips_projected['zip'] == best_zip].index[0]
                        potential_zips_projected = potential_zips_projected.drop(index=selected_idx)
                        buffer_areas = buffer_areas.drop(index=selected_idx)
                        
                        potential_zips_projected = potential_zips_projected.reset_index(drop=True)
                        buffer_areas = buffer_areas.reset_index(drop=True)
                        
                        buffer_geometries = potential_zips_projected['buffer'].tolist()
                        buffer_index = STRtree(buffer_geometries)
        
        # Final post-selection: remove redundant zip codes
        if not selected_zips_gdf.empty:
            buffer_gs = gpd.GeoSeries(selected_zips_gdf['buffer'], crs=projected_crs)
            selected_zips_gdf['buffer_projected'] = buffer_gs
            
            for i in range(len(selected_zips_gdf) - 1, -1, -1):
                temp_gdf = selected_zips_gdf.drop(index=i)
                if not temp_gdf.empty:
                    temp_covered = unary_union(temp_gdf['buffer_projected'])
                    if temp_covered.contains(area_geom_projected):
                        selected_zips_gdf = selected_zips_gdf.drop(index=i)
                        selected_zips = selected_zips_gdf['zip'].tolist()
            
            # Drop the temporary buffer_projected column
            selected_zips_gdf = selected_zips_gdf.drop(columns=['buffer_projected'])
        
        # Reproject selected_zips_gdf to EPSG:4326 for visualization
        if not selected_zips_gdf.empty:
            # Store the original buffers in projected CRS for overlap calculation
            selected_zips_gdf['buffer_projected'] = selected_zips_gdf['buffer']
            # Reproject the GeoDataFrame to EPSG:4326
            selected_zips_gdf = selected_zips_gdf.to_crs('EPSG:4326')
            # Reproject the buffers to EPSG:4326 for visualization
            selected_zips_gdf['buffer'] = gpd.GeoSeries(selected_zips_gdf['buffer_projected'], crs=projected_crs).to_crs('EPSG:4326')
        
        # Convert uncovered area to GeoSeries for visualization
        uncovered_area_gs = gpd.GeoSeries([uncovered_area], crs=projected_crs).to_crs('EPSG:4326') if not uncovered_area.is_empty else gpd.GeoSeries()
        
        return selected_zips, selected_zips_gdf, gpd.GeoSeries([area_geom], crs='EPSG:4326'), uncovered_area_gs

    def visualize_coverage(self, area_name: str, selected_zips: List[str], selected_zips_gdf: gpd.GeoDataFrame, area_geom: gpd.GeoSeries, uncovered_area: gpd.GeoSeries, radius: float, output_file: str):
        """Visualize the selected zip codes, their coverage, and uncovered areas on an interactive map"""
        if not selected_zips or selected_zips_gdf.empty or area_geom.empty:
            print(f"Cannot visualize {area_name}: No data to display")
            return
        
        # Calculate the center of the area for map initialization
        minx, miny, maxx, maxy = area_geom.bounds.iloc[0]
        center_lat = (miny + maxy) / 2
        center_lon = (minx + maxx) / 2
        
        # Create a folium map centered on the area
        m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles='OpenStreetMap')
        
        # Add the area boundary
        GeoJson(
            area_geom.__geo_interface__,
            style_function=lambda x: {'fillColor': 'blue', 'color': 'blue', 'weight': 2, 'fillOpacity': 0.1}
        ).add_to(m)
        
        # Add uncovered areas (if any)
        if not uncovered_area.empty:
            GeoJson(
                uncovered_area.__geo_interface__,
                style_function=lambda x: {'fillColor': 'red', 'color': 'red', 'weight': 1, 'fillOpacity': 0.5}
            ).add_to(m)
        
        # Add the selected zip codes and their buffers
        for idx, row in selected_zips_gdf.iterrows():
            lat = row['geometry'].y
            lon = row['geometry'].x
            popup_text = f"Zip: {row['zip']}"
            Marker(
                location=[lat, lon],
                popup=popup_text,
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_child(folium.Popup(popup_text)).add_to(m)
            
            GeoJson(
                row['buffer'].__geo_interface__,
                style_function=lambda x: {'fillColor': 'green', 'color': 'green', 'weight': 1, 'fillOpacity': 0.3}
            ).add_to(m)
        
        # Calculate overlap area for quantitative analysis
        if not selected_zips_gdf.empty:
            # Determine the appropriate projected CRS for area calculations
            if area_name.lower() in ['conus', 'united states']:
                projected_crs = 'EPSG:5070'
            else:
                projected_crs = self.utm_zones.get(area_name.lower(), 'EPSG:5070')
            
            # Use the original buffers in the projected CRS (before reprojection to EPSG:4326)
            buffer_gs_projected = gpd.GeoSeries(selected_zips_gdf['buffer_projected'], crs=projected_crs)
            
            # Validate geometries to avoid invalid geometry warnings
            buffer_gs_projected = buffer_gs_projected.buffer(0)  # Buffer by 0 to fix invalid geometries
            
            # Calculate total area of individual buffers (in square meters)
            total_buffer_area = buffer_gs_projected.area.sum()
            
            # Calculate the area of the union of all buffers
            union_buffer = unary_union(buffer_gs_projected)
            if not union_buffer.is_valid:
                union_buffer = union_buffer.buffer(0)  # Fix invalid geometry
            union_buffer_area = union_buffer.area
            
            # Overlap area in square meters
            overlap_area_m2 = total_buffer_area - union_buffer_area
            
            # Convert to square miles (1 square meter = 3.861e-7 square miles)
            overlap_area_miles2 = overlap_area_m2 * 3.861e-7
            print(f"Total overlap area: {overlap_area_miles2:.2f} square miles")
        
        # Clean up the GeoDataFrame by dropping the buffer_projected column
        if 'buffer_projected' in selected_zips_gdf.columns:
            selected_zips_gdf = selected_zips_gdf.drop(columns=['buffer_projected'])
        
        # Save the map to an HTML file
        m.save(output_file)
        print(f"Map saved to {output_file}")

def main():
    # File paths
    all_zips = []
    try:
        db = next(get_db_conn())
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        zip_csv_path = os.path.join(project_dir, 'data', 'USZipsWithLatLon_20231227.csv')
        boundary_shapefile_path = os.path.join(project_dir, 'data', 'cb_2023_us_state_500k','cb_2023_us_state_500k.shp')
        states = ['New Mexico', 'South Dakota', 'California', 'Kentucky', 'Alabama', 'Georgia', 'Arkansas', 'Pennsylvania', 'Missouri', 'Colorado', 'Utah', 'Oklahoma', 'Tennessee', 'Wyoming', 'New York', 'Indiana', 'Kansas', 'Idaho', 'Alaska', 'Nevada', 'Illinois', 'Vermont', 'Minnesota', 'Iowa', 'South Carolina', 'New Hampshire', 'Delaware', 'District of Columbia', 'Connecticut', 'Michigan', 'Massachusetts', 'Florida', 'New Jersey', 'North Dakota', 'Maryland', 'Maine', 'Hawaii', 'Rhode Island', 'Montana', 'Arizona', 'Nebraska', 'Washington', 'Texas', 'Ohio', 'Wisconsin', 'Oregon', 'Mississippi', 'North Carolina', 'Virginia', 'West Virginia', 'Louisiana']
        coverage = ZipCodeCoverage(zip_csv_path, boundary_shapefile_path)
        logging.info("Starting coverage analysis")
        states.sort()
        radius = 25
        for state in states:
            logging.info(f"Analyzing coverage for {state}")
            zips, zips_gdf, area, uncovered = coverage.get_coverage_points(state, radius)
            
            zip_list = ",".join(zips)
            zip_schema = CoverageZipListSchema(params=str({'area': state, 'radius': radius}), zips=zip_list)
            zip_model = CoverageZipList(**zip_schema.model_dump())

            db.add(zip_model)
            db.commit()
            
            all_zips.extend(zips)
            logging.info(f"Zip codes selected: {zips}")
            logging.info(f"Number of zip codes: {len(zips)}")
            coverage.visualize_coverage(state, zips, zips_gdf, area, uncovered, radius, f"{project_dir}/data/{state}_coverage.html")
            logging.info(f"Coverage analysis for {state} complete")
            logging.info("===================================")
        logging.info("Coverage analysis complete")
        logging.info(f"Total zip codes selected: {len(all_zips)}")
        logging.info(f"Unique zip codes selected: {len(set(all_zips))}")
        zip_list = ",".join(all_zips)
        zip_schema = CoverageZipListSchema(params=str({'area': states, 'radius': radius}), zips=zip_list)
        zip_model = CoverageZipList(**zip_schema.model_dump())

        db.add(zip_model)
        db.commit()
        logging.info("===================================")
        logging.info(f"Complete list of zip codes: {set(all_zips)}")
    except SQLAlchemyError as e:
        logging.error(f"SQLAlchemyError: {e}")
        if db:
            db.rollback()
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()