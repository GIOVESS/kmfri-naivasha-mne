import{i as u,d as f}from"./index-DPlziPlJ.js";import{f as i}from"./locale-60f8ca58-D9cw43B-.js";/*!
 * All material copyright ESRI, All Rights Reserved, unless otherwise specified.
 * See https://github.com/Esri/calcite-design-system/blob/dev/LICENSE.md for details.
 * v2.13.2
 */const t={};async function M(e,s){const a=`${s}_${e}`;return t[a]||(t[a]=fetch(f(`./assets/${s}/t9n/messages_${e}.json`)).then(n=>(n.ok||o(),n.json())).catch(()=>o())),t[a]}function o(){throw new Error("could not fetch component message bundle")}function c(e){e.messages={...e.defaultMessages,...e.messageOverrides}}function d(){}async function m(e){e.defaultMessages=await r(e,e.effectiveLocale),c(e)}async function r(e,s){if(!u())return{};const{el:a}=e,g=a.tagName.toLowerCase().replace("calcite-","");return M(i(s,"t9n"),g)}async function y(e,s){e.defaultMessages=await r(e,s),c(e)}function C(e){e.onMessagesChange=h}function L(e){e.onMessagesChange=d}function h(){c(this)}export{C as c,L as d,m as s,y as u};
