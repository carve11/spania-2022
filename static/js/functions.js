// functions.js
const YRANG_PAD_FACTOR = 1.1;
const globals = {
  map: null,
  mapHoveredStage: null,
  elevation_data: null,
  stage_summary: null,
  stage_viewed_elevation: null
};

function initializeDocument(token, geojson, elevation_data, stage_summary) {
  const map = addMapboxMap(token);
  addMapData(map, geojson);

  globals['map'] =  map;
  globals['elevation_data'] = elevation_data;
  globals['stage_summary'] = stage_summary;

  map.once('idle', (e) => {
    updateElevationSrc('Total');
  });
}

function addMapboxMap(token) {
  mapboxgl.accessToken =  token;
  const map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/mapbox/outdoors-v12',
    center: [-5.7, 43.25],
    zoom: 7
  });

  return map;
}

function addMapData(map, geojson) {
  // use specific geojson source for hover highlight of a stage 
  // built-in hover is not perfect if stages got overlapping coordinates
  const highlightstage_geojson = {
    'type': 'FeatureCollection',
    'features': [
      {
        'type': 'Feature',
        'geometry': {
          'type': 'LineString',
          'coordinates': []
        }
      }
    ]
  };

  const popup = new mapboxgl.Popup({
    closeButton: false,
    closeOnClick: false
  })
    .setMaxWidth('none');

  map.addControl(new mapboxgl.ScaleControl());

  map.on('load', () => {
    map.addSource('stages_src', {
      "type": "geojson",
      "data": geojson['stages']
    });
  
    map.addSource('highlightstage_src', {
      "type": "geojson",
      "data": highlightstage_geojson
    });

    map.addSource('stage_marker_src', {
      "type": "geojson",
      "data": geojson['start_finish']
    });

    map.addLayer({
      id: 'stages_ly',
      type: 'line',
      source: 'stages_src',
      paint: {
        'line-color': "blue",
        'line-width': 4
      }
    });

    map.addLayer({
      id: 'highlightstage_ly',
      type: 'line',
      source: 'highlightstage_src',
      paint: {
        'line-color': "firebrick",
        'line-width': 5
      }
    });

    map.addLayer({
      id: 'stage_marker_ly',
      type: 'circle',
      source: 'stage_marker_src',
      paint: {
        'circle-color': [
          'match', ['get', 'location_type'],
          'start', 'green',
          'finish', 'red',
          'grey'
        ],
        'circle-radius': 6,
        'circle-stroke-width': 2,
        'circle-stroke-color': '#ffffff'
      }
    });
  });

  map.on('mousemove', ['stages_ly', 'stage_marker_ly'], (e) => {
    map.getCanvas().style.cursor = 'pointer';
    const tooltip = e.features[0].properties.tooltip;
    popup.setLngLat(e.lngLat).setHTML(tooltip).addTo(map);

    if (e.features[0].layer.id === 'stages_ly') {
      const hoveredstage = e.features[0].properties.stage;
      globals.mapHoveredStage = hoveredstage;
      mapHighlightStage(hoveredstage, true);
      stageProfileHighlight(hoveredstage, true);
    }
  });

  map.on('mouseleave', 'stages_ly', (e) => {
    mapHighlightStage(globals.mapHoveredStage, false);
    globals.mapHoveredStage = null;

    stageProfileHighlight(null, false);
    removeMapHoverPopup(map, popup);
  });

  map.on('mouseleave', 'stage_marker_ly', (e) => {
    removeMapHoverPopup(map, popup);
  });

  map.on('click', (e) => {
    // reset elevation profile plot to show all stages
    const stage_layer_feat = map.queryRenderedFeatures(e.point, {layers: ['stages_ly']});
    if (stage_layer_feat.length > 0) {
      return;
    }
    updateElevationSrc('Total');
  });

  map.on('click', 'stages_ly', (e) => {
    const stage = e.features[0].properties.stage;
    stageProfileHighlight(null, false);
    updateElevationSrc(stage);
  });
}

function removeMapHoverPopup(map, popup) {
  map.getCanvas().style.cursor = '';
  popup.remove();
}

function mapHighlightStage(stage, show) {
  const highlightstage_src = globals.map.getSource('highlightstage_src');

  let coord = [];
  if (show) {
    coord = stageCoordinates(stage);
  }
  highlightstage_src._data.features[0].geometry.coordinates = coord;
  highlightstage_src.setData(highlightstage_src._data);
}

