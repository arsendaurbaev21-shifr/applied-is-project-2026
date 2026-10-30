import {$,$$,esc,t,initCommon,api,session,user,attempt,setZone} from './shared.js';
import {overview,orderList,newOrder,showOrder} from './orders.js';
import {catalogs} from './catalogs.js';
import {documents,reports} from './office.js';
import {profile,users,support} from './account.js';
import {inbox,refreshNotificationCount} from './delivery.js';
import {initSearch} from './search.js';
const ctx={catalogs:{},schema:{},catalogTable:'Cities',openOrder:null,wizard:null,navOpen:{},
 async loadCatalogs(){const result=await api(user.Role==='admin'?'/catalogs':'/public/catalogs');ctx.catalogs=result.data;if(result.schema)ctx.schema=result.schema;if(result.timezone)setZone(result.timezone);},
 async render(){await render();},async showOrder(id){await showOrder(ctx,id);},
 async openCatalog(table,id){ctx.catalogTable=table;ctx.catalogFocus=id;if(current()==='catalogs')await render();else location.hash='catalogs';},
 async refreshBackground(){const key=current();if(key==='dashboard')await overview(ctx);if(key==='orders')await orderList(ctx,true);}
};
function current(){const value=location.hash.slice(1)||'dashboard';return ['dashboard','orders','newOrder','catalogs','documents','reports','support','profile','users','notifications'].includes(value)?value:'dashboard';}
function navigation(){
 const button=key=>`<button data-page="${key}" class="${current()===key?'active':''}" ${current()===key?'aria-current="page"':''}>${esc(t(key))}</button>`;
 const group=(name,keys)=>`<details data-nav-group="${name}" ${ctx.navOpen[name]||keys.includes(current())?'open':''}><summary>${t(name)}</summary>${keys.map(button).join('')}</details>`;
 $('#sidebar-nav').innerHTML=(user.Role==='admin'?['dashboard','orders','notifications','documents','reports','catalogs']:['dashboard','orders','newOrder','notifications','documents','reports']).map(button).join('')+group('people',user.Role==='admin'?['users','support','profile']:['support','profile']);
 $$('[data-page]',$('#sidebar-nav')).forEach(b=>b.onclick=()=>{if(current()===b.dataset.page)return;location.hash=b.dataset.page;document.body.classList.remove('menu-open');$('.mobile-menu')?.setAttribute('aria-expanded','false');});
 $$('[data-nav-group]').forEach(el=>el.ontoggle=()=>{ctx.navOpen[el.dataset.navGroup]=el.open;});
 $('#breadcrumb-current').textContent=t(current());$('#breadcrumb-home').onclick=()=>{location.hash='dashboard';};
}
let renderQueue=Promise.resolve();
function render(){renderQueue=renderQueue.catch(()=>{}).then(renderNow);return renderQueue;}
async function renderNow(){
 if(ctx.wizard){try{await ctx.wizard.flush();}catch(error){history.replaceState(null,'',location.pathname+'#newOrder');throw error;}ctx.wizard.dispose();ctx.wizard=null;}
 const key=current();navigation();$('#page-title').textContent=t(key);$('#content').innerHTML=`<p class="muted">${t('loading')}</p>`;
 const handlers={dashboard:()=>overview(ctx),orders:()=>orderList(ctx),newOrder:()=>newOrder(ctx),catalogs:async()=>{const focus=ctx.catalogFocus;ctx.catalogFocus=null;await catalogs(ctx,ctx.catalogTable,focus);},documents:()=>documents(ctx),reports:()=>reports(ctx),support:()=>support(ctx),notifications:()=>inbox(ctx),profile,users};
 if((user.Role==='client'&&['catalogs','users'].includes(key))||(user.Role==='admin'&&key==='newOrder')){location.hash='dashboard';return;}await handlers[key]();
}
initCommon();
attempt(async()=>{
 await session();if(!user){location.assign('/login');return;}const expected=user.Role==='admin'?'/admin':'/customer';if(location.pathname!==expected){location.assign(expected);return;}
 $('#user-name').textContent=user.FullName;await ctx.loadCatalogs();addEventListener('hashchange',()=>attempt(()=>render()));await render();initSearch(ctx);await refreshNotificationCount();
 $('#notification-button').onclick=()=>{if(current()==='notifications')attempt(()=>render());else location.hash='notifications';};$('#notification-button').disabled=false;
 
 $('#refresh').onclick=()=>attempt(async()=>{if(ctx.wizard){await ctx.wizard.flush();await render();return;}await ctx.loadCatalogs();if(current()==='orders')await orderList(ctx,true);else if(current()==='documents')await documents(ctx,true);else if(!['profile','reports'].includes(current()))await render();await refreshNotificationCount();});
 $('#logout').onclick=()=>attempt(async()=>{if(ctx.wizard)await ctx.wizard.flush();await api('/auth/logout',{method:'POST'});ctx.wizard?.dispose();location.assign('/');});
 setInterval(()=>{if(document.visibilityState==='visible')attempt(()=>refreshNotificationCount());if(document.visibilityState==='visible'&&!$('dialog[open]')&&!$('#content').contains(document.activeElement)&&['dashboard','orders'].includes(current()))attempt(()=>ctx.refreshBackground());},30000);
 document.addEventListener('language',()=>attempt(async()=>{const wizard=!!ctx.wizard,forms=$$('input,textarea,select',$('#content')).map(el=>({name:el.name,value:el.value,checked:el.checked})),oid=ctx.openOrder;await render();if(!wizard){const elements=$$('input,textarea,select',$('#content'));forms.forEach((v,i)=>{if(elements[i]?.name===v.name){elements[i].value=v.value;elements[i].checked=v.checked;}});}if(oid)await showOrder(ctx,oid);}));
});
