import esriConfig from "@arcgis/core/config.js";
import Map from "@arcgis/core/Map.js";
import MapView from "@arcgis/core/views/MapView.js";
import GeoJSONLayer from "@arcgis/core/layers/GeoJSONLayer.js";
import Graphic from "@arcgis/core/Graphic.js";
import "@esri/calcite-components/dist/calcite/calcite.css";
import { defineCustomElements } from "@esri/calcite-components/dist/loader";

import { initBridge, setSiteSelection, setFrameHeight } from "./bridge.js";
import "./style.css";

defineCustomElements(window);

const NURSERY_SITE_RENDERER = {
  type: "simple",
  symbol: {
    type: "simple-marker",
    color: "#265B01",
    outline: { color: "#152C00", width: 1.5 },
    size: 10,
  },
};

const RESTORATION_POLYGON_RENDERER = {
  type: "unique-value",
  field: "phase",
  uniqueValueInfos: [
    { value: "pilot", symbol: fillSymbol("#265B01") },
    { value: "target", symbol: fillSymbol("#152C00") },
    { value: "baseline", symbol: fillSymbol("#8a8a8a") },
  ],
};

function fillSymbol(color) {
  return {
    type: "simple-fill",
    color: [...hexToRgb(color), 0.35],
    outline: { color, width: 1.5 },
  };
}

function hexToRgb(hex) {
  const v = parseInt(hex.slice(1), 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
}

function geojsonToBlobUrl(featureCollection) {
  const blob = new Blob([JSON.stringify(featureCollection)], { type: "application/json" });
  return URL.createObjectURL(blob);
}

let view = null;
let nurseryLayer = null;
let polygonLayer = null;

function buildMap(args) {
  esriConfig.apiKey = args.arcgisApiKey;

  const map = new Map({ basemap: "arcgis-topographic" });

  nurseryLayer = new GeoJSONLayer({
    url: geojsonToBlobUrl(args.nurserySites || { type: "FeatureCollection", features: [] }),
    renderer: NURSERY_SITE_RENDERER,
    outFields: ["*"],
    title: "Nursery sites",
  });

  polygonLayer = new GeoJSONLayer({
    url: geojsonToBlobUrl(args.restorationPolygons || { type: "FeatureCollection", features: [] }),
    renderer: RESTORATION_POLYGON_RENDERER,
    outFields: ["*"],
    title: "Restoration polygons",
  });

  map.addMany([polygonLayer, nurseryLayer]);

  view = new MapView({
    container: "map-container",
    map,
    center: [36.32, -0.77], // Lake Naivasha
    zoom: 12,
  });

  view.on("click", async (event) => {
    const hit = await view.hitTest(event, { include: nurseryLayer });
    const graphicHit = hit.results.find((r) => r.graphic?.layer === nurseryLayer);
    if (graphicHit) {
      setSiteSelection(graphicHit.graphic.attributes.id);
    }
  });

  view.when(() => setFrameHeight(args.height || 600));
}

function updateSelection(selectedSiteId) {
  if (!view || selectedSiteId == null) return;
  nurseryLayer.queryFeatures({ where: `id = ${selectedSiteId}`, returnGeometry: true }).then((result) => {
    const g = result.features[0];
    if (g) {
      view.goTo({ target: g.geometry, zoom: 15 }, { duration: 400 });
    }
  });
}

initBridge((args) => {
  if (!view) {
    buildMap(args);
  } else {
    updateSelection(args.selectedSiteId);
    setFrameHeight(args.height || 600);
  }
});
