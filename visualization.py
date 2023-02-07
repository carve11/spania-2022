# visualization.py
from bokeh.plotting import figure
from bokeh.models import TapTool, ColumnDataSource
from bokeh.models import CustomJS, HoverTool, PrintfTickFormatter
from bokeh.models import Range1d, Div, HTMLLabel, Button
from bokeh.layouts import row, column
from functions import lnglat_to_meters
import xyzservices.providers as xyz
import config

FONTSIZE = '14px'
MAX_PLOT_WIDTH = 800

def create_map_figure(srcs):
    low_left = lnglat_to_meters(-7.3, 42.4)
    upper_right = lnglat_to_meters(-4.1, 44.1)

    p = figure(
        max_width = MAX_PLOT_WIDTH,
        sizing_mode = 'stretch_both',
        tools = ['pan', 'wheel_zoom'],
        active_scroll = 'wheel_zoom',
        toolbar_location = None,
        x_axis_type = 'mercator',
        y_axis_type = 'mercator',
        x_range = (low_left[0], upper_right[0]),
        y_range = (low_left[1], upper_right[1]),
        name = 'map'
     )

    p.grid.grid_line_color = None
    p.axis.visible = False

    maptile = xyz.MapBox(
        id = "mapbox/streets-v11",
        accessToken = config.MAPBOX_TOKEN
        )

    p.add_tile(maptile, retina = True)

    p.add_tools(TapTool(name = 'taptool'))

    r_routes = p.multi_line(
        xs = 'xs', ys = 'ys',
        source = srcs['routes'],
        line_color = 'blue',
        line_width = 4,
        hover_line_color = 'firebrick',
        selection_line_color = 'firebrick',
        nonselection_line_width = 2,
        nonselection_line_alpha = 0.5,
        nonselection_line_color = 'blue' 
    )

    p.scatter(
        x = 'x', y = 'y',
        line_color = 'white',
        size = 12,
        line_width = 2,
        fill_color = 'color',
        marker = 'marker',
        source = srcs['start_finish']
        )

    p.circle(
        x = 'x', y = 'y',
        line_color = 'firebrick',
        fill_color = 'white',
        size = 9,
        line_width = 2,
        source = srcs['marker_map'],
        name = 'marker_map'
        )

    p.add_tools(HoverTool(
        tooltips = [("", "@label")]
        ))

    route_hover = HoverTool(
        tooltips = None,
        line_policy = 'none',
        renderers = [r_routes],
        name = 'route_hover'
    )
    p.add_tools(route_hover)

    return p

def elevation_plot(src_elev, src_elev_stage, src_hover, name):
    plot = figure(
        height = 200,
        max_width = MAX_PLOT_WIDTH,
        min_width = 300,
        sizing_mode = 'stretch_width',
        tools = "", 
        toolbar_location = None,
        name = name, 
        y_range = Range1d(0, 1),
        x_range = Range1d(0, 1),
        visible = True
        )

    elevation_plot_styling(plot)
    elevation_glyphs(plot, src_elev, src_elev_stage, src_hover)

    return plot

def elevation_plot_styling(plot):
    plot.title.text_font_size = FONTSIZE
    plot.yaxis[0].formatter = PrintfTickFormatter(format="%d m")
    plot.xaxis[0].formatter = PrintfTickFormatter(format="%d km")
    plot.axis.minor_tick_line_color = None
    plot.outline_line_color = None
    plot.xaxis.axis_line_color = None
    plot.axis.major_tick_line_color = plot.xgrid.grid_line_color
    plot.yaxis.axis_line_color = plot.xgrid.grid_line_color
    plot.axis.major_tick_in = 0
    plot.axis.major_label_text_font_size = FONTSIZE
    plot.background_fill_color = "#efefef"
    plot.ygrid.grid_line_color = 'lightgrey'
    plot.xgrid.grid_line_color = 'lightgrey'
    plot.min_border_right = 10