function stageCoordinates(stage, specificIdx = false) {
  const idx = globals.stage_summary.stage_order.indexOf(stage);
  const geojson = globals.map.getSource('stages_src')._data.features[idx];

  if (!specificIdx) {
    return geojson.geometry.coordinates;
  }
  return geojson.geometry.coordinates[specificIdx];
}

function updateElevationSrc(stage) {
  const plot = window.Bokeh.documents[0].get_model_by_name('elevation_plot');
  const src_elevation = window.Bokeh.documents[0].get_model_by_name('src_elevation');
  const elevation_data = globals['elevation_data'];

  if (stage == 'Total') {
    var {x, y1, stage_idx_arr, stage_arr} = profileAllStages(elevation_data);
    mapHighlightStage(globals.mapHoveredStage, false);
    globals.mapHoveredStage = null; 
  } else {
    var {x, y1, stage_idx_arr, stage_arr} = profileDataStage(elevation_data, stage);
    globals.mapHoveredStage = stage;
    mapHighlightStage(stage, true);
  }

  const {ymin, ymax} = elevationPlotYrng(y1);

  src_elevation.data = {
    x: x,
    y1: y1,
    y2: arrayFill(y1.length, ymin),
    stage_idx: stage_idx_arr,
    stage: stage_arr
  }

  plot.y_range.start = ymin;
  plot.y_range.end = ymax;
  plot.x_range.end = Math.max(...x);

  elevationPlotTitle(stage);

  globals.stage_viewed_elevation = stage;
}

function profileDataStage(elevation_data, stage) {
  const x = elevation_data[stage]['x'];
  const y1 = elevation_data[stage]['y1'];
  const stage_idx_arr = idxArr(x.length);
  const stage_arr = arrayFill(x.length, stage);

  return {x, y1, stage_idx_arr, stage_arr};
}

function profileAllStages(elevation_data) {
  const x = [];
  const y1 = [];
  const stage_arr = [];
  const stage_idx_arr = [];
  const stage_order = globals.stage_summary.stage_order;

  for (const stage of stage_order) {
    const data = elevation_data[stage];
    var total_dist = [];

    if (stage !== stage_order[0]) {
      for(var j = 0; j < data.x.length; ++j) {
        total_dist.push(x[x.length-1] + data.x[j]);
      }
    } else {
      total_dist = data.x;
    }

    x.push(...total_dist);
    y1.push(...data.y1);
    stage_arr.push(...arrayFill(data.x.length, stage));
    stage_idx_arr.push(...idxArr(data.x.length));
  }

  return {x, y1, stage_idx_arr, stage_arr};
}

function elevationPlotYrng(yArr) {
  var min = Math.min(...yArr);
  var max = Math.max(...yArr);
  const rng = max-min;

  if (rng > 1000) {
    min -= 50;
    max += 150;
  } else if (rng > 600) {
    min -= 50;
    max += 200;
  } else if (rng > 300) {
    min -= 50;
    max += 250;
  } else if (rng > 100) {
    min -= 25;
    max += 500;
  } else {
    min -= 25;
    max += 600;
  }

  return {ymin: min, ymax: max}
}

function elevationPlotTitle(stage) {
  const elm_heading = document.getElementsByClassName("elevation-plot-heading")[0];
  const stage_data = globals.stage_summary[stage];

  const txt = `${stage}: ${stage_data.start}-${stage_data.finish} - ${stage_data.distance} km`;

  elm_heading.innerText = txt;
}

function elevationHover(bk_hover_data) {
  var distance = null;
  var elevation = null;
  var visible_bool = false;
  var coord = null;
  var stage = null;

  const indices = bk_hover_data.index.line_indices;
  const h_sy = bk_hover_data.geometry.sy;
  const plot = window.Bokeh.documents[0].get_model_by_name('elevation_plot');
  const p_height = plot.inner_height;
  const p_min_b = plot.min_border;

  if ((indices.length > 0) && (h_sy > p_min_b+1) && (h_sy < p_height+p_min_b-1)){
    const src_elevation = window.Bokeh.documents[0].get_model_by_name('src_elevation');
    const idx = indices[0];
    const stage_idx = src_elevation.data['stage_idx'][idx];
    distance = src_elevation.data['x'][idx];
    elevation = src_elevation.data['y1'][idx];

    stage = src_elevation.data['stage'][idx];
    coord = stageCoordinates(stage, stage_idx);

    visible_bool = true;
  }

  updateElevationMarkerSrc(distance, elevation)
  stageProfileHighlight(stage, visible_bool);
  locationMarkerMap(coord, visible_bool);
  elevationHoverLabel(bk_hover_data, distance, elevation, visible_bool);
  elevationStageLabel(stage, visible_bool);
}

