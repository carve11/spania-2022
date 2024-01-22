# utilities.py
import gpxpy
import gpxpy.gpx
from geopy.distance import distance
import pandas as pd
import numpy as np
import json
import os


def read_and_process_track(route_meta_data, data_path):
    dfs = []
    for s, v in route_meta_data.items():
        fname = os.path.join(data_path, v['gpx_file'])
        gpx_data = read_gpx_data(fname)

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

    #df.loc[:, 'x'], df.loc[:, 'y'] = lnglat_to_meters(df.longitude,df.latitude)
    
    return df

def stage_summary(stage_df, stage_meta_data):
    '''
    Create and return dict of summary data for each stage
    '''
    data = {}

    for stage, grp in stage_df.groupby('stage'):
        data[stage] = {
            'stage_no': int(stage_meta_data[stage]['stage_no']),
            'start': stage_meta_data[stage]['start'],
            'finish': stage_meta_data[stage]['finish'],
        }
        data[stage].update(stage_data(grp))


    # Summary for all stages
    stage = 999

    first_no = stage_df['stage_no'].min()
    last_no = stage_df['stage_no'].max()

    start = stage_df.loc[stage_df['stage_no'] == first_no, 'stage'][0]
    finish = stage_df.loc[stage_df['stage_no'] == last_no, 'stage'][0]

    data['Total'] = {
        'stage_no': stage,
        'start': stage_meta_data[start]['start'],
        'finish': stage_meta_data[finish]['finish']
        }
    data['Total'].update(stage_data(stage_df, total_cum = True))

    data['stage_order'] = stage_order(stage_df)

    return data

def int_val(value):
    return int(np.round(value, 0))

def stage_data(df, total_cum = False):
    cum_distance_col = 'cum_distance'

    if total_cum:
        cum_distance_col = 'total_cum_dist'

    ascent_mask = df['elevation_diff'] >= 0
    decent_mask = df['elevation_diff'] <= 0

    data = {
        'distance': int_val(df[cum_distance_col].max()),
        'ascent': int_val(df[ascent_mask]['elevation_diff'].sum()),
        'decent': abs(int_val(df[decent_mask]['elevation_diff'].sum())),
        'min_elevation': int_val(df['elevation'].min()),
        'max_elevation': int_val(df['elevation'].max()),
    }

    return data

def geojson_data(df, summary):
    '''
    Create and return geojson data for MapBox map:
        - geojson with stages lng, lat 
        - geojson with start, finish point data
    '''
    geo_stages = geojson_stages(df, summary)
    geo_start_finish = geojson_start_finish(df, summary)

    return {'stages': geo_stages, 'start_finish': geo_start_finish}

def geojson_stages(df, summary):
    '''
    Create geojson FeatureCollection of each stage lng, lat
    Add property hover tooltip
    '''
    geojson = {'type': 'FeatureCollection', 'features': []}
    
    for i, stage in enumerate(summary['stage_order']):
        subdf = df[df['stage'] == stage]
        feature = {
            'type': 'Feature', 
            'id': i,
            'properties': {},
            'geometry': {
                'type':'LineString',
                'coordinates':[]
            }
        }
        
        feature['geometry']['coordinates'] = json.loads(
            subdf[['longitude', 'latitude']]
                .round(6)
                .to_json(orient = 'values')
            )
        
        tooltip = f"{stage}: {summary[stage]['start']} - "
        tooltip += f"{summary[stage]['finish']}, "
        tooltip += f"{summary[stage]['distance']} km"

        feature['properties']['stage'] = stage
        feature['properties']['tooltip'] = tooltip

        geojson['features'].append(feature)
    
    return geojson

def geojson_start_finish(df, summary):
    '''
    Create and return geojson FeatureCollection of summary data of each stage.
    Used for start and finish Markers on MapBox map.
    '''
    geojson = {'type': 'FeatureCollection', 'features': []}

    for stage, data in summary.items():
        if df[df['stage'] == stage].empty:
            continue

        feature = point_feature(df, stage, data, 'start')
        geojson['features'].append(feature)

        feature = point_feature(df, stage, data, 'finish')
        geojson['features'].append(feature)

    return geojson

def point_feature(df, stage, data, location_type):
    '''
    Create and return Point type GeoJSON feature.
    Extract coordinates from stages df containing log, lat based on 
    location_type: start (index = 0) or finish (last index).
    '''
    feature = {
        'type': 'Feature', 
        'properties': {},
        'geometry': {
            'type':'Point'
        }
    }
    
    idx = 0
    if location_type == 'finish':
        idx = -1

    coord = df.loc[df['stage'] == stage, ['longitude', 'latitude']].round(6)
    coord = coord.iloc[idx, :].tolist()

    feature['geometry']['coordinates'] = coord
    feature['properties']['stage'] = stage
    feature['properties']['tooltip'] = data[location_type]
    feature['properties']['location_type'] = location_type

    return feature

def stage_elevation_data2dict(df):
    '''
    Lookup dictionary of elevation data for each stage for profile plot
    for Bokeh varea glyph
    '''
    data = {}

    for stage, grp in df.groupby('stage'):
        data[stage] = {
            'x': grp['cum_distance'].tolist(),
            'y1': grp['elevation'].tolist()
        }

    return data

def stage_order(df):
    sub = df[['stage', 'stage_no']].drop_duplicates(subset=['stage_no'])
    
    return sub['stage'].tolist()
    
def read_gpx_data(fname):
    with open(fname, 'r') as gpx_file:
        data = gpxpy.parse(gpx_file)

    print('GPX file read,', os.path.basename(fname))

    return data

def read_meta_data(fname):
    with open(fname, 'r') as f:
        data = json.load(f)

    return data

def read_index_template(fname):
    with open(fname, 'r') as f:
        template = f.read()

    return template

