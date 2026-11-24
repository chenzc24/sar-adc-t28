"use strict";

// The exporter emits the geometry-only subset of LayoutML Core 0.1.
const transforms = {
  R0: [1, 0, 0, 1], R90: [0, 1, -1, 0], R180: [-1, 0, 0, -1], R270: [0, -1, 1, 0],
  MX: [1, 0, 0, -1], MY: [-1, 0, 0, 1], MXR90: [0, 1, 1, 0], MYR90: [0, -1, -1, 0],
};
const pointPattern = /\((-?\d+),(-?\d+)\)/g;
const nativePack = "virtuoso_tsmc28";
const siteRoot = new URL("../", document.currentScript.src);
const chinese = document.documentElement.lang === "zh-CN";
const layoutStrings = chinese ? {
  die: "整片", selection: "选区", full: "全屏", exit: "退出全屏", fullError: "无法进入全屏",
  loading: (done, total) => `正在加载 r8 版图（${done}/${total}）…`,
  loadError: "版图加载失败。", rendererError: "暂时无法加载 LayoutML 渲染器。",
  landmarks: { "IO ring": "IO 环", "ADC core": "ADC 核心", "CDAC and reference": "CDAC 与参考驱动",
    "Bootstrap pair": "自举采样对", "SAR controller": "SAR 控制器", "Output register": "输出寄存器" },
  footprint: "单元外框",
} : {
  die: "Whole die", selection: "Selected area", full: "Full screen", exit: "Exit full screen",
  fullError: "Full screen unavailable", loading: (done, total) => `Loading the r8 chip layout (${done}/${total})…`,
  loadError: "Could not open the layout.", rendererError: "LayoutML's TSMC28 renderer is unavailable.",
  landmarks: {}, footprint: "Footprint",
};
// The upstream pack calls its active and gate packets diff and poly.
const drawingStyleNames = { OD: "diff", PO: "poly" };

function parseLayout(text, release, renderer) {
  const layers = new Map();
  const cells = new Map();
  let current;
  let top;
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    const [kind, name] = line.split(" ", 2);
    if (kind === "layer") {
      if (!release.shape_counts[name]) continue;
      const style = renderer.resolveStyle({ name: drawingStyleNames[name] ?? name });
      layers.set(name, { style, visible: !/^(?:VIA[1-8]|NW|PP|NP)$/.test(name) });
    } else if (kind === "cell") {
      current = { bounds: release.cell_bounds_nm[name], terminals: release.terminal_labels_nm?.[name] ?? [],
        paths: new Map(), instances: [] };
      cells.set(name, current);
    } else if (kind === "inst") {
      const [, child, x, y, orient, columns, rows, dx, dy] = line.match(
        / of=(\w+) at=\((-?\d+),(-?\d+)\) orient=(\w+)(?: array=\((\d+),(\d+)\) step=\((-?\d+),(-?\d+)\))?$/,
      );
      current.instances.push({ child, x: +x, y: +y, matrix: transforms[orient],
        columns: +(columns ?? 1), rows: +(rows ?? 1), dx: +(dx ?? 0), dy: +(dy ?? 0) });
    } else if (kind === "rect" || kind === "polygon") {
      const points = Array.from(line.matchAll(pointPattern), match => [+match[1], +match[2]]);
      if (!current.paths.has(name)) current.paths.set(name, new Path2D());
      const path = current.paths.get(name);
      if (kind === "rect") {
        const [[x, y], [right, upper]] = points;
        path.rect(x, y, right - x, upper - y);
      } else {
        path.moveTo(...points[0]);
        for (let i = 1; i < points.length; i++) path.lineTo(...points[i]);
        path.closePath();
      }
    } else if (kind === "top") {
      top = name;
    } else if (kind && !["layoutml", "units", "}"].includes(kind)) {
      throw new Error(`Unsupported LayoutML statement ${kind}`);
    }
  }
  for (const cell of cells.values()) {
    cell.footprint = cell.instances.length === 0 && cell.paths.size === 1 && cell.paths.has("Footprint");
  }
  if (!cells.has(top)) throw new Error("Missing LayoutML top cell");
  return { layers, cells, top };
}

function place(parent, instance, x = instance.x, y = instance.y) {
  const [a, b, c, d, ox, oy] = parent;
  const [e, f, g, h] = instance.matrix;
  return [a * e + c * f, b * e + d * f, a * g + c * h, b * g + d * h,
    ox + a * x + c * y, oy + b * x + d * y];
}

