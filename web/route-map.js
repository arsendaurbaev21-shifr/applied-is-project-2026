import {$,esc,t} from './shared.js';

import {routePickerHTML,bindRoutePicker} from './route-picker.js';
const majorCities=new Set(['Астана','Алматы','Шымкент','Қарағанды','Ақтөбе','Қостанай','Павлодар','Петропавл','Көкшетау','Орал','Атырау','Ақтау','Қызылорда','Түркістан','Тараз','Талдықорған','Қонаев','Семей','Өскемен','Жезқазған']);
const project=([lon,lat])=>[(lon-67)*Math.cos(48*Math.PI/180),lat-48];
const clamp=(n,a,b)=>Math.min(b,Math.max(a,n));

export async function mountRouteMap(root,catalogs,onSelect){
 root.innerHTML=`<div class="map-shell"><div class="map-top"><div><span class="map-eyebrow">QAZCARGO / 3D</span><h2>${t('mapTitle')}</h2></div><span class="map-mode">${t('mapMode')}</span></div><div class="map-viewport" role="img" aria-label="${esc(t('mapTitle'))}"><div class="map-labels"></div><div class="map-tooltip" hidden></div><p class="map-loading">${t('loading')}</p></div><div class="map-footer">${routePickerHTML()}<div class="map-distance"><small>${t('DistanceKm')}</small><strong>—</strong></div><div class="map-controls"><button type="button" class="small" data-map="in" aria-label="${esc(t('mapZoomIn'))}">＋</button><button type="button" class="small" data-map="out" aria-label="${esc(t('mapZoomOut'))}">−</button><button type="button" class="small" data-map="reset">${t('mapReset')}</button></div></div><p class="map-hint">${t('mapHint')}</p><p class="map-coverage"></p><p class="map-disclaimer">${t('roadMapDisclaimer')} <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">© OpenStreetMap</a> · <a href="https://project-osrm.org/" target="_blank" rel="noopener">OSRM</a> · <a href="https://www.geonames.org/" target="_blank" rel="noopener">GeoNames</a> / Wikidata</p><p class="map-data-date"></p><p class="map-missing" hidden>${t('mapMissing')}</p></div>`;
 const viewport=$('.map-viewport',root),labels=$('.map-labels',root),tooltip=$('.map-tooltip',root);let picker=null;
 let data=catalogs,current=catalogs.Routes[0]?.RouteID,renderer=null,draw=()=>{},routeObjects=[],markers=[],disposed=false;
 let scene,camera,THREE,yaw=0,pitch=.85,distance=26;
 function name(id){return data.Cities.find(c=>c.CityID===id)?.Name||'—';}
 function centre(id){const c=data.Cities.find(c=>c.CityID===id);return c?.Latitude!=null&&c?.Longitude!=null?[Number(c.Longitude),Number(c.Latitude)]:null;}
 function coverage(){$('.map-mode',root).textContent=data.Cities.filter(c=>centre(c.CityID)).length+' '+t('mapCities');$('.map-coverage',root).textContent=data.Cities.filter(c=>centre(c.CityID)).length+' '+t('mapCities')+' · '+data.Routes.length.toLocaleString()+' '+t('mapRoutes');}
 function disposeObjects(objects){for(const item of objects){scene.remove(item);item.geometry?.dispose();item.material?.dispose();}objects.length=0;}
 function selected(id,emit=false){
  current=Number(id);picker?.setRoute(current);const route=data.Routes.find(r=>r.RouteID===current);
  $('.map-distance strong',root).textContent=route?Number(route.DistanceKm).toLocaleString(): '—';
  const a=route&&centre(route.FromCityID),b=route&&centre(route.ToCityID);
  $('.map-data-date',root).textContent=route?.DistanceSource?route.DistanceSource+' · '+String(route.DistanceUpdatedAt).slice(0,10):t('manualDistance');
  $('.map-missing',root).hidden=!!(a&&b);
  if(renderer){
   disposeObjects(routeObjects);labels.innerHTML='';markers=[];
   for(const cityRow of data.Cities){
    const coord=centre(cityRow.CityID);if(!coord)continue;const city=cityRow.Name;
    const [x,z]=project(coord);const active=route&&(cityRow.CityID===route.FromCityID||cityRow.CityID===route.ToCityID);
    const point=new THREE.Mesh(new THREE.SphereGeometry(active ? 0.16 : 0.09,16,10),new THREE.MeshBasicMaterial({color:active?0xffab49:0x88b2ca}));point.position.set(x,.48,-z);point.userData.cityId=cityRow.CityID;point.userData.cityName=city;scene.add(point);routeObjects.push(point);
    if(active){const ring=new THREE.Mesh(new THREE.TorusGeometry(.29,.035,8,36),new THREE.MeshBasicMaterial({color:0xffab49}));ring.rotation.x=Math.PI/2;ring.position.set(x,.4,-z);scene.add(ring);routeObjects.push(ring);}
    const label=document.createElement('span');label.className='map-city'+(active?' active':'');label.textContent=city;labels.append(label);markers.push({el:label,position:point.position.clone(),active:!!active,show:!!active||majorCities.has(city)});
   }
   if(a&&b){
    const [ax,az]=project(a),[bx,bz]=project(b);const height=Math.max(1.2,Math.hypot(ax-bx,az-bz)*.27);
    const curve=new THREE.QuadraticBezierCurve3(new THREE.Vector3(ax,.5,-az),new THREE.Vector3((ax+bx)/2,height,-(az+bz)/2),new THREE.Vector3(bx,.5,-bz));
    const tube=new THREE.Mesh(new THREE.TubeGeometry(curve,64,.055,8,false),new THREE.MeshBasicMaterial({color:0xffa53d}));scene.add(tube);routeObjects.push(tube);
    const mid=curve.getPoint(.6),direction=curve.getTangent(.6).normalize();
    const arrow=new THREE.Mesh(new THREE.ConeGeometry(.16,.44,12),new THREE.MeshBasicMaterial({color:0xffcf8f}));arrow.position.copy(mid);arrow.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),direction);scene.add(arrow);routeObjects.push(arrow);
   }
   draw();
  }
  if(emit&&route)onSelect(route.RouteID);
 }
 picker=bindRoutePicker($('.route-picker',root),data,current,id=>selected(id,true));coverage();selected(current);
 const controller={setRoute:id=>selected(id),updateCatalogs:next=>{data=next;picker.update(data);coverage();selected(data.Routes.some(r=>r.RouteID===current)?current:data.Routes[0]?.RouteID);},dispose:()=>{disposed=true;resize.disconnect();renderer?.dispose();scene?.traverse(o=>{o.geometry?.dispose();if(o.material)o.material.dispose();});}};
 let resize={disconnect(){}};
 try{
  THREE=await import('./vendor/three.module.js');
  const response=await fetch('/static/data/kazakhstan.json');if(!response.ok)throw new Error('map-data');const shapeData=await response.json();
  if(disposed)return controller;
  renderer=new THREE.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.75));renderer.setClearColor(0x102b42,0);
  renderer.domElement.tabIndex=0;renderer.domElement.setAttribute('aria-label',t('mapKeyboard'));viewport.prepend(renderer.domElement);
  $('.map-loading',root).remove();scene=new THREE.Scene();camera=new THREE.PerspectiveCamera(39,1,.1,150);
  scene.add(new THREE.HemisphereLight(0xc6e7ff,0x1b3045,2.4));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(-6,18,12);scene.add(light);
  const polygons=shapeData.geometry.type==='Polygon'?[shapeData.geometry.coordinates]:shapeData.geometry.coordinates;
  for(const rings of polygons){
   const outline=rings[0].map(project);const shape=new THREE.Shape(outline.map(([x,y])=>new THREE.Vector2(x,y)));
   for(const hole of rings.slice(1))shape.holes.push(new THREE.Path(hole.map(project).map(([x,y])=>new THREE.Vector2(x,y))));
   const mesh=new THREE.Mesh(new THREE.ExtrudeGeometry(shape,{depth:.28,bevelEnabled:false}),new THREE.MeshStandardMaterial({color:0x285875,metalness:.25,roughness:.7}));mesh.rotation.x=-Math.PI/2;scene.add(mesh);
   const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(outline.map(([x,y])=>new THREE.Vector3(x,.3,-y))),new THREE.LineBasicMaterial({color:0x73a2ba}));scene.add(line);
  }
  const grid=new THREE.GridHelper(60,30,0x244c65,0x193c54);grid.position.y=-.08;scene.add(grid);
  draw=()=>{
   if(disposed)return;
   const w=viewport.clientWidth,h=viewport.clientHeight;if(!w||!h)return;
   camera.aspect=w/h;camera.updateProjectionMatrix();const fitDistance=distance*Math.max(1,1.9/camera.aspect);camera.position.set(Math.sin(yaw)*Math.cos(pitch)*fitDistance,Math.sin(pitch)*fitDistance,Math.cos(yaw)*Math.cos(pitch)*fitDistance);camera.lookAt(0,0,0);
   renderer.render(scene,camera);
   const boxes=[];for(const marker of [...markers].sort((a,b)=>Number(b.active)-Number(a.active))){const p=marker.position.clone().project(camera);marker.el.hidden=!marker.show||p.z>1;if(marker.el.hidden)continue;const width=marker.el.offsetWidth,height=marker.el.offsetHeight,x=clamp((p.x*.5+.5)*w,width/2,w-width/2);let top=(-p.y*.5+.5)*h+9;for(const box of boxes){if(x+width/2>box.left-4&&x-width/2<box.right+4&&top<box.bottom+4&&top+height>box.top-4){if(!marker.active){marker.el.hidden=true;break;}top=box.bottom+4;}}if(marker.el.hidden)continue;top=clamp(top,12,h-height-4);marker.el.style.left=x+'px';marker.el.style.top=(top-9)+'px';boxes.push({left:x-width/2,right:x+width/2,top,bottom:top+height});}
  };
  function size(){renderer.setSize(viewport.clientWidth,viewport.clientHeight);draw();}
  resize=new ResizeObserver(size);resize.observe(viewport);size();selected(current);
  let pointer=null,dragged=false;const raycaster=new THREE.Raycaster();
  function hit(e){const rect=canvas.getBoundingClientRect();raycaster.setFromCamera(new THREE.Vector2((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1),camera);return raycaster.intersectObjects(routeObjects.filter(o=>o.userData.cityId))[0]?.object;}
  const canvas=renderer.domElement;
  canvas.onpointerdown=e=>{dragged=false;pointer={id:e.pointerId,x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);};
  canvas.onpointermove=e=>{if(!pointer){const city=hit(e);tooltip.hidden=!city;if(city){tooltip.textContent=city.userData.cityName;tooltip.style.left=Math.min(viewport.clientWidth-120,e.offsetX+14)+'px';tooltip.style.top=Math.max(10,e.offsetY-30)+'px';}return;}if(pointer.id!==e.pointerId)return;if(Math.abs(e.clientX-pointer.x)+Math.abs(e.clientY-pointer.y)>2)dragged=true;tooltip.hidden=true;yaw-=(e.clientX-pointer.x)*.008;pitch=clamp(pitch+(e.clientY-pointer.y)*.006,.25,1.45);pointer={...pointer,x:e.clientX,y:e.clientY};draw();};
  canvas.onpointerup=e=>{if(!dragged){const city=hit(e),prior=data.Routes.find(r=>r.RouteID===current);if(city&&prior){const from=e.shiftKey?city.userData.cityId:prior.FromCityID,to=e.shiftKey?prior.ToCityID:city.userData.cityId;const next=data.Routes.find(r=>r.FromCityID===from&&r.ToCityID===to);if(next)selected(next.RouteID,true);}}pointer=null;};canvas.onpointercancel=()=>pointer=null;canvas.onpointerleave=()=>{tooltip.hidden=true;};
  canvas.onkeydown=e=>{let handled=true;if(e.key==='ArrowLeft')yaw-=.15;else if(e.key==='ArrowRight')yaw+=.15;else if(e.key==='ArrowUp')pitch=clamp(pitch+.1,.25,1.45);else if(e.key==='ArrowDown')pitch=clamp(pitch-.1,.25,1.45);else if(e.key==='+')distance=clamp(distance-2,15,55);else if(e.key==='-')distance=clamp(distance+2,15,55);else handled=false;if(handled){e.preventDefault();draw();}};
  root.querySelectorAll('[data-map]').forEach(button=>button.onclick=()=>{if(button.dataset.map==='reset'){yaw=0;pitch=.85;distance=26;}else distance=clamp(distance+(button.dataset.map==='in'?-3:3),15,55);draw();});
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();$('.map-hint',root).textContent=t('mapFallback');});
 }catch{
  renderer?.dispose();renderer=null;$('.map-loading',root)?.remove();
  viewport.innerHTML=`<div class="map-fallback"><span aria-hidden="true">◉ ───── → ◉</span><p>${t('mapFallback')}</p></div>`;
  root.querySelectorAll('[data-map]').forEach(b=>b.disabled=true);
 }
 return controller;
}
