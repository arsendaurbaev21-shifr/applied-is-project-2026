import {$,$$,esc,t,api,attempt,modal,closeModal,badge,user} from './shared.js';

export function initSearch(ctx){
 let timer,sequence=0;
 async function open(){
  const dialog=modal(t('globalSearch'),`<form id="global-search-form" role="search"><label>${t('search')}<input id="global-search-input" type="search" maxlength="120" autocomplete="off" placeholder="${esc(t(user.Role==='admin'?'searchAdminHint':'searchClientHint'))}"></label></form><p class="muted search-help">${t('searchHelp')}</p><div id="global-search-results" aria-live="polite"></div>`,true,'search-dialog');
  const input=$('#global-search-input'),results=$('#global-search-results');input.focus();
  async function find(){const ticket=++sequence,q=input.value.trim();if(q.length<2){results.innerHTML=`<p class="empty">${t('searchMin')}</p>`;return;}results.innerHTML=`<p class="muted">${t('loading')}</p>`;
   try{const data=await api('/search?'+new URLSearchParams({q}));if(ticket!==sequence||!dialog.open||!results.isConnected)return;
    const group=(title,rows,body)=>rows.length?`<section class="search-group"><h3>${t(title)}</h3>${rows.map(body).join('')}</section>`:'';
    results.innerHTML=group('orders',data.orders,r=>`<button class="search-result" data-search-order="${r.OrderID}"><span><strong>${esc(r.OrderNumber)}</strong><small>${esc(r.FromCity+' → '+r.ToCity)}${user.Role==='admin'?' · '+esc(r.ClientName):''}</small></span>${badge(r.Status)}</button>`)+group('Clients',data.clients,r=>`<button class="search-result" data-search-table="Clients" data-search-id="${r.ClientID}"><span><strong>${esc(r.Name)}</strong><small>${t('openCard')}</small></span><b>↗</b></button>`)+group('Routes',data.routes,r=>`<button class="search-result" data-search-table="Routes" data-search-id="${r.RouteID}"><span><strong>${esc(r.FromCity+' → '+r.ToCity)}</strong><small>${esc(r.DistanceKm)} ${t('km')}</small></span><b>↗</b></button>`)+group('Cities',data.cities,r=>`<button class="search-result" data-search-table="Cities" data-search-id="${r.CityID}"><strong>${esc(r.Name)}</strong><b>↗</b></button>`);
    if(!results.innerHTML)results.innerHTML=`<div class="empty">${t('searchNoResults')}</div>`;
    $$('[data-search-order]',results).forEach(b=>b.onclick=()=>attempt(async()=>{closeModal('search-dialog');await ctx.showOrder(Number(b.dataset.searchOrder));}));
    $$('[data-search-table]',results).forEach(b=>b.onclick=()=>attempt(async()=>{closeModal('search-dialog');await ctx.openCatalog(b.dataset.searchTable,Number(b.dataset.searchId));}));
   }catch(error){if(ticket===sequence&&results.isConnected)results.textContent=t(error.code||'server_error');}
  }
  input.oninput=()=>{++sequence;clearTimeout(timer);timer=setTimeout(find,250);};$('#global-search-form').onsubmit=e=>{e.preventDefault();clearTimeout(timer);find();};
  dialog.onkeydown=e=>{if(!['ArrowDown','ArrowUp'].includes(e.key))return;const rows=$$('.search-result',results),i=rows.indexOf(document.activeElement);if(!rows.length)return;e.preventDefault();if(e.key==='ArrowDown')rows[Math.min(i+1,rows.length-1)].focus();else if(i<=0)input.focus();else rows[i-1].focus();};
  dialog.onclose=()=>{++sequence;clearTimeout(timer);};await find();
 }
 $('#global-search-button').onclick=open;$('#global-search-button').disabled=false;
 document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!$('dialog[open]'))open();}});
}
