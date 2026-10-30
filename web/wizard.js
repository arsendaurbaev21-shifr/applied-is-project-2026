import {routePickerHTML,bindRoutePicker} from './route-picker.js';
import {$,$$,esc,t,api,attempt,user,field,select,area,options,money,dateTime,today,toast,confirmAction} from './shared.js';
import {cargoFields,routeLabel,showOrder} from './orders.js';
import {deliveryKeys,deliveryFields,deliverySummary} from './delivery.js';

export async function orderWizard(ctx){
 await ctx.loadCatalogs();const stored=(await api('/drafts/current')).draft;
 const params=new URLSearchParams(location.search),initial=stored?.payload||{RouteID:params.get('route'),TariffID:params.get('tariff'),PickupDate:today(),SenderName:user.FullName,items:[{WeightKg:params.get('weight')||''}]};
 let step=stored?.step||0,key=stored?.key||crypto.randomUUID(),revision=stored?.revision||0;
 let timer,savePromise=null,disposed=false,submitting=false,failed=false,quoteValue=null,transition=false;
 const labels=['wizardRoute','wizardPeople','wizardCargo','wizardReview'];
 $('#content').innerHTML=`<div class="wizard-top"><div><h2>${t('newOrder')}</h2><p class="muted">${t('wizardHint')}</p></div><div class="draft-controls"><span id="draft-status" role="status"></span><button class="small light" id="draft-save">${t('saveDraft')}</button><button class="small light" id="draft-discard">${t('startOver')}</button></div></div><div id="draft-alert" class="notice warm" hidden></div><div class="wizard-steps" aria-label="${esc(t('wizardProgress'))}">${labels.map((label,i)=>`<button type="button" data-step="${i}"><b>${i+1}</b><span>${t(label)}</span></button>`).join('')}</div><form id="new-order" class="panel wizard-panel" novalidate><section data-stage="0"><h3>${t('wizardRoute')}</h3><p class="muted step-hint">${t('routeStepHint')}</p><div class="form-grid">${routePickerHTML()}${select('TariffID',options(ctx.catalogs.Tariffs.filter(r=>r.IsActive),'TariffID','Name',initial.TariffID),'required')}${field('PickupDate','date',initial.PickupDate||today(),'required')}${area('Notes',initial.Notes||'')}</div></section><section data-stage="1" hidden><div class="form-grid">${deliveryFields(initial)}</div></section><section data-stage="2" hidden><div class="toolbar"><h3>${t('wizardCargo')}</h3><button class="small light" type="button" id="add-cargo">+ ${t('addCargo')}</button></div><p class="notice">${t('cargoHint')}</p><div id="cargo-items"></div><p class="field-error" id="cargo-error" role="alert" hidden></p></section><section data-stage="3" hidden><h3>${t('wizardReview')}</h3><p class="muted step-hint">${t('reviewHint')}</p><div id="order-review"></div></section><div class="wizard-actions"><button type="button" class="light" id="wizard-back">← ${t('backStep')}</button><span id="wizard-position"></span><button type="submit" class="accent" id="wizard-next"></button></div><p class="form-error" id="wizard-error" role="alert" hidden></p></form>`;
 const form=$('#new-order'),status=$('#draft-status');$$('h3',form).forEach(el=>el.tabIndex=-1);
 function keepSelection(el,value){if(value&&![...el.options].some(o=>o.value===String(value))){const opt=new Option(t('catalogUnavailable'),String(value),true,true);opt.disabled=true;el.add(opt);el.value=String(value);}}
 bindRoutePicker($('.route-picker',form),ctx.catalogs,initial.RouteID);keepSelection(form.TariffID,initial.TariffID);
 const add=(item={})=>{const div=document.createElement('div');div.className='cargo-item';div.innerHTML=`<div class="cargo-title"><strong></strong><button class="small danger remove-cargo" type="button">${t('removeCargo')}</button></div><div class="form-grid">${cargoFields(ctx,item)}</div>`;$('#cargo-items').append(div);keepSelection($('select',div),item.CargoTypeID);$('.remove-cargo',div).onclick=()=>{div.remove();numberItems();changed();};numberItems();};
 function numberItems(){$$('.cargo-item',form).forEach((div,i)=>$('.cargo-title strong',div).textContent=t('cargoItem')+' '+(i+1));$('#add-cargo').disabled=$$('.cargo-item',form).length>=100;}
 for(const item of initial.items||[{}])add(item);
 $('#add-cargo').onclick=()=>{add();changed();};
 function values(){const data=Object.fromEntries([...new FormData(form)].filter(([k])=>['RouteID','TariffID','PickupDate','Notes',...deliveryKeys].includes(k)));data.items=$$('.cargo-item',form).map(div=>Object.fromEntries($$('input,select',div).map(el=>[el.name,el.value])));return data;}
 const snapshot=()=>JSON.stringify({payload:values(),step});let saved=snapshot();
 function state(message,bad=false){if(disposed)return;status.textContent=message;status.classList.toggle('save-failed',bad);}
 state(stored?t('draftResumed')+' · '+dateTime(stored.updatedAt):t('draftAutomatic'));
 function errorText(error){return (error.field?t(error.field)+': ':'')+t(error.code||'server_error');}
 function showError(error){const el=$('#wizard-error');el.hidden=false;el.textContent=errorText(error);}
 function schedule(){clearTimeout(timer);timer=setTimeout(()=>{save().catch(()=>{});},900);}
 function changed(){quoteValue=null;failed=false;state(t('draftUnsaved'));$('#wizard-error').hidden=true;schedule();}
 form.addEventListener('input',e=>{e.target.removeAttribute('aria-invalid');e.target.closest('label')?.querySelector('.field-error')?.remove();changed();});
 form.addEventListener('change',changed);
 async function save(force=false){
  clearTimeout(timer);if(disposed)return;if(submitting)throw {code:'draftSubmitting'};
  if(savePromise){await savePromise;return save(force);}
  if(!force&&saved===snapshot()&&!failed)return;
  const content=snapshot();state(t('draftSaving'));
  savePromise=(async()=>{
   try{const result=await api('/drafts/'+key,{method:'PUT',body:{...JSON.parse(content),revision}});revision=result.draft.revision;saved=content;failed=false;state(t('draftSaved')+' · '+dateTime(result.draft.updatedAt));$('#draft-alert').hidden=true;}
   catch(error){failed=true;state(t('draftSaveFailed'),true);const alert=$('#draft-alert');alert.hidden=false;alert.textContent=errorText(error)+' '+t('draftKeepOpen');throw error;}
  })();
  try{await savePromise;}finally{savePromise=null;}
  if(saved!==snapshot())return save();
 }
 const unload=e=>{if(saved!==snapshot()||savePromise||failed||submitting){e.preventDefault();e.returnValue='';}};
 addEventListener('beforeunload',unload);
 const control={flush:()=>save(),dispose:()=>{disposed=true;clearTimeout(timer);removeEventListener('beforeunload',unload);},relabel:()=>{}};ctx.wizard=control;
 $('#draft-save').onclick=()=>save(true).catch(showError);
 $('#draft-discard').onclick=async()=>{
  if(!await confirmAction(t('discardDraftConfirm')))return;
  try{await save();if(revision)await api('/drafts/'+key,{method:'DELETE',body:{revision}});control.dispose();ctx.wizard=null;history.replaceState(null,'',location.pathname+'#newOrder');await ctx.render();}catch(error){showError(error);}finally{transition=false;form.inert=false;const next=$('#wizard-next');if(next)next.disabled=false;}
 };
 function fieldError(el,message){el.setAttribute('aria-invalid','true');let hint=el.closest('label').querySelector('.field-error');if(!hint){hint=document.createElement('small');hint.className='field-error';hint.id='error-'+el.name+'-'+$$('.field-error',form).length;el.closest('label').append(hint);el.setAttribute('aria-describedby',hint.id);}hint.textContent=message;}
 function validate(index){
  const stage=$(`[data-stage="${index}"]`,form);$$('.field-error',stage).filter(el=>el.id!=='cargo-error').forEach(el=>el.remove());$$('[aria-invalid]',stage).forEach(el=>el.removeAttribute('aria-invalid'));
  let first=null;
  for(const el of $$('input,select,textarea',stage)){
   if(el.hidden)continue;
   let message='';if(!el.checkValidity())message=t(el.validity.valueMissing?'requiredField':'invalidField');
   if(el.tagName==='SELECT'&&(!el.value||el.selectedOptions[0]?.disabled))message=t('catalogUnavailable');
   if(el.name.includes('Phone')&&el.value&&(!/^\+?[0-9 ()-]{7,30}$/.test(el.value)||el.value.replace(/\D/g,'').length<7||el.value.replace(/\D/g,'').length>15))message=t('phone_invalid');
   if(el.name==='PickupWindowEnd'&&el.value&&form.PickupWindowStart.value&&el.value<=form.PickupWindowStart.value)message=t('pickup_window');
   if(message){fieldError(el,message);first??=el;}
  }
  if(index===2&&!$$('.cargo-item',form).length){$('#cargo-error').hidden=false;$('#cargo-error').textContent=t('cargo_required');first=$('#add-cargo');}else if(index===2)$('#cargo-error').hidden=true;
  if(first){showStep(index,false);first.focus();return false;}return true;
 }
 function showStep(index,persist=true){step=index;$$('[data-stage]',form).forEach(el=>el.hidden=Number(el.dataset.stage)!==index);$$('[data-step]').forEach(el=>{const n=Number(el.dataset.step);el.classList.toggle('active',n===index);el.classList.toggle('complete',n<index);if(n===index)el.setAttribute('aria-current','step');else el.removeAttribute('aria-current');});$('#wizard-back').hidden=index===0;$('#wizard-position').textContent=(index+1)+' / 4';$('#wizard-next').textContent=index===3?t('sendOrder'):t('nextStep')+' →';if(persist&&saved!==snapshot())schedule();}
 async function review(){
  for(let i=0;i<3;i++)if(!validate(i))return false;
  const data=values();const cents=data.items.reduce((sum,item)=>{const [whole,frac='']=Number(item.WeightKg).toFixed(2).split('.');return sum+BigInt(whole)*100n+BigInt(frac.padEnd(2,'0'));},0n);
  const result=await api('/public/quote?'+new URLSearchParams({RouteID:data.RouteID,TariffID:data.TariffID,WeightKg:`${cents/100n}.${String(cents%100n).padStart(2,'0')}`}));if(disposed)return false;quoteValue=result.amount;
  const route=ctx.catalogs.Routes.find(r=>String(r.RouteID)===data.RouteID),tariff=ctx.catalogs.Tariffs.find(r=>String(r.TariffID)===data.TariffID);
  $('#order-review').innerHTML=`<div class="review-heading"><div><small>${t('route')}</small><h2>${esc(routeLabel(ctx,route))}</h2><p>${esc(data.PickupDate)} · ${esc(tariff.Name)}</p></div><div class="review-price"><small>${t('QuotedAmount')}</small><strong>${money(quoteValue)}</strong></div></div>${deliverySummary(data)}<h3>${t('cargo')}</h3>${data.items.map((item,i)=>`<div class="review-item"><strong>${i+1}. ${esc(item.Description)}</strong><span>${esc(item.WeightKg)} ${t('kg')} · ${esc(item.VolumeM3)} m³ · ${esc(item.Quantity)} ${t('packages')}</span></div>`).join('')}${data.Notes?`<p class="notice">${esc(data.Notes)}</p>`:''}`;return true;
 }
 async function move(index){if(index>step){for(let i=step;i<Math.min(index,3);i++)if(!validate(i))return;}if(index===3&&!await review())return;showStep(index);$(`[data-stage="${step}"] h3`,form)?.focus();}
 async function jump(index){if(transition||submitting)return;transition=true;form.inert=true;try{await move(index);}finally{transition=false;form.inert=false;}}
 $$('[data-step]').forEach(b=>b.onclick=()=>attempt(()=>jump(Number(b.dataset.step))));$('#wizard-back').onclick=()=>attempt(()=>jump(step-1));
 form.onsubmit=async e=>{
  e.preventDefault();if(submitting||transition)return;transition=true;$('#wizard-next').disabled=true;$('#wizard-error').hidden=true;
  if(step<3){form.inert=true;try{await move(step+1);}catch(error){showError(error);}finally{transition=false;form.inert=false;$('#wizard-next').disabled=false;}return;}
  form.inert=true;
  try{
   if(!await review())return;await save(true);submitting=true;form.inert=true;state(t('draftSubmitting'));
   const result=await api('/drafts/'+key+'/submit',{method:'POST',body:{revision}});
   submitting=false;control.dispose();ctx.wizard=null;toast(t('saved'));history.replaceState(null,'',location.pathname+'#orders');await ctx.render();await showOrder(ctx,result.id);
  }catch(error){submitting=false;form.inert=false;state(t(failed?'draftSaveFailed':'draftSaved'),failed);if(error.field){const match=form.elements.namedItem(error.field);const el=match instanceof RadioNodeList?match[0]:match;if(el instanceof Element){const stage=el.closest('[data-stage]');if(stage)showStep(Number(stage.dataset.stage));fieldError(el,t(error.code));el.focus();}}showError(error);}finally{transition=false;form.inert=false;const next=$('#wizard-next');if(next)next.disabled=false;}
 };
 showStep(step,false);if(step===3){try{await review();}catch(error){showStep(2);showError(error);}}
}
