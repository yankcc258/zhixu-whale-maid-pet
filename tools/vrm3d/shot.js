const {chromium}=require('playwright');const http=require('http');const fs=require('fs');const path=require('path');
const srv=http.createServer((q,r)=>{const f=path.join(__dirname,decodeURIComponent(q.url.split('?')[0])==='/'?'index.html':decodeURIComponent(q.url.split('?')[0]));fs.readFile(f,(e,d)=>{if(e){r.writeHead(404);r.end();return}r.writeHead(200,{'Content-Type':f.endsWith('.js')?'text/javascript':f.endsWith('.html')?'text/html':'application/octet-stream'});r.end(d)})}).listen(8765,async()=>{
 const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const p=await b.newPage();
 p.on('console',m=>console.log('console:',m.text()));
 await p.goto('http://localhost:8765/?m='+process.argv[2]+'&s='+(process.argv[4]||'mtoon')+(process.argv[5]?'&face=1':''));await p.waitForFunction('window.done',null,{timeout:120000});
 const err=await p.evaluate('window.err');if(err)console.log('ERR',err);
 const s=await p.evaluate('window.shots');for(const k in s)fs.writeFileSync(process.argv[3]+'_'+k+'.png',Buffer.from(s[k].split(',')[1],'base64'));
 await b.close();srv.close();});
