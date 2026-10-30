import {$,esc,t} from './shared.js';

// The form submits the existing RouteID contract. Only city lists enter the DOM.
export function routePickerHTML(){return `<div class="route-picker"><label>${t('FromCity')}<select data-city-from aria-label="${esc(t('FromCity'))}" required></select></label><button type="button" class="small light route-swap" aria-label="${esc(t('swapCities'))}">⇄</button><label>${t('ToCity')}<select data-city-to aria-label="${esc(t('ToCity'))}" required></select></label><select name="RouteID" hidden aria-hidden="true" tabindex="-1"></select><small class="route-km" role="status"></small></div>`;}

export function bindRoutePicker(root,catalogs,initial,onChange=()=>{}){
 const from=$('[data-city-from]',root),to=$('[data-city-to]',root),id=$('[name=RouteID]',root),note=$('.route-km',root);
 let data=catalogs;let byId,byPair,outgoing,cityMap;
 function index(){byId=new Map(data.Routes.map(r=>[String(r.RouteID),r]));byPair=new Map(data.Routes.map(r=>[r.FromCityID+':'+r.ToCityID,r]));outgoing=new Map();for(const r of data.Routes){if(!outgoing.has(r.FromCityID))outgoing.set(r.FromCityID,new Set());outgoing.get(r.FromCityID).add(r.ToCityID);}cityMap=new Map(data.Cities.map(c=>[c.CityID,c]));}
 function opts(ids){return [...ids].map(n=>cityMap.get(n)).filter(Boolean).sort((a,b)=>a.Name.localeCompare(b.Name,'kk')).map(c=>`<option value="${c.CityID}">${esc(c.Name)}</option>`).join('');}
 function destinations(prior){to.innerHTML=opts(outgoing.get(Number(from.value))||[]);if([...to.options].some(o=>o.value===String(prior)))to.value=String(prior);}
 function renderRoute(notify=false){const r=byPair.get(from.value+':'+to.value);id.innerHTML=r?`<option value="${r.RouteID}">${r.RouteID}</option>`:'';note.textContent=r?`${Number(r.DistanceKm).toLocaleString(undefined,{maximumFractionDigits:2})} ${t('km')} · ${t(r.DistanceSource?'roadDistance':'manualDistance')}`:t('noRoute');if(notify){id.dispatchEvent(new Event('input',{bubbles:true}));id.dispatchEvent(new Event('change',{bubbles:true}));onChange(r?.RouteID);}}
 function setRoute(value){const r=byId.get(String(value));if(!r){id.innerHTML=value?`<option value="${esc(value)}" selected>${esc(value)}</option>`:'';from.value='';to.value='';note.textContent=t('noRoute');return;}from.value=String(r.FromCityID);destinations(r.ToCityID);renderRoute();}
 function populate(value){index();from.innerHTML=opts(outgoing.keys());destinations();setRoute(value||data.Routes[0]?.RouteID);}
 from.onchange=()=>{destinations(to.value);renderRoute(true);};to.onchange=()=>renderRoute(true);
 $('.route-swap',root).onclick=()=>{const r=byPair.get(to.value+':'+from.value);if(r){setRoute(r.RouteID);renderRoute(true);}};
 populate(initial);
 return {setRoute,update(next){const prior=id.value;data=next;populate(prior);},getRoute(){return byId.get(id.value);}};
}
