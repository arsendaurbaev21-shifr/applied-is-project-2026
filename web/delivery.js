import {$,$$,esc,t,api,attempt,field,dateTime,badge,toast} from './shared.js';

export const deliveryKeys=['SenderName','SenderPhone','PickupAddress','RecipientName','RecipientPhone','DeliveryAddress','PickupWindowStart','PickupWindowEnd'];
export function deliveryFields(order={}){
 return `<div class="span2 delivery-heading"><h3>${t('deliveryDetails')}</h3><p>${t('deliveryHint')}</p></div>`+
 deliveryKeys.map(key=>field(key,key.includes('Window')?'time':key.includes('Phone')?'tel':'text',order[key]||'',
 `required ${key.includes('Window')?'':`maxlength="${key.includes('Address')?250:key.includes('Phone')?30:120}"`}`)).join('');
}
export function deliverySummary(o){
 return `<section class="delivery-summary"><h3>${t('deliveryDetails')}</h3><div class="detail-grid">${deliveryKeys.map(key=>`<div class="detail-field"><small>${t(key)}</small>${esc(o[key]||'—')}</div>`).join('')}</div></section>`;
}
export function trackingCard(o){
 return `<section class="tracking-share"><div><h3>${t('tracking')}</h3><p>${t('trackingPrivateHint')}</p></div><div class="form-actions"><a class="button small light" href="/track#${esc(o.TrackingCode)}" target="_blank" rel="noopener">${t('openTracking')} ↗</a><button class="small" id="copy-tracking">${t('copyLink')}</button></div><input class="tracking-link" id="tracking-link" readonly aria-label="${esc(t('trackingLink'))}" value="${esc(location.origin+'/track#'+o.TrackingCode)}"></section>`;
}
export function bindTracking(){
 $('#copy-tracking')?.addEventListener('click',()=>attempt(async()=>{
  const input=$('#tracking-link');
  try{await navigator.clipboard.writeText(input.value);toast(t('linkCopied'));}
  catch{input.focus();input.select();toast(t('copyManually'));}
 }));
}
export async function refreshNotificationCount(){
 const data=await api('/notifications');const el=$('#notification-count');
 if(el){el.textContent=data.unread>99?'99+':String(data.unread);el.hidden=!data.unread;}
 return data;
}
export async function inbox(ctx){
 let cursor=null,rows=[];
 $('#content').innerHTML=`<div class="toolbar"><div><h2>${t('notifications')}</h2><p class="muted">${t('notificationHint')}</p></div><button class="light" id="read-all">${t('markAllRead')}</button></div><div id="notice-list"></div><button class="light" id="more-notices" hidden>${t('loadMore')}</button>`;
 async function load(append=false){
  const data=await api('/notifications'+(append&&cursor?'?before='+cursor:''));cursor=data.nextBefore;
  rows=append?[...rows,...data.rows]:data.rows;
  $('#notice-list').innerHTML=rows.length?rows.map(r=>`<article class="notice-card ${r.ReadAt?'':'unread'}"><span class="notice-dot" aria-hidden="true"></span><div><small>${esc(r.OrderNumber)} · ${esc(dateTime(r.CreatedAt))}</small><h3>${t('notice_'+r.EventType)} ${r.NewStatus?badge(r.NewStatus):''}</h3><span class="muted">${t(r.ReadAt?'noticeRead':'noticeUnread')}</span></div><div class="notice-actions"><button class="small light" data-notice-open="${r.NotificationID}">${t('open')}</button>${r.ReadAt?'':`<button class="small" data-notice-read="${r.NotificationID}">${t('markRead')}</button>`}</div></article>`).join(''):`<div class="panel empty">${t('noNotifications')}</div>`;
  $('#more-notices').hidden=!cursor;$('#read-all').disabled=!data.unread;
  const count=$('#notification-count');count.textContent=data.unread>99?'99+':String(data.unread);count.hidden=!data.unread;
  $$('[data-notice-read]').forEach(b=>b.onclick=()=>attempt(async()=>{await api(`/notifications/${b.dataset.noticeRead}/read`,{method:'POST'});await load();}));
  $$('[data-notice-open]').forEach(b=>b.onclick=()=>attempt(async()=>{const row=rows.find(r=>r.NotificationID===Number(b.dataset.noticeOpen));await api(`/notifications/${row.NotificationID}/read`,{method:'POST'});await load();await ctx.showOrder(row.OrderID);}));
 }
 $('#read-all').onclick=()=>attempt(async()=>{await api('/notifications/read-all',{method:'POST'});await load();});
 $('#more-notices').onclick=()=>attempt(()=>load(true));
 await load();
}