def elevation_glyphs(plot, src_elev, src_elev_stage, src_hover):
    plot.varea(
        x = 'x',
        y1 = 'y1',
        y2 = 'y2',
        fill_color = '#F07353',
        fill_alpha = 0.6,
        source = src_elev,
        name = 'r_elevation'
        )

    plot.varea(
        x = 'x',
        y1 = 'y1',
        y2 = 'y2',
        fill_color = '#C03127',
        fill_alpha = 0.5,
        source = src_elev_stage,
        name = 'r_elev_stage'
        )

    # add a ghost line in order to capture index when hovering
    r_ghost = plot.line(
        x = 'x', y = 'y1',
        line_color = None,
        source = src_elev
        )

    plot.circle(
        x = 'x', y = 'y',
        line_color = 'black',
        fill_color = 'white',
        size = 6,
        line_width = 2,
        source = src_hover,
        name = 'marker_elevation'
        )

    hover = HoverTool(
        tooltips = None, 
        mode = 'vline',
        line_policy = 'none',
        renderers = [r_ghost],
        name = 'hover'
    )

    plot.add_tools(hover)

    elevation_label = HTMLLabel(
        x = 0.5,
        y = 5,
        x_units = 'data',
        y_units = 'screen',
        text_baseline = 'top',
        y_offset = -2, 
        text = '',
        text_font = 'system-ui',
        text_font_size = '13px',
        text_align = 'left',
        visible = False,
        name = 'elevation_label'
        )
    plot.add_layout(elevation_label)


def add_callback(sources, elevation_plot, map_plot):
    ''' 
    use js_on_event callback for tap instead of adding callback directly
    on taptool in order to capture event when clicking on map w/o hitting
    glyph in order to udate the profile plot with profile for all stages
    '''
    tap_cb_code = '''
      const idx = src_routes.selected.indices;
      var stage = '';
      if (idx.length === 0) {
        stage = 'Total';
      } else {
        stage = src_routes.data['stage'][idx];
      }
      updateElevationSrc(stage);
    '''
    tap_cb = CustomJS(
        args = {
            'src_routes': sources['routes'],
            'src_elevation': sources['elevation'],
            'elevation_data': sources['elevation_data'],
            },
        code = tap_cb_code
        )
    map_plot.js_on_event('tap', tap_cb)

    route_hover_cb_code = '''
      const indices = cb_data.index.indices;
      routeHoverProfileHighlight(indices);
    '''
    route_hover_cb = CustomJS(
        args = {
          'elevation_plot': elevation_plot
        },
        code = route_hover_cb_code)
    map_plot.select(name = 'route_hover')[0].callback = route_hover_cb

    hover_cb_code = '''
        elevationHover(cb_data, elevation_plot, src_marker_map, src_marker_elevation);
    '''
    hover_cb = CustomJS(
    args = {
        'src_marker_map': sources['marker_map'],
        'src_marker_elevation': sources['marker_elevation'],
        'elevation_plot': elevation_plot
        }, 
        code = hover_cb_code
    )
    elevation_plot.select(name = 'hover')[0].callback = hover_cb


def create_sources():
    src = {}
    src['routes'] = ColumnDataSource(
        data = {'xs': [], 'ys': [], 'label': [], 'stage': []},
        name = 'src_routes'
        )
    src['elevation'] = ColumnDataSource(
        data = {'x': [], 'y1': [], 'y2': [], 'stage_idx': [], 'stage': []},
        name = 'src_elevation'
        )
    src['elevation_stage'] = ColumnDataSource(
        data = {'x': [], 'y1': [], 'y2': []},
        name = 'src_elev_stage'
        )
    src['elevation_data'] = ColumnDataSource(
        data = {'x': [], 'y1': [], 'stage': []},
        name = 'src_elevation_data'
        )
    src['marker_map'] = ColumnDataSource(data = {'x': [], 'y': []})
    src['marker_elevation'] = ColumnDataSource(data = {'x': [], 'y': []})
    src['start_finish'] = ColumnDataSource(
        data = {'x': [], 'y': [], 'label': [], 'marker': [], 'color': []}
        )

    return src