function transformedBounds([x, y, x1, y1], [a, b, c, d, ox, oy]) {
  const firstX = a * x + c * y + ox;
  const firstY = b * x + d * y + oy;
  const lastX = a * x1 + c * y1 + ox;
  const lastY = b * x1 + d * y1 + oy;
  return [Math.min(firstX, lastX), Math.min(firstY, lastY), Math.max(firstX, lastX), Math.max(firstY, lastY)];
}

const identity = [1, 0, 0, 1, 0, 0];

function landmarkBounds(model, labels) {
  const result = new Map();
  function visit(id, pose) {
    const cell = model.cells.get(id);
    if (id in labels) {
      const box = transformedBounds(cell.bounds, pose);
      const old = result.get(id);
      result.set(id, old ? [Math.min(old[0], box[0]), Math.min(old[1], box[1]),
        Math.max(old[2], box[2]), Math.max(old[3], box[3])] : box);
    }
    for (const inst of cell.instances) {
      if (model.cells.get(inst.child).instances.length || inst.child in labels) visit(inst.child, place(pose, inst));
    }
  }
  visit(model.top, identity);
  return result;
}

function installLayout(model, release, renderer) {
  const shell = document.querySelector("#chip-viewer");
  const canvas = document.querySelector("#layout-canvas");
  const stage = canvas.parentElement;
  const ctx = canvas.getContext("2d");
  const boxOverlay = document.querySelector("#layout-zoom-box");
  const scaleLabel = document.querySelector("#layout-scale");
  const locationLabel = document.querySelector("#layout-location");
  const fitButton = shell.querySelector('[data-layout-action="fit"]');
  const boxButton = shell.querySelector('[data-layout-action="box"]');
  const fullscreenButton = shell.querySelector('[data-layout-action="fullscreen"]');
  const terminalToggle = shell.querySelector("#layout-terminal-labels");
  const view = { x: 0, y: 0, scale: 1, bounds: release.bounds_nm, name: layoutStrings.die };
  const layerOrder = [...model.layers].sort(([, a], [, b]) => a.style.z - b.style.z);
  let queued = false;
  let fitMode = true;
  let boxStart;
  const touches = new Map();

  function transform([a, b, c, d, x, y], scale, width, height) {
    return { a: scale*a, b: -scale*b, c: scale*c, d: -scale*d,
      e: width/2+(x-view.x)*scale, f: height/2-(y-view.y)*scale };
  }

  function render() {
    queued = false;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(canvas.clientWidth * dpr);
    const h = Math.round(canvas.clientHeight * dpr);
    if (!w || !h) return;
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    ctx.fillStyle = window.LML_STYLE_PACKS[nativePack].background;
    ctx.fillRect(0, 0, w, h);
    const scale = dpr * view.scale;
    const halfWidth = w / (2*scale), halfHeight = h / (2*scale);
    const x0 = view.x-halfWidth, y0 = view.y-halfHeight, x1 = view.x+halfWidth, y1 = view.y+halfHeight;
    const visiblePaths = new Map(layerOrder.filter(([name, layer]) => layer.visible && (name !== "CO" || view.scale >= 0.018))
      .map(([name]) => [name, new Path2D()]));
    const showFootprints = visiblePaths.has("Footprint");
    const showTerminals = terminalToggle.checked && view.scale >= 0.13;
    const terminals = [];

    function draw(id, pose) {
      const cell = model.cells.get(id);
      if (cell.footprint && !showFootprints) return;
      const [left, bottom, right, top] = transformedBounds(cell.bounds, pose);
      if (right < x0 || left > x1 || top < y0 || bottom > y1 ||
          Math.max(right-left, top-bottom)*view.scale < (cell.footprint ? 2.5 : 0.8)) return;
      for (const inst of cell.instances) {
        const child = model.cells.get(inst.child);
        if (child.footprint && (!showFootprints || Math.max(child.bounds[2]-child.bounds[0], child.bounds[3]-child.bounds[1])*view.scale < 2.5)) continue;
        for (let row = 0; row < inst.rows; row++) {
          for (let col = 0; col < inst.columns; col++) {
            draw(inst.child, place(pose, inst, inst.x + col*inst.dx, inst.y + row*inst.dy));
          }
        }
      }
      if (!cell.paths.size && !cell.terminals.length) return;
      const matrix = transform(pose, scale, w, h);
      for (const [name, path] of cell.paths) visiblePaths.get(name)?.addPath(path, matrix);
      if (showTerminals) {
        for (const [label, x, y] of cell.terminals) {
          terminals.push([label, matrix.a*x + matrix.c*y + matrix.e, matrix.b*x + matrix.d*y + matrix.f]);
        }
      }
    }

    draw(model.top, identity);
    for (const [name, path] of visiblePaths) {
      renderer.paintDRFPath(ctx, path, model.layers.get(name).style, [], dpr);
    }
    const [x, y, right, top] = release.bounds_nm;
    const die = new Path2D();
    const rectangle = new Path2D();
    rectangle.rect(x, y, right-x, top-y);
    die.addPath(rectangle, transform(identity, scale, w, h));
    renderer.paintDRFPath(ctx, die, renderer.resolveStyle({ name: "Die outline" }), [], dpr);
    ctx.font = `600 ${11*dpr}px monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineWidth = 2*dpr;
    ctx.strokeStyle = "#000";
    ctx.fillStyle = "#fff";
    for (const terminal of terminals) {
      ctx.strokeText(...terminal);
      ctx.fillText(...terminal);
    }
    scaleLabel.textContent = `${(1 / view.scale / 1000).toPrecision(2)} µm/px`;
    locationLabel.textContent = `${view.name} · ${ (view.x/1000).toFixed(2) }, ${ (view.y/1000).toFixed(2) } µm`;
  }

  function requestPaint() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(render);
  }

  function fit(bounds = release.bounds_nm, name = layoutStrings.die) {
    const [x, y, x1, y1] = bounds;
    Object.assign(view, { x: (x+x1)/2, y: (y+y1)/2, name, bounds,
      scale: 0.89*Math.min(canvas.clientWidth/(x1-x), canvas.clientHeight/(y1-y)) });
    fitMode = true;
    requestPaint();
  }

  function zoom(factor, px = canvas.clientWidth/2, py = canvas.clientHeight/2) {
    const min = Math.min(canvas.clientWidth, canvas.clientHeight)/(1.4*(release.bounds_nm[2]-release.bounds_nm[0]));
    const scale = Math.max(min, Math.min(2, view.scale*factor));
    const delta = 1/view.scale-1/scale;
    view.x += (px-canvas.clientWidth/2)*delta;
    view.y -= (py-canvas.clientHeight/2)*delta;
    view.scale = scale;
    fitMode = false;
    requestPaint();
  }

  function pan(dx, dy) {
    view.x -= dx/view.scale;
    view.y += dy/view.scale;
    fitMode = false;
    requestPaint();
  }

  function boxMode(enabled) {
    boxButton.setAttribute("aria-pressed", String(enabled));
    canvas.dataset.box = String(enabled);
  }

  function xy(event) {
    const bounds = canvas.getBoundingClientRect();
    return [event.clientX-bounds.left, event.clientY-bounds.top];
  }

  canvas.addEventListener("wheel", event => {
    event.preventDefault();
    const units = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? canvas.clientHeight : 1;
    zoom(Math.exp(-Math.max(-240, Math.min(240, event.deltaY*units))*0.0025), ...xy(event));
  }, { passive: false });
  canvas.addEventListener("pointerdown", event => {
    if (event.button !== 0 && event.button !== 1) return;
    if (event.button === 1) event.preventDefault();
    canvas.setPointerCapture(event.pointerId);
    const point = xy(event);
    touches.set(event.pointerId, point);
    if (event.button === 0 && touches.size === 1 && (canvas.dataset.box === "true" || event.shiftKey)) boxStart = point;
    if (touches.size > 1) { boxStart = undefined; boxOverlay.hidden = true; }
  });
  canvas.addEventListener("auxclick", event => { if (event.button === 1) event.preventDefault(); });
  canvas.addEventListener("pointermove", event => {
    if (!touches.has(event.pointerId)) return;
    const previous = [...touches.values()];
    const next = xy(event);
    touches.set(event.pointerId, next);
    if (boxStart) {
      const [x, y] = boxStart;
      Object.assign(boxOverlay.style, { left: `${Math.min(x,next[0])}px`, top: `${Math.min(y,next[1])}px`,
        width: `${Math.abs(x-next[0])}px`, height: `${Math.abs(y-next[1])}px` });
      boxOverlay.hidden = false;
    } else if (previous.length === 1) {
      pan(next[0]-previous[0][0], next[1]-previous[0][1]);
    } else if (previous.length === 2) {
      const [a, b] = [...touches.values()];
      const [c, d] = previous;
      const priorDistance = Math.hypot(c[0]-d[0], c[1]-d[1]);
      const cx = (a[0]+b[0])/2, cy = (a[1]+b[1])/2;
      pan(cx-(c[0]+d[0])/2, cy-(c[1]+d[1])/2);
      if (priorDistance > 0) zoom(Math.hypot(a[0]-b[0], a[1]-b[1])/priorDistance, cx, cy);
    }
  });
  function releasePointer(event) {
    touches.delete(event.pointerId);
    if (!boxStart) return;
    const [x, y] = boxStart;
    const [x1, y1] = xy(event);
    boxStart = undefined;
    boxOverlay.hidden = true;
    boxMode(false);
    if (event.type !== "pointerup" || Math.min(Math.abs(x1-x), Math.abs(y1-y)) < 8) return;
    const worldX = px => view.x + (px-canvas.clientWidth/2)/view.scale;
    const worldY = py => view.y - (py-canvas.clientHeight/2)/view.scale;
    fit([worldX(Math.min(x, x1)), worldY(Math.max(y, y1)), worldX(Math.max(x, x1)), worldY(Math.min(y, y1))], layoutStrings.selection);
  }
  canvas.addEventListener("pointerup", releasePointer);
  canvas.addEventListener("pointercancel", releasePointer);

  const shortcuts = { "+": () => zoom(1.4), "=": () => zoom(1.4), "-": () => zoom(1/1.4), "0": () => fit(),
    ArrowLeft: () => pan(35, 0), ArrowRight: () => pan(-35, 0), ArrowUp: () => pan(0, 35), ArrowDown: () => pan(0, -35) };
  canvas.addEventListener("keydown", event => {
    const action = Object.hasOwn(shortcuts, event.key) && shortcuts[event.key];
    if (action) { event.preventDefault(); action(); }
  });
  shell.querySelector('[data-layout-action="in"]').addEventListener("click", () => zoom(1.4));
  shell.querySelector('[data-layout-action="out"]').addEventListener("click", () => zoom(1/1.4));
  fitButton.addEventListener("click", () => fit());
  boxButton.addEventListener("click", () => boxMode(canvas.dataset.box !== "true"));
  terminalToggle.addEventListener("change", requestPaint);
  fullscreenButton.addEventListener("click", () => {
    const action = document.fullscreenElement ? document.exitFullscreen() : shell.requestFullscreen();
    action.catch(() => { fullscreenButton.textContent = layoutStrings.fullError; });
  });
  document.addEventListener("fullscreenchange", () => {
    fullscreenButton.textContent = document.fullscreenElement ? layoutStrings.exit : layoutStrings.full;
  });
  for (const [id, bounds] of landmarkBounds(model, release.landmarks)) {
    const button = document.createElement("button");
    button.type = "button";
    const title = release.landmarks[id];
    button.textContent = layoutStrings.landmarks[title] ?? title;
    button.addEventListener("click", () => fit(bounds, button.textContent));
    document.querySelector("#layout-landmarks").append(button);
  }
  for (const [name, layer] of model.layers) {
    const label = document.createElement("label");
    const toggle = document.createElement("input");
    const swatch = document.createElement("i");
    toggle.type = "checkbox";
    toggle.checked = layer.visible;
    toggle.addEventListener("change", () => { layer.visible = toggle.checked; requestPaint(); });
    swatch.style.setProperty("--layer-color", layer.style.color);
    label.append(toggle, swatch, name === "Footprint" ? layoutStrings.footprint : name);
    document.querySelector("#layout-layers").append(label);
  }
  new ResizeObserver(() => fitMode ? fit(view.bounds, view.name) : requestPaint()).observe(stage);
  fit();
}

async function fetchLayoutPart(path) {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const response = await fetch(new URL(path, siteRoot), { signal: AbortSignal.timeout(18000) });
      if (!response.ok) throw new Error(`Layout data request failed (${response.status})`);
      return await response.arrayBuffer();
    } catch (error) {
      if (attempt === 1) throw error;
    }
  }
}

async function loadLayout() {
  const status = document.querySelector("#layout-loading");
  try {
    const renderer = window.LMLWebGLRenderer;
    if (!renderer?.paintDRFPath || !window.LML_STYLE_PACKS?.[nativePack]) {
      throw new Error(layoutStrings.rendererError);
    }
    renderer.setStylePack(nativePack);
    const manifest = await fetch(new URL("layout-data/release.json?display=terminals", siteRoot));
    if (!manifest.ok) throw new Error("Layout manifest request failed");
    const release = await manifest.json();
    let loaded = 0;
    const parts = await Promise.all(release.geometry_parts.map(async path => {
      const bytes = await fetchLayoutPart(path);
      status.textContent = layoutStrings.loading(++loaded, release.geometry_parts.length);
      return bytes;
    }));
    const stream = new Blob(parts).stream().pipeThrough(new DecompressionStream("gzip"));
    const bytes = await new Response(stream).text();
    installLayout(parseLayout(bytes, release, renderer), release, renderer);
    status.hidden = true;
  } catch (error) {
    status.textContent = `${layoutStrings.loadError} ${error.message}`;
  }
}

loadLayout();
