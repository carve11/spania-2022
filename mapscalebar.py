from bokeh.models import CustomJS, ColumnDataSource
from bokeh.models import LabelSet, PolyAnnotation, Whisker
from bokeh import events
import os

ROOTDIR = os.path.dirname(__file__)
STATIC = 'static'
JS = 'js'
SCALEBAR_JS_FILE = 'scalebar_functions.js'

OUTLINE_BAR_COLOR = '#444444'


class MapScaleBar:
    '''
    Add a map scale bar to a Bokeh plot object figure.
    '''
    def __init__(self, p):
        self.plot = p
        self._init_sources()
        self._annotations()
        self._add_callback()
        self._add_events()

    def _init_sources(self):
        self.src_labels = ColumnDataSource(
            data = {'x': [], 'y': [], 'text': [], 'align': []}
            )

        self.src_bar = ColumnDataSource(
            data = {'base': [], 'lower': [], 'upper': [], 'color': []}
        )

    def _annotations(self):
        # dark and light filling part of scale bar
        # only Whisker annotation supports array of multiple items
        # and need to use annotation which is in screen units
        scale_whisker = Whisker(
            base = 'base',
            upper = 'upper',
            lower = 'lower',
            lower_units = 'screen',
            upper_units = 'screen',
            base_units = 'screen',
            lower_head = None,
            upper_head = None,
            dimension = 'width',
            line_color = 'color',
            line_width = 7,
            level = 'annotation',
            source = self.src_bar,
            name = 'scale_bar'
            )
        self.plot.add_layout(scale_whisker)

        self.scale_outline = PolyAnnotation(
            xs_units = 'screen',
            ys_units = 'screen',
            xs = [],
            ys = [],
            line_width = 1,
            line_color = OUTLINE_BAR_COLOR,
            line_alpha = 1,
            fill_color = None,
            name = 'scale_outline'
            )
        self.plot.add_layout(self.scale_outline)

        scale_labels = LabelSet(
            x = 'x',
            y = 'y',
            x_units = 'screen',
            y_units = 'screen',
            text = 'text',
            text_align = 'align',
            text_baseline = 'alphabetic',
            text_font_size = '11px',
            source = self.src_labels,
            name = 'scale_labels_ann'
            )
        self.plot.add_layout(scale_labels)

    def _add_callback(self):
        cb_code = '''
            scalebar(plot, scale_outline, src_labels, src_bar);
        '''
        self.cb_scalebar = CustomJS(
            args = {
                'plot': self.plot,
                'scale_outline': self.scale_outline,
                'src_labels': self.src_labels,
                'src_bar': self.src_bar
                },
            code = cb_code,
            name = 'mapScaleScript'
            )

    def _add_events(self):
        self.plot.js_on_event(events.Pan, self.cb_scalebar)
        self.plot.js_on_event(events.MouseWheel, self.cb_scalebar)
        self.plot.js_on_event(events.Pinch, self.cb_scalebar)
        self.plot.js_on_event(events.Reset, self.cb_scalebar)
        self.plot.js_on_event(events.RangesUpdate, self.cb_scalebar)