function updateElevationMarkerSrc(distance, elevation) {
  var x = [];
  var y = [];
  const src = window.Bokeh.documents[0].get_model_by_name('src_elevation_marker');

  if (distance !== null) {
    x.push(distance);
    y.push(elevation);
  }

  src.data = {
    x: x,
    y: y
  }
}

function elevationHoverLabel(bk_hover_data, x, y, visible) {
  const plot = window.Bokeh.documents[0].get_model_by_name('elevation_plot');
  const label = plot.select(name = 'elevation_label')[0];
  
  if (!visible) {
    label.visible = visible;
    return;
  }

  const XOFFSET = 5;
  var text_align = 'left';
  var x_offset = XOFFSET;
  var sx2canvas_border = plot.outer_width;
  sx2canvas_border -= plot.min_border_right;
  sx2canvas_border -= bk_hover_data['geometry'].sx;

  if (sx2canvas_border < 70) {
    text_align = 'right';
    x_offset = -XOFFSET;
  }

  label.x_offset = x_offset;
  label.text_align = text_align;
  label.x = x;
  label.y = plot.inner_height;

  var txt = x.toFixed() + ' km\n';
  txt += y.toFixed() + ' m';
  label.text = txt;
  label.visible = visible;
}

function elevationStageLabel(stage, visible) {
  const plot = window.Bokeh.documents[0].get_model_by_name('elevation_plot');
  const label = plot.select(name = 'elevation_stage_label')[0];

  if ((!visible) || (globals.stage_viewed_elevation !== 'Total')) {
    label.visible = false;
    label.text = '';
    return;
  }

  if (label.text === stage) {
    return;
  }

  const src_elev_stage = window.Bokeh.documents[0].get_model_by_name('src_elevation_stage');
  const data = src_elev_stage.data;

  label.x = (data['x'][data['x'].length-1] + data['x'][0])/2;
  label.x = plot.inner_width;
  label.y = plot.inner_height + 5;
  label.text = stage;
  label.visible = true;
}

function stageProfileHighlight(stage, visible) {
  const plot = window.Bokeh.documents[0].get_model_by_name('elevation_plot');
  const highlight_glyph = plot.select(name = 'r_elevation_stage')[0];
  const src_elev_stage = window.Bokeh.documents[0].get_model_by_name('src_elevation_stage');
  
  if ((!visible) || (globals.stage_viewed_elevation !== 'Total')) {
    highlight_glyph.visible = false;
    src_elev_stage.data = {
      x: [],
      y1: [],
      y2: []
    }
    return;
  }

  const src_elevation = window.Bokeh.documents[0].get_model_by_name('src_elevation');
  const min_idx = src_elevation.data['stage'].indexOf(stage);
  const max_idx = src_elevation.data['stage'].lastIndexOf(stage);
  
  src_elev_stage.data = {
    x: src_elevation.data['x'].slice(min_idx, max_idx+1),
    y1: src_elevation.data['y1'].slice(min_idx, max_idx+1),
    y2: src_elevation.data['y2'].slice(min_idx, max_idx+1)
  }

  highlight_glyph.visible = true;
}

function locationMarkerMap(coord, show) {
  const elm = document.getElementById("location-marker");
  const bbox_rect = elm.getBoundingClientRect();
  const elm_offset = bbox_rect.width / 2;

  if (!show) {
    elm.style.display = "none";

    return;
  }

  const scr_units = globals.map.project(new mapboxgl.LngLat(coord[0], coord[1]));

  elm.style.display = "block";
  elm.style.left = `${scr_units.x-elm_offset}px`;
  elm.style.top = `${scr_units.y-elm_offset}px`;
}

function arrayFill(length, value) {
  var array = [];
  for(var i = 0; i < length; ++i) array.push(value);
  return array;
}

function idxArr(length) {
  var array = [];
  for(var i = 0; i < length; ++i) array.push(i);
  return array;
}
