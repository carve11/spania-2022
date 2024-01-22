from bokeh.io import save, curdoc
from bokeh.embed import file_html
from bokeh.resources import CDN
from bokeh.layouts import column
from bokeh.models import Div, CustomJS, Select
import os
import utilities as utl
import visualization as viz
import config

ROOT_DIR = os.path.dirname(__file__)
TEMPLATES_DIR = 'templates'
DATA_DIR = 'data'
TRACKS_METADATA = 'stage_meta_data.json'

def stage_data():
    '''
    Load and process GPX data from indivual stages and return geojson data
    anad stage summary data
    '''
    fname = os.path.join(ROOT_DIR, DATA_DIR, TRACKS_METADATA)
    stage_meta_data = utl.read_meta_data(fname)

    data_path = os.path.join(ROOT_DIR, DATA_DIR)
    stages_df = utl.read_and_process_track(stage_meta_data, data_path)
    stage_summary = utl.stage_summary(stages_df, stage_meta_data)
    
    geojson = utl.geojson_data(stages_df, stage_summary)
    elevation_data = utl.stage_elevation_data2dict(stages_df)

    return geojson, elevation_data, stage_summary

def viz_elements(doc):
    '''
    Bokeh objects for visualization. Define CDS and create and add
    profile elevation plot to document
    '''
    srcs = viz.sources()
    p_elevation = viz.elevation_plot(srcs)

    doc.add_root(p_elevation)

def init_doc(doc, geojson, elevation_data, stage_summary):
    cb_doc_ready = CustomJS(
        args = {
            'mapbox_token': config.MAPBOX_TOKEN,
            'geojson': geojson,
            'elevation_data': elevation_data,
            'stage_summary': stage_summary
        },
      code = """
        initializeDocument(mapbox_token, geojson, elevation_data, stage_summary);
      """)
    doc.js_on_event("document_ready", cb_doc_ready)

def app(title):
    doc = curdoc()
    geojson, elevation_data, stage_summary = stage_data()
    viz_elements(doc)
    init_doc(doc, geojson, elevation_data, stage_summary)

    doc.template_variables['root'] = '.'
    stages = {k: v for k, v in stage_summary.items() if k != 'stage_order'}
    doc.template_variables['stages'] = stages

    doc.title = title

    return doc

def template(fname_tmplate):
    fname = os.path.join(ROOT_DIR, TEMPLATES_DIR, fname_tmplate)
    return utl.read_index_template(fname)

if __name__ == "__main__":
    INDEX_TEMPLATE = 'index.html'
    DOC_TITLE = 'Biketrip 2022'
    FOUTPUT = "index.html"

    doc = app(DOC_TITLE)
    index_template = template(INDEX_TEMPLATE)

    index_html = file_html(
        doc,
        resources = CDN,
        template = index_template,
        template_variables = doc.template_variables
        )

    with open(FOUTPUT, "w") as f:
        f.write(index_html)
    
    print("Wrote %s" % FOUTPUT)
