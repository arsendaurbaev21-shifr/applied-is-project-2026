import {confirmAction,$,$$,esc,t,api,attempt,user,timezone,formData,field,select,area,options,money,dateTime,badge,table,modal,closeModal,toast,printHTML,actionMenu} from './shared.js';
const categories=['contract','invoice','waybill','photo','report','other'];
export async function documents(ctx,keep=false){
 const orders=(await api('/orders')).rows;
 if(!keep||!$('#doc-filter'))$('#content').innerHTML=`<div class="toolbar"><h2>${t('documents')}</h2><div class="right"><button class="light" id="text-document">${t('textDocument')}</button><button class="accent" id="upload-document">+ ${t('upload')}</button></div></div><p class="notice">${t('fileHint')}</p><form class="filters" id="doc-filter">${field('search','search')}${select('Category',`<option value="">${t('all')}</option>`+categories.map(c=>`<option value="${c}">${t(c)}</option>`).join(''))}${select('OrderID',options(orders,'OrderID','OrderNumber','',true))}<button type="submit">${t('filter')}</button></form><div class="panel" id="document-list"></div>`;
 const f=$('#doc-filter');const result=await api('/documents?'+new URLSearchParams(formData(f)));
 $('#document-list').innerHTML=table(result.rows,['Title','OriginalName',{key:'Category',render:r=>esc(t(r.Category))},{key:'FileSize',render:r=>esc((r.FileSize/1024).toFixed(1)+' KB')},'CreatedAt'],r=>actionMenu(`<button data-preview="${r.DocumentID}">${t('preview')}</button><a class="button small light" href="/api/documents/${r.DocumentID}/file">${t('download')}</a>${user.Role==='admin'||r.OwnerUserID===user.UserID?`<button data-delete-doc="${r.DocumentID}">${t('delete')}</button>`:''}`));
 f.onsubmit=e=>{e.preventDefault();attempt(()=>documents(ctx,true),f);};
 const upload=(text=false)=>{const d=modal(t(text?'textDocument':'upload'),`<form id="upload-form"><div class="form-grid">${field('Title','text','','maxlength="160" required')}${select('Category',categories.map(c=>`<option value="${c}">${t(c)}</option>`).join(''))}${select('OrderID',options(orders,'OrderID','OrderNumber','',true))}${text?area('bodyText','',500000):`<label>${t('file')}<input name="file" type="file" accept=".pdf,.txt,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.png,.jpg,.jpeg,.gif,.webp,.bmp" required></label>`}</div><p class="notice" style="margin-top:18px">${t('fileHint')}</p><div class="form-actions"><button type="submit">${t('save')}</button></div></form>`);const form=$('#upload-form',d);form.onsubmit=e=>{e.preventDefault();attempt(async()=>{const data=new FormData(form);if(text){const body=String(data.get('bodyText'));if(!body.trim())throw {code:'file_required'};data.delete('bodyText');data.append('file',new Blob([body],{type:'text/plain'}),'QazCargo.txt');}await api('/documents',{method:'POST',body:data});closeModal();toast(t('saved'));await documents(ctx,true);},form);};};
 $('#upload-document').onclick=()=>upload();$('#text-document').onclick=()=>upload(true);
 $$('[data-delete-doc]').forEach(b=>b.onclick=async()=>{if(await confirmAction(t('confirmDelete')))attempt(async()=>{await api('/documents/'+b.dataset.deleteDoc,{method:'DELETE'});await documents(ctx,true);});});
 $$('[data-preview]').forEach(b=>b.onclick=()=>attempt(()=>previewDocument(Number(b.dataset.preview))));
}
async function previewDocument(id){
 const result=await api(`/documents/${id}/preview`);const d=result.document;let content=result.html;
 if(result.kind==='pdf')content=`<p class="notice">${t('pdfHint')}</p><iframe title="${esc(d.Title)}" src="/api/documents/${id}/file?inline=1"></iframe>`;
 if(result.kind==='image')content=`<img src="/api/documents/${id}/file?inline=1" alt="${esc(d.Title)}">`;
 if(result.kind==='download')content=`<p>${t('officeHint')}</p>`;
 const canPrint=['image','text','docx'].includes(result.kind);
 modal(d.Title,`<div class="toolbar"><a class="button light" href="/api/documents/${id}/file">${t('download')}</a>${canPrint?`<div class="right"><select id="orientation"><option value="portrait">${t('portrait')}</option><option value="landscape">${t('landscape')}</option></select><button id="print-doc">${t('print')}</button></div>`:''}</div>${result.kind==='docx'?`<p class="notice">${t('docxHint')}</p>`:''}<div class="document-preview">${content}</div>`,true);
 $('#print-doc')?.addEventListener('click',()=>printHTML(d.Title,content,$('#orientation').value));
}
export async function reports(ctx){
 const types=user.Role==='admin'?['orders','payments','clients','fleet']:['orders','payments'];
 $('#content').innerHTML=`<div class="panel"><h2>${t('reports')}</h2><form id="report-form" class="filters">${select('reportType',types.map(s=>`<option value="${s}">${t(s)}</option>`).join(''))}${field('from','date')}${field('to','date')}${select('Status',`<option value="">${t('all')}</option>`+['New','Confirmed','InTransit','Delivered','Cancelled'].map(s=>`<option value="${s}">${t(s)}</option>`).join(''))}<button type="submit">${t('buildReport')}</button></form><p class="notice">${t('paymentHint')}</p></div><div id="report-output"><p class="muted">${t('reportStale')}</p></div>`;
 const form=$('#report-form');
 function stale(){const kind=form.reportType.value;form.from.disabled=form.to.disabled=!['orders','payments'].includes(kind);form.Status.disabled=kind!=='orders';$('#report-output').innerHTML=`<p class="muted">${t('reportStale')}</p>`;}
 form.addEventListener('input',stale);form.addEventListener('change',stale);
 form.onsubmit=e=>{e.preventDefault();attempt(async()=>{
  const data=formData(form);const kind=data.reportType;delete data.reportType;if(data.Status!==undefined){data.status=data.Status;delete data.Status;}
  const path=`/reports/${kind}?${new URLSearchParams(data)}`;const result=await api(path);
  const columns={orders:['OrderNumber','ClientName','FromCity','ToCity','OrderDate','Status','QuotedAmount','PaidAmount','BalanceAmount'],payments:['OrderNumber','ClientName','Amount','PaidAt',{key:'Method',render:r=>esc(t(r.Method))},'Note'],clients:['Name','Phone','Email','Address'],fleet:['PlateNumber','Brand','VehicleType','CapacityKg','IsActive']}[kind];
  const summary=`<div class="report-summary"><span>${t('count')}<strong>${result.count}</strong></span>${Object.entries(result.totals).map(([k,v])=>`<span>${t(k)}<strong>${money(v)}</strong></span>`).join('')}</div>`;
  const meta=`${t('generated')}: ${dateTime(result.generated)} · ${timezone} · ${t('filters')}: ${data.from||'—'} / ${data.to||'—'} · ${t(data.status||'all')}`;
  const content=table(result.rows,columns)+summary;
  $('#report-output').innerHTML=`<div class="panel"><div class="toolbar"><h2>${t(kind)}</h2><div class="right"><select id="report-orientation"><option value="landscape">${t('landscape')}</option><option value="portrait">${t('portrait')}</option></select><a class="button light" href="/api${esc(path)}&format=csv">${t('csv')}</a><button id="print-report">${t('print')}</button></div></div><p class="time-note">${esc(meta)}</p>${content}</div>`;
  $('#print-report').onclick=()=>printHTML(t(kind),content,$('#report-orientation').value,meta);
 },form);};
}
