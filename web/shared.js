import {t,lang,setLanguage,translate} from './i18n.js';
export {t,lang,translate};
export const $=(selector,root=document)=>root.querySelector(selector);
export const $$=(selector,root=document)=>[...root.querySelectorAll(selector)];
export const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export let csrf='',user=null,timezone='Asia/Qyzylorda';
export function setZone(value){timezone=value;}
export const money=value=>new Intl.NumberFormat(lang==='kk'?'kk-KZ':lang==='ru'?'ru-KZ':'en-GB',{minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(value||0))+' ₸';
export function dateTime(value){if(!value)return '—';if(/^\d{4}-\d{2}-\d{2}$/.test(value))return value;return new Intl.DateTimeFormat(lang==='en'?'en-GB':lang+'-KZ',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23',timeZone:timezone}).format(new Date(value));}
export function localInput(value){if(!value)return '';const parts=new Intl.DateTimeFormat('sv-SE',{timeZone:timezone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(value));return parts.replace(' ','T');}
export const today=()=>localInput(new Date().toISOString()).slice(0,10);
export const badge=value=>`<span class="badge status-${esc(value)}">${esc(t(value))}</span>`;
export function toast(message,bad=false){const el=$('#toast');el.textContent=message;el.className='toast show'+(bad?' bad':'');clearTimeout(el.timer);el.timer=setTimeout(()=>el.classList.remove('show'),7000);}
export async function api(path,options={}){
 const headers={'Accept-Language':lang,...options.headers};if(options.method&&options.method!=='GET')headers['X-CSRF-Token']=csrf;
 if(options.body&&!(options.body instanceof FormData)){headers['Content-Type']='application/json';options.body=JSON.stringify(options.body);}
 let response;try{response=await fetch('/api'+path,{credentials:'same-origin',...options,headers});}catch{throw {code:'network'};}
 const data=await response.json();if(!response.ok)throw data.error||{code:'server_error'};
 if(data.csrf)csrf=data.csrf;return data;
}
export async function session(){const result=await api('/auth/session');user=result.user;return result;}
export async function attempt(fn,form=null){try{if(form){$('.form-error',form)?.remove();$$('button[type=submit]',form).forEach(x=>x.disabled=true);}return await fn();}catch(error){const message=t(error.code||'server_error');if(form){const el=document.createElement('p');el.className='form-error';el.setAttribute('role','alert');el.textContent=(error.field?t(error.field)+': ':'')+message;form.append(el);if(error.field)form.elements.namedItem(error.field)?.focus();}else toast(message,true);if(error.code==='login_required')setTimeout(()=>location.assign('/login'),1000);}finally{if(form)$$('button[type=submit]',form).forEach(x=>x.disabled=false);}}
export function formData(form){return Object.fromEntries(new FormData(form));}
export function options(rows,pk,label,selected='',blank=false){return (blank?`<option value="">${esc(t('choose'))}</option>`:'')+rows.map(r=>`<option value="${esc(r[pk])}" ${String(r[pk])===String(selected)?'selected':''}>${esc(typeof label==='function'?label(r):r[label])}</option>`).join('');}
export function field(name,type='text',value='',extra=''){return `<label>${esc(t(name))}<input name="${esc(name)}" type="${type}" value="${esc(value)}" ${extra}></label>`;}
export function select(name,html,extra=''){return `<label>${esc(t(name))}<select name="${name}" ${extra}>${html}</select></label>`;}
export function area(name,value='',max=500){return `<label class="span2">${esc(t(name))}<textarea name="${name}" maxlength="${max}" rows="3">${esc(value)}</textarea></label>`;}
export function table(rows,columns,actions=null){if(!rows.length)return `<div class="empty">${esc(t('empty'))}</div>`;return `<div class="table-wrap"><table><thead><tr>${columns.map(c=>`<th>${esc(t(typeof c==='string'?c:c.key))}</th>`).join('')}${actions?`<th>${t('actions')}</th>`:''}</tr></thead><tbody>${rows.map(row=>`<tr>${columns.map(col=>{let key=typeof col==='string'?col:col.key;let value=row[key];let body=typeof col==='object'&&col.render?col.render(row):['QuotedAmount','PaidAmount','BalanceAmount','Amount'].includes(key)?esc(money(value)):key==='Status'?badge(value):key==='IsActive'?esc(t(value?'yes':'no')):key.endsWith('At')||key==='OrderDate'?esc(dateTime(value)):esc(value??'—');return '<td class="'+(['QuotedAmount','PaidAmount','BalanceAmount','Amount','OrderNumber','PickupDate','Status'].includes(key)?'nowrap':key==='route'?'route-cell':'')+'">'+body+'</td>';}).join('')}${actions?'<td>'+actions(row)+'</td>':''}</tr>`).join('')}</tbody></table></div>`;}
export function actionMenu(html){return `<details class="actions"><summary aria-label="${esc(t('actions'))}">${t('actions')} ▾</summary><div>${html}</div></details>`;}
export function modal(title,html,wide=false,id='dialog'){const dialog=$('#'+id);$('.dialog-title',dialog).textContent=title;$('.dialog-body',dialog).innerHTML=html;dialog.classList.toggle('wide',wide);if(!dialog.open)dialog.showModal();return dialog;}
export function closeModal(id='dialog'){$('#'+id).close();}
export function confirmAction(message){return new Promise(resolve=>{const d=document.createElement('dialog');d.className='dialog';d.innerHTML=`<div class="dialog-body"><h3>${esc(message)}</h3><div class="form-actions"><button data-yes>${t('confirm')}</button><button class="light" data-no>${t('cancel')}</button></div></div>`;document.body.append(d);d.addEventListener('close',()=>{const accepted=d.returnValue==='yes';d.remove();resolve(accepted);},{once:true});$('[data-yes]',d).onclick=()=>d.close('yes');$('[data-no]',d).onclick=()=>d.close('no');d.showModal();});}
export function printHTML(title,html,orientation='portrait',meta=''){
 const win=window.open('','_blank');if(!win){toast(t('popup'),true);return;}
 win.document.write(`<!doctype html><html lang="${lang}"><head><meta charset="utf-8"><title>${esc(title)}</title><link rel="stylesheet" href="/static/print.css"><style>@page{size:A4 ${orientation}}</style></head><body><header><strong>QazCargo</strong><span>${esc(t('brandSub'))}</span></header><h1>${esc(title)}</h1><p class="meta">${esc(dateTime(new Date().toISOString()))} · ${esc(timezone)}</p>${meta?'<p>'+esc(meta)+'</p>':''}${html}<footer>${esc(t('paymentHint'))}</footer><script src="/static/print.js" defer></script></body></html>`);win.document.close();
}
export function initCommon(){
 document.documentElement.lang=lang;
 $$('.language').forEach(el=>{el.value=lang;el.addEventListener('change',()=>setLanguage(el.value));});
 document.addEventListener('language',()=>{$$('.language').forEach(el=>el.value=lang);translate();});
 $$('dialog').forEach(d=>{d.addEventListener('click',e=>{if(e.target===d)d.close();});$('.dialog-close',d)?.addEventListener('click',()=>d.close());});
 document.addEventListener('click',e=>$$('details.actions[open]').forEach(d=>{if(!d.contains(e.target))d.open=false;}));
 document.addEventListener('keydown',e=>{if(e.key==='Escape')$$('details.actions[open]').forEach(d=>{d.open=false;$('summary',d).focus();});});
 $('.mobile-menu')?.addEventListener('click',()=>{document.body.classList.toggle('menu-open');$('.mobile-menu').setAttribute('aria-expanded',document.body.classList.contains('menu-open'));});
 translate();
}
