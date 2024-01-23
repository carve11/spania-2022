# visualization.py
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, CustomJS, InlineStyleSheet
from bokeh.models import HoverTool, PrintfTickFormatter, TapTool
from bokeh.models import Range1d, HTMLLabel

MAX_PLOT_WIDTH = 800
FONTSIZE = '14px'
LINECOLOR = 'darkgrey'
PLOT_FILLCOLOR = 'linen'

def elevation_plot(sources):
    '''
    Bokeh figure for plotting the elevation profile of a stage.
    '''
    plot = figure(
        height = 200,
        max_width = MAX_PLOT_WIDTH,
        min_width = 300,
        sizing_mode = 'stretch_width',
        tools = "", 
        toolbar_location = None,
        name = 'elevation_plot', 
        y_range = Range1d(0, 1),
        x_range = Range1d(0, 1),
        visible = True
        )

    profile_plot_styling(plot)
    profile_glyphs(plot, sources)
    add_callback(plot, sources)

    return plot

def profile_plot_styling(plot):
    plot.title.text_font_size = FONTSIZE
    plot.yaxis[0].formatter = PrintfTickFormatter(format="%d m")
    plot.xaxis[0].formatter = PrintfTickFormatter(format="%d km")
    plot.axis.minor_tick_line_color = None
    plot.outline_line_color = None
    plot.xaxis.axis_line_color = None
    plot.axis.major_tick_line_color = LINECOLOR
    plot.yaxis.axis_line_color = None
    plot.axis.major_tick_in = 0
    plot.axis.major_label_text_font_size = FONTSIZE
    plot.background_fill_color = PLOT_FILLCOLOR
    plot.border_fill_color = PLOT_FILLCOLOR
    plot.ygrid.grid_line_color = LINECOLOR
    plot.xgrid.grid_line_color = None
    plot.min_border_right = 10

def profile_glyphs(plot, sources):
    '''
    Glyphs for elevation profile plot
    '''
    # glyph for elevation profile
    r_varea = plot.varea(
        x = 'x',
        y1 = 'y1',
        y2 = 'y2',
        fill_color = '#F07353',
        fill_alpha = 0.8,
        source = sources['elevation'],
        name = 'r_elevation'
        )

    # glyph for highlight a specific stage profile
    plot.varea(
        x = 'x',
        y1 = 'y1',
        y2 = 'y2',
        fill_color = '#C03127',
        fill_alpha = 0.6,
        source = sources['elevation_stage'],
        name = 'r_elevation_stage'
        )

    # ghost line in order to capture index when hovering
    r_ghost = plot.line(
        x = 'x',
        y = 'y1',
        line_color = None,
        source = sources['elevation']
        )

    plot.add_tools(HoverTool(
        tooltips = None, 
        mode = 'vline',
        line_policy = 'none',
        renderers = [r_ghost],
        name = 'elevation_hover'
    ))

    plot.add_tools(TapTool(
        renderers = [r_varea],
        name = 'taptool'
    ))

    # elevation, distance marker 
    plot.circle(
        x = 'x',
        y = 'y',
        line_color = 'black',
        fill_color = 'white',
        size = 6,
        line_width = 2,
        source = sources['elevation_marker'],
        name = 'elevation_marker'
        )

    # elevation, distance label
    elevation_label = HTMLLabel(
        x = 0.5,
        y = 5,
        x_units = 'data',
        y_units = 'screen',
        text_baseline = 'top',
        y_offset = -2, 
        text = '',
        text_font_size = '13px',
        text_align = 'left',
        visible = False,
        name = 'elevation_label'
        )
    plot.add_layout(elevation_label)

    # if elevation profile plot shows all stages, show stage number 
    # if plot is hovered
    elevation_stage_label = HTMLLabel(
        x = 0.5,
        y = 5,
        x_units = 'screen',
        y_units = 'screen',
        text_baseline = 'bottom',
        text = '',
        text_font_size = '13px',
        text_align = 'right',
        visible = False,
        name = 'elevation_stage_label'
        )
    plot.add_layout(elevation_stage_label)

def add_callback(plot, sources):
    hover_cb = CustomJS(
        code = '''
          elevationHover(cb_data);
        '''
    )
    plot.select(name = 'elevation_hover')[0].callback = hover_cb

    tap_cb_code = '''
      selectStageElevationPlot(src);
    '''

    taptool_callback = CustomJS(
        args = {
          'src': sources['elevation']
          },
          code = tap_cb_code
    )
    plot.select(name = 'taptool')[0].callback = taptool_callback

def sources():
    src = {}
    # Source for profile plot where x, y1, y2 are coordinates
    # for bokeh varea glyph
    src['elevation'] = ColumnDataSource(
        data = {'x': [], 'y1': [], 'y2': [], 'stage_idx': [], 'stage': []},
        name = 'src_elevation'
        )

    # Source for highlight specific stage on profile plot when showing 
    # profiles for all stages. 
    # x, y1, y2 are coordinates for bokeh varea glyph
    src['elevation_stage'] = ColumnDataSource(
        data = {'x': [], 'y1': [], 'y2': []},
        name = 'src_elevation_stage'
        )

    # Source elevation, distance marker on profile plot
    src['elevation_marker'] = ColumnDataSource(
        data = {'x': [], 'y': []},
        name = 'src_elevation_marker'
        )

    return src
