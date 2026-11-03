const {chromium}=require('playwright');const http=require('http');const fs=require('fs');const path=require('path');
const [,, model, outdir, presets] = process.argv;
const srv=http.createServer((q,r)=>{const u=decodeURIComponent(q.url.split('?')[0]);const f=path.join(__dirname,u==='/'?'sprite.html':u);fs.readFile(f,(e,d)=>{if(e){r.writeHead(404);r.end();return}r.writeHead(200,{'Content-Type':f.endsWith('.js')?'text/javascript':f.endsWith('.html')?'text/html':'application/octet-stream'});r.end(d)})}).listen(8766,async()=>{
 const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});const p=await b.newPage();
 p.on('console',m=>console.log('console:',m.text()));
 await p.goto('http://localhost:8766/?m='+model+(presets?'&p='+presets:'')+(process.argv[5]?'&toon='+process.argv[5]:'')+(process.argv[6]?'&hs='+process.argv[6]:''));await p.waitForFunction('window.done',null,{timeout:180000});
 const err=await p.evaluate('window.err');if(err)console.log('ERR',err);
 const s=await p.evaluate('window.shots');fs.mkdirSync(outdir,{recursive:true});for(const k in s)fs.writeFileSync(path.join(outdir,k+'.png'),Buffer.from(s[k].split(',')[1],'base64'));
 console.log('shots',Object.keys(s).join(','));await b.close();srv.close();});
