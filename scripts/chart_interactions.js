/* Derived layout for a filtered price comparison. This module has no browser
 * dependency, so visibility, annotation ownership and ranges can be tested
 * independently of Plotly's rendering. Source prices are never changed. */
(function (root) {
  "use strict";
  const clone = value => JSON.parse(JSON.stringify(value));
  const axisKey = ref => "yaxis" + (ref === "y" ? "" : ref.slice(1));
  const visible = trace => trace.visible !== false && trace.visible !== "legendonly";
  const clean = text => text.replace(/<br\s*\/?>/gi, "\n").replace(/<[^>]*>/g, "");

  function rangeFor(traces, axis, original, logarithmic = false) {
    const active = traces.filter(t => (t.yaxis || "y") === axis && visible(t));
    if (!active.length) return original.slice();
    const all = traces.filter(t => (t.yaxis || "y") === axis);
    if (active.length === all.length) return original.slice();
    const values = active.flatMap(t => t.y).filter(Number.isFinite);
    if (logarithmic) return [Math.log10(Math.min(...values)) - 0.22, Math.log10(Math.max(...values)) + 0.22];
    const maximum = Math.max(...values);
    const lower = original[0];
    const span = Math.max(maximum - lower, lower ? 5 : 0.5);
    return [lower, Number((Math.max(maximum, lower + span) + span * 0.22).toPrecision(8))];
  }

  function intersects(box, a, b) {
    // Clip a price segment against the padded text box (Liang–Barsky).
    const dx = b[0] - a[0], dy = b[1] - a[1];
    const p = [-dx, dx, -dy, dy];
    const q = [a[0] - box[0], box[2] - a[0], a[1] - box[1], box[3] - a[1]];
    let low = 0, high = 1;
    for (let i = 0; i < 4; i++) {
      if (p[i] === 0) { if (q[i] < 0) return false; }
      else {
        const r = q[i] / p[i];
        if (p[i] < 0) low = Math.max(low, r); else high = Math.min(high, r);
        if (low > high) return false;
      }
    }
    return true;
  }
  const overlap = (a, b) => a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1];
  function derive(base, metadata, traces, changedAxes, currentLayout, size, measure) {
    const update = {};
    const annotations = clone(base.layout.annotations);
    const changed = new Set(changedAxes || metadata.axes);
    const width = size.width, totalHeight = size.height;
    const textWidth = measure || ((s, font) => s.length * font * 0.55);
    const ranges = {};
    for (const axis of metadata.axes) {
      const key = axisKey(axis);
      ranges[axis] = changed.has(axis) ? rangeFor(traces, axis, base.layout[key].range, base.layout[key].type === "log")
        : (currentLayout[key].range || base.layout[key].range).slice();
      if (changed.has(axis)) {
        update[key + ".range"] = ranges[axis];
        update[key + ".autorange"] = false;
        update[key + ".tickmode"] = "auto";
        update[key + ".tickvals"] = null;
        update[key + ".ticktext"] = null;
        update[key + ".tickprefix"] = "$";
      }
    }
    annotations.forEach((a, i) => {
      const owner = metadata.annotationOwners[i];
      if (owner !== null) a.visible = visible(traces[owner]);
    });

    for (const axis of metadata.axes) {
      const key = axisKey(axis), domain = base.layout[key].domain;
      const scale = value => base.layout[key].type === "log" ? Math.log10(value) : value;
      const height = totalHeight * (domain[1] - domain[0]);
      const range = ranges[axis], delta = range[1] - range[0];
      const matching = traces.filter(t => (t.yaxis || "y") === axis && visible(t));
      const dates = base.layout["xaxis" + (axis === "y" ? "" : axis.slice(1))].range;
      const start = Date.parse(dates[0]), span = Date.parse(dates[1]) - start;
      const px = d => (Date.parse(d) - start) / span * width;
      const py = y => (y - range[0]) / delta * height;
      const paths = matching.map(t => t.x.map((x, i) => [px(x), py(scale(t.y[i]))]));
      const used = [];
      const labels = annotations.filter(a => a.yref === axis && a.visible !== false);
      const ends = labels.filter(a => a.xanchor === "left").sort((a, b) => a.y - b.y);
      const positions = [];
      ends.forEach(a => positions.push(Math.max(py(a.y), positions.length ? positions.at(-1) + 64 : 28)));
      if (positions.length) {
        positions[positions.length - 1] = Math.min(positions.at(-1), height - 24);
        for (let i = positions.length - 2; i >= 0; i--) positions[i] = Math.min(positions[i], positions[i + 1] - 64);
      }
      const ordered = [...ends, ...labels.filter(a => a.xanchor !== "left")];
      for (const a of ordered) {
        const font = a.font?.size || 12, lines = clean(a.text).split("\n");
        const w = Math.max(...lines.map(t => textWidth(t, font))) + 10;
        const h = lines.length * font * 1.2 + 8;
        const x = px(a.x), y = py(a.y), endIndex = ends.indexOf(a);
        let options = [];
        if (endIndex >= 0) options = [[55, y - positions[endIndex]]];
        else {
          options.push([a.ax || 0, a.ay || -38]);
          for (const dx of [0, -60, 60, -110, 110, -170, 170, -230, 230])
            for (const dy of [-38, 38, -60, 60, -90, 90, -125, 125]) options.push([dx, dy]);
        }
        let fitted = false;
        for (const [dx, dy] of options) {
          const cx = x + dx, cy = y - dy;
          const box = endIndex >= 0 ? [cx - 4, cy - h / 2 - 4, cx + w + 4, cy + h / 2 + 4]
            : [cx - w / 2 - 4, cy - h / 2 - 4, cx + w / 2 + 4, cy + h / 2 + 4];
          if (endIndex < 0 && (box[0] < 0 || box[2] > width || box[1] < 0 || box[3] > height)) continue;
          if (used.some(b => overlap(box, b))) continue;
          if (endIndex < 0 && paths.some(path => path.some((p, i) => i > 0 && intersects(box, path[i - 1], p)))) continue;
          a.ax = dx; a.ay = dy; used.push(box); fitted = true; break;
        }
        if (!fitted && endIndex < 0) a.visible = false;
      }
      if (!matching.length) {
        annotations.push({xref: "paper", yref: "paper", x: 0.5, y: (domain[0] + domain[1]) / 2,
          text: "Select a family in the legend to show prices", showarrow: false,
          font: {size: 16, color: "#73777d"}});
      }
    }
    update.annotations = annotations;
    return update;
  }
  const api = {derive, rangeFor, visible, intersects};
  root.ModelCompass = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);


