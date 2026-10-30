import {$,esc,t,initCommon,api,session,attempt,dateTime,badge} from './shared.js';
initCommon();
let lastResult=null;
function draw(result){
 const o=result.order;const stages=['New','Confirmed','InTransit','Delivered'];const position=stages.indexOf(o.Status);
 $('#tracking-result').innerHTML=`<section class="panel tracking-result"><div class="toolbar"><div><small class="muted">${t('OrderNumber')}</small><h2>${esc(o.OrderNumber)}</h2></div>${badge(o.Status)}</div><div class="tracking-route"><strong>${esc(o.FromCity)}</strong><span>→</span><strong>${esc(o.ToCity)}</strong></div><div class="tracking-steps">${stages.map((state,i)=>`<div class="${i<=position?'done':''}"><b>${i<position?'✓':i+1}</b><span>${t(state)}</span></div>`).join('')}</div>${o.Status==='Cancelled'?`<p class="notice">${t('trackingCancelled')}</p>`:''}<div class="detail-grid"><div class="detail-field"><small>${t('PickupDate')}</small>${esc(o.PickupDate)}</div><div class="detail-field"><small>${t('expectedArrival')}</small>${o.ExpectedArrivalAt?esc(dateTime(o.ExpectedArrivalAt)):t('notScheduled')}</div></div><h3>${t('history')}</h3><ol class="tracking-history">${result.history.map(h=>`<li><span>${t(h.NewStatus)}</span><time>${esc(dateTime(h.ChangedAt))}</time></li>`).join('')}</ol><p class="time-note">${t('trackingLiveHint')}</p></section>`;
}
async function lookup(){
 const input=$('#tracking-code');const code=input.value.trim().toUpperCase();
 lastResult=null;$('#tracking-result').innerHTML='';
 const result=await api('/public/tracking',{method:'POST',body:{code}});
 lastResult=result;history.replaceState(null,'','/track#'+encodeURIComponent(code));draw(result);
}
$('#tracking-form').onsubmit=e=>{e.preventDefault();attempt(lookup,e.target);};
document.addEventListener('language',()=>{if(lastResult)draw(lastResult);});
addEventListener('hashchange',()=>{const code=location.hash.slice(1);if(/^[a-fA-F0-9]{64}$/.test(code)){$('#tracking-code').value=code;attempt(lookup,$('#tracking-form'));}});
attempt(async()=>{await session();const code=location.hash.slice(1);if(code){$('#tracking-code').value=code;await lookup();}},$('#tracking-form'));
