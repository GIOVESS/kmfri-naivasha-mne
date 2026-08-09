import esriConfig from "@arcgis/core/config.js";
import Map from "@arcgis/core/Map.js";
import Basemap from "@arcgis/core/Basemap.js";
import WebTileLayer from "@arcgis/core/layers/WebTileLayer.js";
import MapView from "@arcgis/core/views/MapView.js";
import GeoJSONLayer from "@arcgis/core/layers/GeoJSONLayer.js";
import Graphic from "@arcgis/core/Graphic.js";
import Zoom from "@arcgis/core/widgets/Zoom.js";
import Home from "@arcgis/core/widgets/Home.js";
import Compass from "@arcgis/core/widgets/Compass.js";
import ScaleBar from "@arcgis/core/widgets/ScaleBar.js";
import "@arcgis/core/assets/esri/themes/dark/main.css"; // required for widgets (Zoom/Home/
                                                          // Compass/ScaleBar) to render styled
                                                          // and positioned — without this they
                                                          // exist in the DOM but are invisible
import "@esri/calcite-components/dist/calcite/calcite.css";
import { defineCustomElements } from "@esri/calcite-components/dist/loader";

import { initBridge, setSiteSelection, setFrameHeight } from "./bridge.js";
import "./style.css";

defineCustomElements(window);

// Colors tuned for a light Voyager basemap: distinct hues per restoration
// phase (rather than two similar greens, which were tuned for contrast
// against a dark basemap and are hard to tell apart on a light one) and a
// dark marker outline for definition against light tiles.
const NURSERY_SITE_RENDERER = {
  type: "simple",
  symbol: {
    type: "simple-marker",
    color: "#2E7D32",
    outline: { color: "#FFFFFF", width: 2 },
    size: 11,
  },
};

const RESTORATION_POLYGON_RENDERER = {
  type: "unique-value",
  field: "phase",
  uniqueValueInfos: [
    { value: "pilot", symbol: fillSymbol("#2E7D32") },
    { value: "target", symbol: fillSymbol("#1565C0") },
    { value: "baseline", symbol: fillSymbol("#757575") },
  ],
};

function fillSymbol(color) {
  return {
    type: "simple-fill",
    color: [...hexToRgb(color), 0.4],
    outline: { color, width: 2 },
  };
}

