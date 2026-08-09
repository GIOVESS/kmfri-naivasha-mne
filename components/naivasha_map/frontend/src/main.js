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

// Colors brightened relative to the literal brand green (#265B01/#152C00) —
// against a dark basemap those read as near-black. This keeps site markers
// and polygon fills legible without changing the brand's light-mode assets.
const NURSERY_SITE_RENDERER = {
  type: "simple",
  symbol: {
    type: "simple-marker",
    color: "#5BC221",
    outline: { color: "#0E1116", width: 1.5 },
    size: 11,
  },
};

const RESTORATION_POLYGON_RENDERER = {
  type: "unique-value",
  field: "phase",
  uniqueValueInfos: [
    { value: "pilot", symbol: fillSymbol("#3A8A00") },
    { value: "target", symbol: fillSymbol("#8FD14F") },
    { value: "baseline", symbol: fillSymbol("#9BA3AE") },
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

  // Dark basemap: keeps Lake Naivasha's shoreline and built-up/residential
  // areas legible while matching the app's dark theme. Requires a valid
  // ArcGIS API key (esriConfig.apiKey, set above) — without one, Esri's
  // hosted basemap tiles won't load and only the GeoJSON overlay layers
  // below (which render client-side) will be visible.
  const map = new Map({ basemap: "arcgis-dark-gray" });

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
