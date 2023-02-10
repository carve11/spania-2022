function zoomBtnClick(elem_id) {
	var plot = window.Bokeh.documents[0].get_model_by_name('elevation_all');
  const factor_step = 0.1;
  var factor = 1;

  if (elem_id === 'zoom-in') {
    factor = 1 - factor_step;
  } else {
    factor = 1 + factor_step;
  }
  
  var plot = window.Bokeh.documents[0].get_model_by_name('map');
  const xstart = plot.x_range.start;
  const xend = plot.x_range.end;
  const ystart = plot.y_range.start;
  const yend = plot.y_range.end;
  const x_rng = xend - xstart;
  const y_rng = yend - ystart;
  const x_center = xstart + (x_rng / 2);
  const y_center = ystart + (y_rng / 2);

  const new_xrng = (xend-xstart) * factor;
  const new_yrng = (yend-ystart)* factor;
  const new_xstart = x_center - new_xrng/2;
  const new_xend = x_center + new_xrng/2;
  const new_ystart = y_center - new_yrng/2;
  const new_yend = y_center + new_yrng/2;

  plot.x_range.start = new_xstart;
  plot.x_range.end = new_xend;
  plot.y_range.start = new_ystart;
  plot.y_range.end= new_yend;
}

function resetBtnClick() {
	var plot = window.Bokeh.documents[0].get_model_by_name('map');
	resetRange(plot.x_range);
	resetRange(plot.y_range);
}

function resetRange(rngObj) {
	const {reset_start, reset_end} = rngObj;
	rngObj.start = reset_start;
  rngObj.end = reset_end;
}

function showProfile(stage) {
	updateElevationSrc(stage);
}

function updateElevationSrc(stage_id) {
	const plot = window.Bokeh.documents[0].get_model_by_name('elevation');
	const src_elevation = window.Bokeh.documents[0].get_model_by_name('src_elevation');
	const elevation_data = window.Bokeh.documents[0].get_model_by_name('src_elevation_data');
	const data = src_elevation.data;

	if (stage_id == 'Total') {
		var {x, y1, stage_idx, stage} = profileAllStages(elevation_data);
		const stage_elm = document.querySelectorAll(`[stageid="${stage_id}"]`)[0];
	} else {
		var {x, y1, stage_idx, stage} = profileDataStage(elevation_data, stage_id);
		const src_routes = window.Bokeh.documents[0].get_model_by_name('src_routes');
  	const routes_stage_idx = src_routes.data['stage'].indexOf(stage_id);
  	src_routes.selected.indices = [routes_stage_idx];
	}

	data['x'] = x;
	data['y1'] = y1;
	data['stage_idx'] = stage_idx;
	data['stage'] = stage;
	data['y2'] = minPlotElevation(data['y1']);
  src_elevation.change.emit();

  const stage_elm = document.querySelectorAll(`[stageid="${stage_id}"]`)[0];
  const elm_heading = document.getElementsByClassName("elevation-plot-heading")[0];
  elm_heading.innerText = stage_elm.innerText;

  plot.y_range.start = Math.min(...data['y2']);
  plot.y_range.end = Math.max(...data['y1'])*1.1;
  plot.x_range.end = Math.max(...data['x']);
}

function profileDataStage(elevationObj, stage_id) {
	const elev_stage_idx = elevationObj.data['stage'].indexOf(stage_id);
	const x = elevationObj.data['x'][elev_stage_idx];
  const y1 = elevationObj.data['y1'][elev_stage_idx];
  const stage_idx = idxArr(x.length);
  const stage = arrayFill(x.length, stage_id);

  return {x, y1, stage_idx, stage};
}

function profileAllStages(elevationObj) {
	const x = [];
	const y1 = [];
	const stage = [];
	const stage_idx = [];
	const data = elevationObj.data;

	for (var i = 0; i < data.stage.length; i++) {
		var total_dist = [];
		if (i > 0) {
			for(var j = 0; j < data.x[i].length; ++j) {
				total_dist.push(x[x.length-1] + data.x[i][j]);
			}
		} else {
			total_dist = data.x[i];
		}
		x.push(...total_dist);
		y1.push(...data.y1[i]);
		stage.push(...arrayFill(data.x[i].length, data.stage[i]));
		stage_idx.push(...idxArr(data.x[i].length));
	}
	return {x, y1, stage_idx, stage};
}

