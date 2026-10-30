// Optional development check. Node.js is not required to run the website.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const web=path.join(root,'web');
globalThis.localStorage={getItem(){return 'kk';}};
const {translations}=await import('data:text/javascript;base64,'+fs.readFileSync(path.join(web,'i18n.js')).toString('base64'));
const missing=new Set();
let count=0;
for(const filename of fs.readdirSync(web)){
  if(!/\.(js|html)$/.test(filename))continue;
  const text=fs.readFileSync(path.join(web,filename),{encoding:'utf8',flag:'r'});
  if(filename.endsWith('.js')){
    const result=spawnSync(process.execPath,['--check',path.join(web,filename)],{encoding:'utf8'});
    if(result.status!==0)throw new Error(result.stderr);
    count++;
  }
  if(!/\.(js|html)$/.test(filename))continue;
  for(const match of text.matchAll(/\bt\('([^']+)'\)|data-t="([^"]+)"/g)){
    const key=match[1]||match[2];
    if(!translations[key])missing.add(key);
  }
}
for(const [key,values] of Object.entries(translations)){
  if(values.length!==3||values.some(value=>typeof value!=='string'||!value.trim()))throw new Error('Incomplete translation: '+key);
}
if(missing.size)throw new Error('Missing literal translations: '+[...missing].join(', '));
console.log(`PASS: ${count} JavaScript modules parse; ${Object.keys(translations).length} keys have KK/RU/EN values; referenced literal keys exist.`);
