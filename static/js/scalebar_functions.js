// scalebar_functions.js
const SCALE_LENGTH_PX = 125;
const SCALE_OFFSET = 15;
const SCALE_THICKNESS = 7;
const BASE_UNIT = 'm';
const BAR_LIGHT_COLOR = 'white';
const BAR_DARK_COLOR = 'grey';
const LABEL_STANDOFF = 3;

function scalebar(plot, scale_outline, src_labels, src_bar) {
  var scale_lngth_px = SCALE_LENGTH_PX;
  var unit = BASE_UNIT;
  const scale_x_offset = SCALE_OFFSET;
  const scale_y_offset = SCALE_OFFSET;
  const scale_y_dy = SCALE_THICKNESS;
  const {xscale, yscale} = scales(plot);

  var px_size = calcPxsize(xscale, yscale, scale_lngth_px);
  var scale_distance = scale_lngth_px * px_size;
  var {px_size, scale_distance, unit} = adjPxsizeUnit(px_size, scale_distance, unit);

  scale_distance = scaleDistance(scale_distance);
  scale_lngth_px = Math.round(scale_distance / px_size);

  updateBarSource(scale_distance, scale_lngth_px, src_bar, plot);
  updateBarOutline(scale_outline, scale_lngth_px);
  updateLabelsSource(scale_distance, scale_lngth_px, unit, src_labels, plot);
}

function calcPxsize(xscale, yscale, scale_length_px) {
  const {p1, p2} = calcPointsLatLonMidCanvas(xscale, yscale, scale_length_px);
  let d2 = calcGreatCirleDistance(p1, p2);

  return d2 / scale_length_px;
}

function calcPointsLatLonMidCanvas(xscale, yscale, scale_length_px) {
  // define the points to be used to calculate great-circle distance
  // use points in the middel of the canvas that are at a diagonal
  // return points as [lon, lat]
  const width = xscale.s_rng.end-xscale.s_rng.start;
  const height = yscale.s_rng.end-yscale.s_rng.start;

  const half_dist = Math.sqrt( ((scale_length_px/2)**2) / 2 );
  const x0 = (width/2) - half_dist;
  const x1 = x0 + 2*half_dist;
  
  const y0 = (height/2) - half_dist;
  const y1 = y0 + 2*half_dist;

  const p1 = [screen2Data(x0, xscale), screen2Data(y0, yscale)];
  const p2 = [screen2Data(x1, xscale), screen2Data(y1, yscale)];
  
  return {p1: projection(p1), p2: projection(p2)};
}

