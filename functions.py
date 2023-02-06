# functions.py
import gpxpy
import gpxpy.gpx
from geopy.distance import distance
import pandas as pd
import numpy as np
import json
import os

GPX_FILE_DIR = 'data'
TEMPLATES_DIR = 'templates'

root_dir = os.path.dirname(__file__)

def lnglat_to_meters(longitude, latitude):
    """
    https://github.com/bokeh/bokeh/issues/10009
    Projects the given (longitude, latitude) values into Web Mercator
    coordinates (meters East of Greenwich and meters North of the Equator).

    Longitude and latitude can be provided as scalars, Pandas columns,
    or Numpy arrays, and will be returned in the same form.  Lists
    or tuples will be converted to Numpy arrays.

    Examples:
       easting, northing = lnglat_to_meters(-74,40.71)

       easting, northing = lnglat_to_meters(np.array([-74]),np.array([40.71]))

       df=pandas.DataFrame(dict(longitude=np.array([-74]),latitude=np.array([40.71])))
       df.loc[:, 'longitude'], df.loc[:, 'latitude'] = lnglat_to_meters(df.longitude,df.latitude)
    """
    if isinstance(longitude, (list, tuple)):
        longitude = np.array(longitude)
    if isinstance(latitude, (list, tuple)):
        latitude = np.array(latitude)

    origin_shift = np.pi * 6378137
    easting = longitude * origin_shift / 180.0
    northing = np.log(np.tan((90 + latitude) * np.pi / 360.0)) * origin_shift / np.pi

    return (easting, northing)

def read_and_process_track(route_meta_data):
    dfs = []
    for s, v in route_meta_data.items():
        gpx_data = read_gpx_file(v['gpx_file'])
        route_df = gpx_data_to_df(gpx_data)
        route_df = process_track_data(route_df)
        route_df['stage'] = s
        route_df['stage_no'] = int(v['stage_no'])
        dfs.append(route_df)

    df = pd.concat(dfs)

    # add total cumulative for all stages
    df.index.name = 'index'
    df = df.reset_index()
    df = df.sort_values(by = ['stage_no', 'index'])
    df['total_cum_dist'] = df['distance'].cumsum()
    df = df.set_index('index')

    return df

def read_gpx_file(fname):
    f = os.path.join(root_dir, GPX_FILE_DIR, fname)
    with open(f, 'r') as gpx_file:
        data = gpxpy.parse(gpx_file)

    print('GPX file read,', fname)

    return data

def gpx_data_to_df(gpx_obj):
    route_info = []
    trackno = 0
    for track in gpx_obj.tracks:
        segmentno = 0
        for segment in track.segments:
            for point in segment.points:
                route_info.append({
                    'track': f'track{trackno}',
                    'segment': f'segment{segmentno}',
                    'latitude': point.latitude,
                    'longitude': point.longitude,
                    'elevation': point.elevation
                })
            segmentno += 1
        trackno += 1
    return pd.DataFrame(route_info)

def process_track_data(df):
    df['elevation_diff'] = df['elevation'].diff()

    df['point'] = df.apply(
        lambda row: (row['latitude'], row['longitude']), axis = 1
        )
    df['point_next'] = df['point'].shift(1)
    df.loc[df['point_next'].isna(), 'point_next'] = None
    df['distance'] = df.apply(
        lambda row: distance(row['point'], row['point_next']).km 
        if row['point_next'] is not None else 0,
        axis = 1
        )

    df['cum_distance'] = df['distance'].cumsum()
    df = df.drop(columns = ['point', 'point_next'])

    df.loc[:, 'x'], df.loc[:, 'y'] = lnglat_to_meters(df.longitude,df.latitude)
    
    return df

def read_meta_data(fname):
    f = os.path.join(root_dir, GPX_FILE_DIR, fname)
    with open(f, 'r') as f:
        data = json.load(f)

    return data

def read_index_template(fname):
    f = os.path.join(root_dir, TEMPLATES_DIR, fname)
    with open(f, 'r') as f:
        template = f.read()

    return template