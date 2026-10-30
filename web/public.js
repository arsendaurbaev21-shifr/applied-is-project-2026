import {routePickerHTML,bindRoutePicker} from './route-picker.js';
import {$,$$,esc,t,lang,translate,initCommon,api,session,user,attempt,options,field,formData,money,setZone} from './shared.js';
let catalogs=null,registering=false,mapController=null,mapLoading=false,calculatorPicker=null;
async function updateMap(){if(mapLoading)return;if(mapController){mapController.updateCatalogs(catalogs);mapController.setRoute($('#calculator-form').RouteID.value);return;}mapLoading=true;try{const {mountRouteMap}=await import('./route-map.js');mapController=await mountRouteMap($('#route-map-widget'),catalogs,id=>{const form=$('#calculator-form');calculatorPicker?.setRoute(id);$('#estimate').hidden=true;});mapController.setRoute($('#calculator-form').RouteID.value);}finally{mapLoading=false;}}
initCommon();
const query=new URLSearchParams(location.search);
function destination(){const p=new URLSearchParams();for(const k of ['route','tariff','weight']){const value=query.get(k);if(value&&/^\d+(\.\d+)?$/.test(value))p.set(k,value);}return user?.Role==='admin'?'/admin':'/customer'+(p.size?'?'+p:'#orders')+(p.size?'#newOrder':'');}
function loginForm(){
 $('#auth-form').innerHTML=`<form id="login-form">${registering?field('FullName','text','','maxlength="120" required autocomplete="name"')+field('Phone','tel','','maxlength="30" required autocomplete="tel"'):''}${field('Email','email','','maxlength="120" required autocomplete="username"')}${field('Password','password','','minlength="10" maxlength="128" required autocomplete="'+(registering?'new-password':'current-password')+'"')}<small class="muted">${esc(t('passwordHint'))}</small><button type="submit">${t(registering?'register':'login')}</button></form><div class="login-switch"><span>${t(registering?'haveAccount':'noAccount')}</span><button type="button" id="toggle-auth">${t(registering?'login':'register')}</button></div>`;
 $('#toggle-auth').onclick=()=>{registering=!registering;loginForm();};
 $('#login-form').onsubmit=e=>{e.preventDefault();attempt(async()=>{await api('/auth/'+(registering?'register':'login'),{method:'POST',body:formData(e.target)});await session();location.assign(destination());},e.target);};
}
function routeName(row){return (catalogs.Cities.find(c=>c.CityID===row.FromCityID)?.Name||'')+' → '+(catalogs.Cities.find(c=>c.CityID===row.ToCityID)?.Name||'');}
function renderCatalogs(){
 const form=$('#calculator-form');const prior=formData(form);
 const picker=$('#calculator-route');picker.innerHTML=routePickerHTML();calculatorPicker=bindRoutePicker(picker,catalogs,prior.RouteID||query.get('route'),id=>{if(id)mapController?.setRoute(id);$('#estimate').hidden=true;});
 form.TariffID.innerHTML=options(catalogs.Tariffs,'TariffID','Name',prior.TariffID||query.get('tariff'));
 $('#route-cards').innerHTML=catalogs.Routes.length?catalogs.Routes.slice(0,6).map(r=>`<article class="route-card"><div class="route-line">${esc(catalogs.Cities.find(c=>c.CityID===r.FromCityID)?.Name)}<span class="arrow">→</span>${esc(catalogs.Cities.find(c=>c.CityID===r.ToCityID)?.Name)}</div><p>${esc(t('DistanceKm'))}: ${esc(r.DistanceKm)}</p><button class="small light" data-route="${r.RouteID}">${t('calculate')} ↗</button></article>`).join(''):`<div class="empty">${t('empty')}</div>`;
 $$('[data-route]').forEach(button=>button.onclick=()=>{calculatorPicker.setRoute(button.dataset.route);mapController?.setRoute(form.RouteID.value);$('#estimate').hidden=true;$('#calculator').scrollIntoView({behavior:'smooth'});form.WeightKg.focus();});
}
async function loadCatalogs(){const data=await api('/public/catalogs');const changed=catalogs&&JSON.stringify(catalogs)!==JSON.stringify(data.data);if(catalogs&&!changed)return;catalogs=data.data;setZone(data.timezone);renderCatalogs();await updateMap();if(changed)$('#estimate').hidden=true;}
if(document.body.dataset.page==='login'){
 loginForm();attempt(()=>session());document.addEventListener('language',()=>{const values=formData($('#login-form'));loginForm();for(const [key,value] of Object.entries(values)){$('#login-form').elements.namedItem(key).value=value;}});
}else{
 attempt(async()=>{await session();await loadCatalogs();if(user){const link=$('.header-actions .button');link.textContent=t('cabinet');link.href=user.Role==='admin'?'/admin':'/customer';}});
 $('#calculator-form').onsubmit=e=>{e.preventDefault();attempt(async()=>{const values=formData(e.target);const result=await api('/public/quote?'+new URLSearchParams(values));const params=new URLSearchParams({route:values.RouteID,tariff:values.TariffID,weight:values.WeightKg});$('#estimate').hidden=false;$('#estimate').innerHTML=`<div><small class="muted">${t('estimate')}</small><br><strong>${money(result.amount)}</strong></div><a class="button accent" href="${user?.Role==='client'?'/customer':'/login'}?${params}#newOrder">${t('request')} →</a>`;},e.target);};
 $('#calculator-form').addEventListener('input',()=>{$('#estimate').hidden=true;mapController?.setRoute($('#calculator-form').RouteID.value);});
 document.addEventListener('language',()=>{if(catalogs){renderCatalogs();mapController?.dispose();mapController=null;attempt(updateMap);}$('#estimate').hidden=true;});
 setInterval(()=>{if(document.visibilityState==='visible'&&!document.activeElement.closest('#calculator-form,#route-map-widget'))attempt(()=>loadCatalogs());},60000);
}
