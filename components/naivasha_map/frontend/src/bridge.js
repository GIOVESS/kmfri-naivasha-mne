import { Streamlit } from "streamlit-component-lib";

/**
 * Thin wrapper around streamlit-component-lib for this component's needs:
 * - onRender(callback): callback(renderData.args) fires on every Streamlit rerun
 * - setSiteSelection(siteId): pushes a click result back to Python
 */

export function initBridge(onRenderArgs) {
  Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, (event) => {
    const args = event.detail.args;
    onRenderArgs(args);
  });
  Streamlit.setComponentReady();
}

let clickCounter = 0;

export function setSiteSelection(siteId) {
  // A monotonic counter, not just { site_id }. Streamlit component functions
  // keep returning whatever was last sent via setComponentValue on every
  // subsequent script rerun, even after Python passes a different prop in —
  // it only counts as a "new" value when the payload itself changes. Without
  // the counter, clicking Reset Filters (a pure Python-side state change)
  // would see the map component's stale click payload replayed and clobber
  // the reset right back to the previously-selected site. See
  // dashboard/filters.py's sync_from_map_component for the other half of this.
  clickCounter += 1;
  Streamlit.setComponentValue({ site_id: siteId, click_seq: clickCounter });
}

export function setFrameHeight(height) {
  Streamlit.setFrameHeight(height);
}