function minPlotElevation(elevationArr) {
	const min_elv = Math.min(...elevationArr);
  var factor = 1.0;

  if (min_elv > 10) {
  	factor = 0.9;
  } else if (min_elv >= 0) {
  	factor = 0
  } else {
  	factor = 1.1
  }
  return arrayFill(elevationArr.length, min_elv*factor);
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

function elevationHover(cbObj, elevation_plot, src_marker_map, src_marker_elevation) {
	const indices = cbObj.index.line_indices;
  const marker_map_data = src_marker_map.data;
  const marker_elevation_data = src_marker_elevation.data;
  const elevation_label = elevation_plot.select(name = 'elevation_label')[0];
  const src_routes = window.Bokeh.documents[0].get_model_by_name('src_routes');
	const src_elevation = window.Bokeh.documents[0].get_model_by_name('src_elevation');
	const src_elev_stage = window.Bokeh.documents[0].get_model_by_name('src_elev_stage');
	const highlight_glyph = elevation_plot.select(name = 'r_elev_stage')[0];

  var marker_map_x = [];
  var marker_map_y = [];
  var marker_elevation_x = [];
  var marker_elevation_y = [];
  var label_visible = false;
  var highlight_visible = false;


  if (indices.length > 0) {
    const idx = indices[0];
    const stage = src_elevation.data['stage'][idx];
    const routes_stage_idx = src_routes.data.stage.indexOf(stage);
    const stage_idx = src_elevation.data['stage_idx'][idx];
    const distance = src_elevation.data['x'][idx];
    const elevation = src_elevation.data['y1'][idx];

    marker_elevation_x.push(distance);
    marker_elevation_y.push(elevation);
    marker_map_x.push(src_routes.data['xs'][routes_stage_idx][stage_idx]);
    marker_map_y.push(src_routes.data['ys'][routes_stage_idx][stage_idx]);

    formatElevationHoverLabel(elevation_plot, cbObj, elevation_label, distance, elevation);
    label_visible = true;

    const elm_heading = document.getElementsByClassName("elevation-plot-heading")[0];
    if (elm_heading.innerText.startsWith('Total')) {
			stageProfileHighlight(stage);
			highlight_visible = true;
    } 
  }
  elevation_label.visible = label_visible;
  highlight_glyph.visible = highlight_visible;

  src_marker_map.data['x'] = marker_map_x;
  src_marker_map.data['y'] = marker_map_y;

  src_marker_elevation.data['x'] = marker_elevation_x;
  src_marker_elevation.data['y'] = marker_elevation_y;

  src_marker_map.change.emit();
  src_marker_elevation.change.emit();
}

function formatElevationHoverLabel(plot, cbObj, labelObj, x, y) {
	const XOFFSET = 5;
	var text_align = 'left';
  var x_offset = XOFFSET;
  var sx2canvas_border = plot.outer_width;
  sx2canvas_border -= plot.min_border_right;
  sx2canvas_border -= cbObj['geometry'].sx;

  if (sx2canvas_border < 70) {
    text_align = 'right';
    x_offset = -XOFFSET;
  }
  labelObj.x_offset = x_offset;
  labelObj.text_align = text_align;
  labelObj.x = x;
  labelObj.y = plot.inner_height;
  var txt = x.toFixed() + ' km\n';
  txt += y.toFixed() + ' m';
  labelObj.text = txt;
}

function routeHoverProfileHighlight(indices) {
	const src_routes = window.Bokeh.documents[0].get_model_by_name('src_routes');
	const plot = window.Bokeh.documents[0].get_model_by_name('elevation');
	const highlight_glyph = plot.select(name = 'r_elev_stage')[0];

	if ((src_routes.selected.indices.length != 0) || (indices.length === 0)) {
    highlight_glyph.visible = false;
		return
	}
	stageProfileHighlight(src_routes.data.stage[indices]);
	highlight_glyph.visible = true;
}

function stageProfileHighlight(stage) {
	const src_elev_stage = window.Bokeh.documents[0].get_model_by_name('src_elev_stage');
	const src_elevation = window.Bokeh.documents[0].get_model_by_name('src_elevation');
	const min_idx = src_elevation.data['stage'].indexOf(stage);
	const max_idx = src_elevation.data['stage'].lastIndexOf(stage);
	x = src_elevation.data['x'].slice(min_idx, max_idx+1);
	y1 = src_elevation.data['y1'].slice(min_idx, max_idx+1);
	y2 = src_elevation.data['y2'].slice(min_idx, max_idx+1);

	src_elev_stage.data['x'] = x;
	src_elev_stage.data['y1'] = y1;
	src_elev_stage.data['y2'] = y2;
	src_elev_stage.change.emit();
}

function runBkScript() {
  if ((window.Bokeh.documents[0] !== undefined)) {
      updateElevationSrc('Total');

      // need to add an onload JS function that executes the Bokeh CustomJS
      // script for the scale bar otherwise no scalebar present initially
      let bkScript = window.Bokeh.documents[0].get_model_by_name('mapScaleScript');
      bkScript.execute();
  } else {
      setTimeout(runBkScript, 1000);
  }
}
window.onload = function() {
  runBkScript();
}