function hexToRgb(hex) {
  const v = parseInt(hex.slice(1), 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
}

/**
 * Basemap: CARTO Voyager tiles (free, no API key, no referrer allowlisting
 * required) rather than Esri's hosted basemap-styles service. Voyager is a
 * light, high-contrast style — lake shoreline, roads, and built-up/
 * residential areas are all clearly labeled and colored, which reads better
 * than a dark basemap for this kind of site-inspection use case even though
 * the surrounding app chrome is dark-themed.
 *
 * This is a deliberate scope decision, not a workaround for a broken key:
 * a fully authoritative, custom-digitized basemap (papyrus extent, gazetted
 * boundaries, verified road/residential layers) needs an Esri Creator seat
 * and real digitization work — that's a Phase 1 line item, not a demo-stage
 * requirement. See system-design.md ADR-5.
 */
function buildBasemap() {
  return new Basemap({
    baseLayers: [
      new WebTileLayer({
        // @2x retina tiles — crisper labels/roads than the base resolution,
        // which read as washed-out on high-DPI screens.
        urlTemplate: "https://{subDomain}.basemaps.cartocdn.com/rastertiles/voyager/{level}/{col}/{row}@2x.png",
        subDomains: ["a", "b", "c", "d"],
        copyright: "© OpenStreetMap contributors © CARTO",
      }),
    ],
    title: "carto-voyager",
    id: "carto-voyager",
  });
}

function geojsonToBlobUrl(featureCollection) {
  const blob = new Blob([JSON.stringify(featureCollection)], { type: "application/json" });
  return URL.createObjectURL(blob);
}

let view = null;
let nurseryLayer = null;
let polygonLayer = null;
let nurseryLayerView = null;
let homeViewpoint = null;
let hoverHighlight = null;
let selectionHighlight = null;
let previousSelectedSiteId; // undefined until first render — distinguishes
                            // "never selected anything" from "selection was
                            // just cleared", so Reset Filters snaps the view
                            // back but initial load doesn't animate for no reason

const HOME_VIEWPOINT = { center: [36.32, -0.77], zoom: 12 }; // Lake Naivasha
const TRANSITION = { duration: 400, easing: "ease-in-out" };

function buildMap(args) {
  // Kept for future Places/Geocoding/Routing use (privileges already enabled
  // on this key) — no longer required for the basemap itself, see below.
  esriConfig.apiKey = args.arcgisApiKey;

  const map = new Map({ basemap: buildBasemap() });

  nurseryLayer = new GeoJSONLayer({
    url: geojsonToBlobUrl(args.nurserySites || { type: "FeatureCollection", features: [] }),
    renderer: NURSERY_SITE_RENDERER,
    outFields: ["*"],
    title: "Nursery sites",
    popupTemplate: {
      title: "{site_name}",
      content: [
        {
          type: "fields",
          fieldInfos: [
            { fieldName: "site_code", label: "Site code" },
            { fieldName: "stakeholder", label: "Stakeholder" },
            { fieldName: "capacity_units", label: "Capacity (seedlings)" },
            { fieldName: "established", label: "Established" },
          ],
        },
      ],
    },
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
    center: HOME_VIEWPOINT.center,
    zoom: HOME_VIEWPOINT.zoom,
    // Shared style for both the hover and selection highlights below — amber
    // reads clearly against the light basemap and doesn't collide with the
    // marker/polygon palette (greens, blue, grey).
    highlightOptions: { color: "#FFC107", haloOpacity: 0.9, fillOpacity: 0.25 },
  });

  view.on("click", async (event) => {
    const hit = await view.hitTest(event, { include: nurseryLayer });
    const graphicHit = hit.results.find((r) => r.graphic?.layer === nurseryLayer);
    if (graphicHit) {
      setSiteSelection(graphicHit.graphic.attributes.id);
    }
  });

  // Hover feedback: pointer cursor + a light highlight halo over whatever
  // marker is under the cursor, distinct from the (persistent) selection
  // highlight below — makes it visually obvious the markers are clickable
  // before the user commits to a click.
  view.on("pointer-move", async (event) => {
    const hit = await view.hitTest(event, { include: nurseryLayer });
    const graphicHit = hit.results.find((r) => r.graphic?.layer === nurseryLayer);

    view.container.style.cursor = graphicHit ? "pointer" : "default";

    if (hoverHighlight) {
      hoverHighlight.remove();
      hoverHighlight = null;
    }
    if (graphicHit && nurseryLayerView) {
      hoverHighlight = nurseryLayerView.highlight(graphicHit.graphic);
    }
  });

  view.whenLayerView(nurseryLayer).then((layerView) => {
    nurseryLayerView = layerView;
  });

  view.when(() => {
    // Home resets to the initial Lake Naivasha extent. Captured here (once
    // the view has actually loaded and view.viewpoint reflects the center/
    // zoom passed to the constructor) rather than reconstructed from raw
    // coordinates, which is more reliable across projections/scale rounding.
    homeViewpoint = view.viewpoint.clone();
    const homeWidget = new Home({ view, viewpoint: homeViewpoint });
    view.ui.add(homeWidget, "top-left");
    view.ui.add(new Zoom({ view }), "top-left");
    view.ui.add(new Compass({ view }), "top-left");
    view.ui.add(new ScaleBar({ view, unit: "metric" }), "bottom-left");

    setFrameHeight(args.height || 600);
    previousSelectedSiteId = args.selectedSiteId; // avoid a spurious reset-animation on the next rerun
  });
}

function setSelectionHighlight(graphicOrNull) {
  if (selectionHighlight) {
    selectionHighlight.remove();
    selectionHighlight = null;
  }
  if (graphicOrNull && nurseryLayerView) {
    selectionHighlight = nurseryLayerView.highlight(graphicOrNull);
  }
}

function updateSelection(selectedSiteId) {
  if (!view) return;

  if (selectedSiteId == null) {
    setSelectionHighlight(null);
    // Only snap back to the home extent on an actual clear (Reset Filters),
    // not on every rerun while nothing is selected — otherwise a user who's
    // manually panned around with no site selected would get yanked back
    // on unrelated Streamlit reruns.
    if (previousSelectedSiteId != null && homeViewpoint) {
      view.goTo(homeViewpoint, TRANSITION);
    }
    previousSelectedSiteId = selectedSiteId;
    return;
  }

  previousSelectedSiteId = selectedSiteId;
  nurseryLayer.queryFeatures({ where: `id = ${selectedSiteId}`, returnGeometry: true }).then((result) => {
    const g = result.features[0];
    if (g) {
      view.goTo({ target: g.geometry, zoom: 15 }, TRANSITION);
      setSelectionHighlight(g);
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