ModelCompass.mount = async function (payload) {
  const clone = value => JSON.parse(JSON.stringify(value));
  for (const panel of payload.panels) {
    const chart = document.getElementById('chart-' + panel.id);
    const strip = document.getElementById('latest-' + panel.id);
    const canvas = document.createElement('canvas'), context = canvas.getContext('2d');
    const measure = (text, size) => { context.font = size + 'px Arial'; return context.measureText(text).width; };
    let applying = false, pending = Promise.resolve(), timer;
    function presentation() {
      const responsive = clone(panel.base);
      const narrow = chart.getBoundingClientRect().width < 1050;
      responsive.layout.margin.r = narrow ? 30 : 285;
      responsive.layout.margin.l = chart.getBoundingClientRect().width < 600 ? 80 : 100;
      if (narrow) {
        const xa = responsive.layout.xaxis;
        const count = Math.min(panel.base.layout.xaxis.tickvals.length, chart.getBoundingClientRect().width < 600 ? 3 : 4);
        const indices = Array.from({length: count}, (_, i) => Math.round(i * (panel.base.layout.xaxis.tickvals.length - 1) / Math.max(1, count - 1)));
        xa.tickvals = indices.map(i => panel.base.layout.xaxis.tickvals[i]);
        xa.ticktext = indices.map(i => panel.base.layout.xaxis.ticktext[i]);
      }
      strip.hidden = !narrow;
      return {responsive, narrow};
    }
    const first = presentation();
    await Plotly.newPlot(chart, first.responsive.data, first.responsive.layout,
      {responsive: false, displayModeBar: false, displaylogo: false, scrollZoom: false});
    function synchronize(changedAxes) {
      pending = pending.catch(() => {}).then(async () => {
        const {responsive, narrow} = presentation();
        const width = chart.getBoundingClientRect().width;
        const margin = responsive.layout.margin;
        const update = ModelCompass.derive(responsive, panel.metadata, chart.data, changedAxes,
          chart.layout, {width: width - margin.l - margin.r,
            height: responsive.layout.height - margin.t - margin.b}, measure);
        if (narrow) update.annotations.forEach(a => {
          if (a.xanchor === 'left') a.visible = false;
        });
        Object.assign(update, {margin, 'xaxis.tickvals': responsive.layout.xaxis.tickvals,
          'xaxis.ticktext': responsive.layout.xaxis.ticktext, width});
        applying = true;
        try { await Plotly.relayout(chart, update); } finally { applying = false; }
        strip.querySelectorAll('[data-family]').forEach(item => {
          item.hidden = !ModelCompass.visible(chart.data[Number(item.dataset.family)]);
        });
      }).catch(error => console.error('Could not update chart', error));
      return pending;
    }
    chart.on('plotly_restyle', event => {
      if (Object.prototype.hasOwnProperty.call(event[0], 'visible')) synchronize(['y']);
    });
    chart.on('plotly_relayout', event => {
      if (!applying && Object.keys(event).some(key => key.startsWith('yaxis.range'))) synchronize([]);
    });
    window.addEventListener('resize', () => { clearTimeout(timer); timer = setTimeout(() => synchronize([]), 120); });
    await synchronize([]);
  }
};
