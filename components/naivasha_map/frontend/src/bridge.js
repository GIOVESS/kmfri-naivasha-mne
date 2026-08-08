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

export function setSiteSelection(siteId) {
  Streamlit.setComponentValue({ site_id: siteId });
}

export function setFrameHeight(height) {
  Streamlit.setFrameHeight(height);
}
