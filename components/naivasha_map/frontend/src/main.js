import esriConfig from "@arcgis/core/config.js";
import Map from "@arcgis/core/Map.js";
import Basemap from "@arcgis/core/Basemap.js";
import WebTileLayer from "@arcgis/core/layers/WebTileLayer.js";
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

/**
 * Basemap: CARTO Dark Matter tiles (free, no API key, no referrer allowlisting
 * required) rather than Esri's hosted basemap-styles service. Clearly shows
 * Lake Naivasha's shoreline, road network, and built-up/residential areas.
 *
 * This is a deliberate scope decision, not a workaround for a broken key:
 * a fully authoritative, custom-digitized basemap (papyrus extent, gazetted
 * boundaries, verified road/residential layers) needs an Esri Creator seat
 * and real digitization work — that's a Phase 1 line item, not a demo-stage
 * requirement. See system-design.md ADR-5.
 */
function buildDarkBasemap() {
  return new Basemap({
    baseLayers: [
      new WebTileLayer({
        urlTemplate: "https://{subDomain}.basemaps.cartocdn.com/dark_all/{level}/{col}/{row}.png",
        subDomains: ["a", "b", "c", "d"],
        copyright: "© OpenStreetMap contributors © CARTO",
      }),
    ],
    title: "carto-dark",
    id: "carto-dark",
  });
}

function geojsonToBlobUrl(featureCollection) {
  const blob = new Blob([JSON.stringify(featureCollection)], { type: "application/json" });
  return URL.createObjectURL(blob);
}

let view = null;
let nurseryLayer = null;
let polygonLayer = null;

function buildMap(args) {
  // Kept for future Places/Geocoding/Routing use (privileges already enabled
  // on this key) — no longer required for the basemap itself, see below.
  esriConfig.apiKey = args.arcgisApiKey;

  const map = new Map({ basemap: buildDarkBasemap() });

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
