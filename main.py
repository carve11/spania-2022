import pandas as pd
import numpy as np
import os
from bokeh.document import Document
from bokeh.io import curdoc
from bokeh.embed import file_html
from bokeh.resources import CDN
from bokeh.layouts import row, column
import visualization as viz
from functions import lnglat_to_meters, read_meta_data, read_index_template
from functions import read_and_process_track

FOUTPUT = "index.html"
TRACKS_METADATA = 'stage_meta_data.json'
INDEX_TEMPLATE = 'index_template.html'

def routes_data_dict(df, meta_data):
    '''
    Dictionary of data for ColumnDataSource for stages on the map plot.
    Setup as dict with x,y as list of lists for Bokeh multiline glyph.
    '''
    data = {'xs': [], 'ys': [], 'label': [], 'stage': []}

    for stage, grp in df.groupby('stage'):
        data['xs'].append(grp['x'].tolist())
        data['ys'].append(grp['y'].tolist())

        stage_info = meta_data[stage]
        tooltip = '{}: {} - {}, {} km'.format(
            stage_info['name'],
            stage_info['start'],
            stage_info['finish'],
            int(np.round(grp['cum_distance'].max(), 0))
        )
        data['label'].append(tooltip)
        data['stage'].append(stage)

    return data

def create_start_end_data(route_meta_data, route_df):
    '''
    Dataframe of data for ColumnDataSource for start and finish markers on 
    map plot.
    '''
    meta_data_df = pd.DataFrame(route_meta_data).T
    meta_data_df.index.name = 'stage'
    meta_data_df = meta_data_df.reset_index()
    meta_data_df = meta_data_df.melt(
        id_vars = ['stage'], value_vars = ['start', 'finish'],
        var_name = 'marker_type', value_name = 'label'
        )
    meta_data_df['marker'] = 'circle'
    meta_data_df['color'] = 'green'

    m = meta_data_df['marker_type'] == 'finish'
    meta_data_df.loc[m, 'marker'] = 'square'
    meta_data_df.loc[m, 'color'] = 'red'

    meta_data_df = meta_data_df.groupby('stage').apply(
        lambda df: add_xy(df, route_df)
        )

    return meta_data_df[['label', 'marker', 'color', 'x', 'y']]

def add_xy(df, route_df):
    stage = df['stage'].tolist()[0]
    sub_df = route_df[route_df['stage'] == stage].reset_index(drop = True)
    if sub_df.empty:
        return

    coord = lat_long_pair_to_list(sub_df, 0)
    df.loc[df['marker_type'] == 'start', ['x', 'y']] = coord

    coord = lat_long_pair_to_list(sub_df, sub_df.index.max())
    df.loc[df['marker_type'] == 'finish', ['x', 'y']] = coord

    return df

def lat_long_pair_to_list(df, idx_no):
    return df.loc[idx_no, ['x', 'y']].tolist()

def setup_elevation_data(df):
    '''
    Dictionary of elevation data for ColumnDataSource
    '''
    data = {'x': [], 'y1': [], 'stage': []}

    for stage, grp in df.groupby('stage'):
        data['x'].append(grp['cum_distance'].tolist())
        data['y1'].append(grp['elevation'].tolist())
        data['stage'].append(stage)

    return data

def setup_route_data(df, route_meta_data):
    '''
    Dictionary of summary data for each stage and a total for all stages.
    Used for Jinja2 index template variables.
    '''
    data = individual_stage_summary(df, route_meta_data)
    data['Total'] = all_stages_summary(df, route_meta_data)

    return data

def individual_stage_summary(df, route_meta_data):
    data = {}

    for stage, grp in df.groupby('stage'):
        data[stage] = {
            'stage_no': int(route_meta_data[stage]['stage_no']),
            'start': route_meta_data[stage]['start'],
            'finish': route_meta_data[stage]['finish'],
        }
        data[stage].update(route_values_data(grp))

    return data

def route_values_data(df, total_cum = False):
    cum_distance_col = 'cum_distance'
    if total_cum:
        cum_distance_col = 'total_cum_dist'

    data = {
        'distance': int(np.round(df[cum_distance_col].max(), 0)),
        'ascent': int(np.round(
            df[df['elevation_diff'] >= 0]['elevation_diff'].sum(),
            0
        )),
        'decent': int((-1)*np.round(
            df[df['elevation_diff'] <= 0]['elevation_diff'].sum(),
            0
        )),
        'min_elevation': int(np.round(df['elevation'].min(), 0)),
        'max_elevation': int(np.round(df['elevation'].max(), 0)),
    }

    return data

def all_stages_summary(df, route_meta_data):
    start = df.loc[df['stage_no'] == df['stage_no'].min(), 'stage'][0]
    finish = df.loc[df['stage_no'] == df['stage_no'].max(), 'stage'][0]

    data = {
        'stage_no': 999,
        'start': route_meta_data[start]['start'],
        'finish': route_meta_data[finish]['finish']
        }
    data.update(route_values_data(df, total_cum = True))

    return data

def app():
    route_meta_data = read_meta_data(TRACKS_METADATA)
    routes_df = read_and_process_track(route_meta_data)
    route_data = setup_route_data(routes_df, route_meta_data)
    
    srcs = viz.create_sources()
    srcs['routes'].data = routes_data_dict(routes_df, route_meta_data)
    srcs['start_finish'].data = create_start_end_data(route_meta_data, routes_df)
    srcs['elevation_data'].data = setup_elevation_data(routes_df)

    p_map = viz.create_map_figure(srcs)
    p_elevation = viz.elevation_plot(
        srcs['elevation'], srcs['elevation_stage'],
        srcs['marker_elevation'], 'elevation'
        )
    
    viz.add_callback(srcs, p_elevation, p_map)

    doc = Document()
    doc = curdoc()
    doc.add_root(p_map)
    doc.add_root(p_elevation)
    template_variables = {'stages': route_data}

    return doc, template_variables

if __name__ == "__main__":
    doc, template_variables = app()
    doc.validate()
    index_template = read_index_template(INDEX_TEMPLATE)
    index_html = file_html(
        doc,
        resources = CDN,
        title = 'Biketrip 2022',
        template = index_template,
        template_variables = template_variables
        )

    with open(FOUTPUT, "w") as f:
        f.write(index_html)
    
    print("Wrote %s" % FOUTPUT)