function calcGreatCirleDistance(point1, point2) {
  /* - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  */
  /* Latitude/longitude spherical geodesy tools                         (c) Chris Veness 2002-2021  */
  /*                                                                                   MIT Licence  */
  /* www.movable-type.co.uk/scripts/latlong.html                                                    */
  /* www.movable-type.co.uk/scripts/geodesy-library.html#latlon-spherical                           */
  /* - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -  */
  // Calculate great-circle distance between two points based on haversine formula (ref above).
  // point data format: [lon, lat]

  const lon1 = point1[0];
  const lat1 = point1[1];
  const lon2 = point2[0];
  const lat2 = point2[1];
  
  const R = 6371e3; // metres
  const φ1 = lat1 * Math.PI/180; // φ, λ in radians
  const φ2 = lat2 * Math.PI/180;
  const Δφ = (lat2-lat1) * Math.PI/180;
  const Δλ = (lon2-lon1) * Math.PI/180;

  const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
            Math.cos(φ1) * Math.cos(φ2) *
            Math.sin(Δλ/2) * Math.sin(Δλ/2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

  return R * c; // in metres
}

function adjPxsizeUnit(pxsize, distance, unit) {
  var unit_conv = 1;
  if (distance > 2000) {
      unit_conv = 1/1000;
      unit = 'km';
  }
  const scale_distance = distance * unit_conv;
  const px_size = pxsize * unit_conv;

  return {px_size, scale_distance, unit};
}

function scaleDistance(distance) {
  var scale_multiple = 2;

  if (distance > 2000) {
      scale_multiple = 1000;
  } else if (distance > 1500) {
      scale_multiple = 500;
  } else if (distance > 1000) {
      scale_multiple = 200;
  } else if (distance > 500) {
      scale_multiple = 100;
  } else if (distance > 100) {
      scale_multiple = 50;
  } else if (distance > 50) {
      scale_multiple = 20;
  } else if (distance > 10) {
      scale_multiple = 10;
  }

  return Math.round(distance/scale_multiple)*scale_multiple;
}

function updateBarSource(distance, length, src, plot) {
  const mid_y = SCALE_OFFSET + Math.round(SCALE_THICKNESS/2);
  const base = [];
  const lower = [];
  const upper = [];
  const color = [];

  var bar_splits = 1;
  if ((distance % 3) === 0) {
    bar_splits = 3;
  } else if ((distance % 2) === 0) {
    bar_splits = 4;
  }

  const split_px = length / bar_splits;
  for (var i = 0; i < bar_splits; i++) {
    const x0 = Math.round(SCALE_OFFSET + split_px * i);
    const x1 = Math.round(SCALE_OFFSET + split_px * (i+1));
    
    if (i%2 == 0) {
        color.push(BAR_DARK_COLOR);
    } else {
        color.push(BAR_LIGHT_COLOR);
    }
    base.push(mid_y);
    lower.push(x0);
    upper.push(x1);
  }

  src.data['base'] = base;
  src.data['lower'] = lower;
  src.data['upper'] = upper;
  src.data['color'] = color;
  src.change.emit();

  const bar_glyph = plot.select(name = 'scale_bar')[0];
  bar_glyph.thickness = SCALE_THICKNESS;
}

function updateBarOutline(glyph, length) {
  const x0 = SCALE_OFFSET;
  const x1 = x0 + length;
  const y0 = SCALE_OFFSET;
  const y1 = y0 + SCALE_THICKNESS;

  glyph.xs = [x0, x1, x1, x0];
  glyph.ys = [y0, y0, y1, y1];
}

function updateLabelsSource(distance, length, unit, src, plot) {
  const labels = [];
  const x = [];
  const y = [];
  const sy = SCALE_OFFSET + SCALE_THICKNESS + LABEL_STANDOFF;
  const align = [];

  var split = 2;
  if ((distance % 3) === 0) split = 3;
    
  for (let i = 0; i < split + 1; i++) {
    const sx = Math.round(SCALE_OFFSET + (length/split) * i);
    const label = Math.round(i*distance/split).toString();
    x.push(sx);
    y.push(sy);
    labels.push(label);
    align.push('center');
  }
  
  const labels_ann = plot.select(name = 'scale_labels_ann')[0];
  const font_size = labels_ann.text_font_size.value;
  const font = labels_ann.text_font.value;
  const last_label_width = getTextWidth(labels[split], font, font_size);
  labels.push(` ${unit}`);
  x.push(x[split]+last_label_width/2);
  y.push(sy);
  align.push('left');

  src.data['x'] = x;
  src.data['y'] = y;
  src.data['text'] = labels;
  src.data['align'] = align;
  src.change.emit();
}

function scales(plot) {
  const xscale = scale(dataRngProps(plot.inner_width), rngProperties(plot.x_range));
  const yscale = scale(dataRngProps(plot.inner_height), rngProperties(plot.y_range));

  return {xscale, yscale};
}

function scale(s_rng, d_rng) {
  // s_rng: screen units px
  // d_rng: data units
  return {s_rng, d_rng};
}

function screen2Data(num, scale) {
  const ratio = (scale.d_rng.end-scale.d_rng.start)/(scale.s_rng.end-scale.s_rng.start);
  return scale.d_rng.start + (ratio * num);
}

function rngProperties(rngObj) {
  return {start: rngObj.start, end: rngObj.end};
}

function dataRngProps(end) {
  return {start: 0, end: end};
}

function projection(coord) {
  const mercator = proj4.defs("GOOGLE");
  const wgs84 = proj4.defs("WGS84");
  const wgs84_mercator = proj4(wgs84, mercator);

  return wgs84_mercator.inverse(coord);
}

function getTextWidth(text, font, fontsize) {
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  
  const font_str = `${fontsize} ${font}`;
  context.font = font_str || getComputedStyle(document.body).font;
  const width = context.measureText(text).width;
  canvas.remove();
  return width;
}
