const $ = id => document.getElementById(id);
const libraryRoot = new URL('../library/', import.meta.url);
const siteRoot = new URL('../', import.meta.url);
const cache = new Map(), pasted = new Map(), selected = new Set();
let catalog, original, versions, state, visible = [], request = 0, filterTimer;
const custom = [
  {id:'paste-gae',label:'개역개정 · 직접 붙여넣기',lang:'ko',type:'paste'},
  {id:'paste-new',label:'새번역 · 직접 붙여넣기',lang:'ko',type:'paste'},
  {id:'paste-niv',label:'NIV · 직접 붙여넣기',lang:'en',type:'paste'},
  {id:'paste-other',label:'내 비교본 · 직접 붙여넣기',lang:'und',type:'paste'}
];
const labels = {ko:'한국어',en:'English',es:'Español'};
const node = (tag, text, className) => {const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;};
const version = id => versions.find(v=>v.id===id);
export function safeHTTP(value,base=siteRoot){const u=new URL(value,base);if(!['http:','https:'].includes(u.protocol))throw new Error('Unsupported link scheme');return u;}
const book = () => catalog.books.find(b=>b.id===state.book);
const maximum = () => book().chapters[String(state.chapter)];
const ref = () => `${book().name} ${state.chapter}:${state.from}${state.to===state.from?'':'-'+state.to}`;
const pasteKey = id => `${id}/${state.book}/${state.chapter}`;
function option(select,value,label){const o=node('option',label);o.value=value;select.append(o);}
async function getJSON(path){
  // Share an in-flight request; drop failures so an explicit retry can fetch again.
  if(!cache.has(path))cache.set(path,fetch(new URL(path,libraryRoot),{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}).catch(e=>{cache.delete(path);throw e;}));
  return cache.get(path);
}
function error(message){$('reader-error').hidden=!message;$('reader-error').replaceChildren();if(message){$('reader-error').append(node('span',message+' '));const retry=node('button','다시 불러오기');retry.onclick=()=>catalog?render():location.reload();$('reader-error').append(retry);}}
function query(){
  const p=new URLSearchParams({book:state.book,chapter:state.chapter,from:state.from,to:state.to,left:state.left,right:state.right,mode:state.mode});if(state.hebrew)p.set('hebrew','1');
  const u=new URL(location.href);u.search=p.toString();u.hash='';return u;
}
function updateURL(){history.replaceState(null,'',query());}
function syncControls(){
  $('book').value=state.book;$('chapter').replaceChildren();for(const c of Object.keys(book().chapters))option($('chapter'),c,c+'장');$('chapter').value=state.chapter;
  $('left-version').value=state.left;$('right-version').value=state.right;$('show-hebrew').checked=state.hebrew;
  $('right-label').hidden=state.mode==='read';$('mode-read').setAttribute('aria-pressed',String(state.mode==='read'));$('mode-compare').setAttribute('aria-pressed',String(state.mode==='compare'));
  for(const id of ['from-verse','to-verse']){$(id).max=maximum();} $('from-verse').value=state.from;$('to-verse').value=state.to;
  $('previous').disabled=state.book==='Gen'&&state.chapter===1;$('next').disabled=state.book==='Rev'&&state.chapter===22;
  const ids=[state.left,...(state.mode==='compare'?[state.right]:[])].filter(id=>version(id).type==='paste');
  const old=$('paste-target').value;$('paste-target').replaceChildren();for(const id of new Set(ids))option($('paste-target'),id,version(id).label);
  $('paste-panel').hidden=!ids.length;if(ids.includes(old))$('paste-target').value=old;loadPaste();
  $('copy-source').querySelector('[value=right]').disabled=state.mode==='read';$('copy-source').querySelector('[value=both]').disabled=state.mode==='read';if(state.mode==='read')$('copy-source').value='left';
}
function loadPaste(){const v=$('paste-target').value;$('paste-text').value=v?(pasted.get(pasteKey(v))?.raw||''):'';$('paste-status').textContent='';}
function columns(){return [version(state.left),...(state.mode==='compare'?[version(state.right)]:[]),...(state.hebrew?[{id:'he',label:'히브리어 · WLC 표시문',lang:'he',type:'original'}]:[])];}
async function rowsFor(v){
  if(v.type==='paste')return pasted.get(pasteKey(v.id))?.rows||{};
  if(v.type==='library')return (await getJSON(`${v.id}/${state.book}.json`)).chapters[String(state.chapter)]||{};
  const lang=v.id==='he'?'he':v.lang;return Object.fromEntries(Object.entries(original.records[state.book]?.[state.chapter]||{}).map(([n,r])=>[n,r[lang]]));
}
export function missing(v,value){return value===''?'배포본에 별도 본문 없음':v.type==='library'?'이 배포본에 해당 절 없음':v.type==='paste'?'이 절의 본문을 붙여 넣어 주세요':v.id==='he'?'히브리어 표시문 미공개':'원문성경 미공개';}
async function render(){
  clearTimeout(filterTimer);$('share-status').textContent='';$('share-url').hidden=true;
  const ticket=++request;selected.clear();visible=[];$('copy-status').textContent='';$('verses').replaceChildren();$('copy-preview').value='';$('reader').setAttribute('aria-busy','true');$('copy-text').disabled=true;$('download-text').disabled=true;
  syncControls();updateURL();error('');$('reader-loading').hidden=false;$('reader-loading').textContent='본문을 불러오는 중입니다…';
  try{
    const cols=columns(),data=await Promise.all(cols.map(rowsFor));if(ticket!==request)return;
    $('reference-eyebrow').textContent=`${state.book.toUpperCase()} / ${state.mode==='compare'?'VERSE COMPARISON':'READING'}`;$('chapter-title').textContent=`${book().name} ${state.chapter}장`;
    $('verse-head').style.setProperty('--columns',cols.length);$('verse-head').replaceChildren(node('span','절'),...cols.map(v=>node('span',v.label)));
    const filter=$('chapter-filter').value.trim().toLocaleLowerCase();const fragment=document.createDocumentFragment();
    for(let n=state.from;n<=state.to;n++){
      const values=data.map(d=>d[String(n)]);if(filter&&!values.some(t=>typeof t==='string'&&t.toLocaleLowerCase().includes(filter)))continue;
      visible.push({number:n,cols,values});const row=node('article',undefined,'reading-verse');row.id='verse-'+n;row.style.setProperty('--columns',cols.length);
      const label=node('label',undefined,'verse-number'),check=node('input');check.type='checkbox';check.setAttribute('aria-label',`${n}절 선택`);check.dataset.verse=n;check.addEventListener('change',()=>{check.checked?selected.add(n):selected.delete(n);preview();});label.append(node('span',String(n)),check);row.append(label);
      cols.forEach((v,i)=>{const cell=node('div',undefined,'verse-cell');cell.lang=v.lang;if(v.lang==='he')cell.dir='rtl';cell.append(node('small',v.label));cell.append(node('p',values[i]||missing(v,values[i]),values[i]?'':'missing'));
        const studyPath=original.records[state.book]?.[state.chapter]?.[n]?.study?.[v.lang];
        if(v.id.startsWith('original-')&&values[i]&&studyPath){const a=node('a','번역 근거 · 모델 비교 ↗','study-link');a.href=safeHTTP(studyPath.replace(/^\//,''));cell.append(a);}row.append(cell);});fragment.append(row);
    }
    $('verses').replaceChildren(fragment);$('empty-result').hidden=visible.length>0;
    const originalColumn=cols.some(v=>v.type==='original');const ownCount=Object.keys(original.records[state.book]?.[state.chapter]||{}).length;
    $('reading-notice').textContent=(originalColumn?`원문성경 v${original.version} · 이 장의 공개 범위 ${ownCount}절. AI 보조 연구 초안 · 전문가 검수 전. `:'')+'절 번호 기준 대조입니다. 판본에 따라 절 구분과 본문 계열이 다를 수 있습니다.';
    $('copy-text').disabled=false;$('download-text').disabled=false;preview();
  }catch(e){if(ticket===request){error('본문을 불러오지 못했습니다. 연결을 확인하고 다시 시도해 주세요.');$('selection-count').textContent='본문을 불러오지 못했습니다';}}
  finally{if(ticket===request){$('reader-loading').hidden=true;$('reader').setAttribute('aria-busy','false');}}
}
function changeLocation(b,c,from=1,to=null){state.book=b;state.chapter=c;state.from=from;state.to=to??maximum();$('chapter-filter').value='';render();}
function move(direction){let i=catalog.books.findIndex(b=>b.id===state.book),c=state.chapter+direction;const current=catalog.books[i];if(c<1){i--;if(i<0)return;c=Object.keys(catalog.books[i].chapters).length;}else if(c>Object.keys(current.chapters).length){i++;if(i>=catalog.books.length)return;c=1;}changeLocation(catalog.books[i].id,c);}

// A numbered line starts a verse; subsequent unnumbered lines continue it.
// Fully unnumbered input uses one nonempty line per verse, from the range start.
export function parsePasted(text,start,end){
  const lines=text.split(/\r?\n/).map(s=>s.trim()).filter(Boolean);if(!lines.length)throw new Error('붙여넣을 본문이 없습니다.');
  const pattern=/^(?:\[(\d+)\]\s*|(\d+)[.)]\s*|(\d+)\s+)(.+)$/;
  const numbered=lines.some(s=>pattern.test(s)),rows={};let current=null;
  for(let i=0;i<lines.length;i++){
    const m=lines[i].match(pattern);
    if(numbered&&m){current=Number(m[1]??m[2]??m[3]);if(!Number.isInteger(current)||current<1||current>end)throw new Error(`이 장의 절 번호는 1–${end}입니다.`);if(Object.hasOwn(rows,current))throw new Error(`${current}절 번호가 중복되었습니다.`);rows[current]=m[4];}
    else if(numbered){if(current===null)throw new Error('첫 줄에 절 번호를 적어 주세요.');rows[current]+=' '+lines[i];}
    else{const n=start+i;if(n>end)throw new Error('붙여넣은 줄 수가 이 장의 범위를 넘었습니다.');rows[n]=lines[i];}
  }return rows;
}
export function formatRows(rows,indices,format){
  if(!rows.length)return '';
  if(format==='tsv'){const clean=t=>String(t).replace(/[\t\r\n]+/g,' ');return [['절',...indices.map(i=>rows[0].cols[i].label)].map(clean).join('\t'),...rows.map(r=>[r.number,...indices.map(i=>r.values[i]===undefined||r.values[i]===''?'['+missing(r.cols[i],r.values[i])+']':r.values[i])].map(clean).join('\t'))].join('\n');}
  return indices.map(i=>{const lines=rows.filter(r=>r.values[i]).map(r=>(format==='numbered'?r.number+' ':'')+r.values[i]);return lines.length?(indices.length>1?rows[0].cols[i].label+'\n':'')+lines.join('\n'):'';}).filter(Boolean).join('\n\n');
}
function preview(){
  $('copy-status').textContent='';$('quick-status').textContent='';
  const rows=selected.size?visible.filter(r=>selected.has(r.number)):visible;
  $('selection-count').textContent=selected.size?`${selected.size}절 선택 · 선택한 절만 복사`:`선택 없음 · 표시된 ${visible.length}절 범위 복사`;
  if(!rows.length){$('copy-preview').value='';return;}
  const source=$('copy-source').value,indices=source==='left'?[0]:source==='right'?[1]:[0,...(state.mode==='compare'?[1]:[])];
  let text=formatRows(rows,indices,$('copy-format').value);if(text&&$('copy-credit').checked){
    const nums=rows.map(r=>r.number),coverage=`선택 범위: ${book().name} ${state.chapter}:${nums.join(',')}`;
    const credits=indices.map(i=>{const v=rows[0].cols[i],available=rows.filter(r=>r.values[i]).map(r=>r.number).join(','),scope=`복사 가능한 본문 절: ${available||'없음'}`;if(v.type==='library')return `${v.label} · ${scope} · ${v.rights}\n${v.rights_url}`;if(v.type==='paste')return `${v.label} · ${scope} · 사용자 제공 본문, 원권리자 권리 유지`;return `${v.label} v${original.version} · ${scope} · Hansam Yang · AI 보조 연구 초안 / 전문가 검수 전 · CC BY 4.0\n${new URL('reuse/',siteRoot)}`;});
    text+='\n\n'+coverage+'\n'+credits.join('\n');
  }$('copy-preview').value=text;
}
async function copy(text,status,field){
  if(!text){$(status).textContent='복사할 본문이 없습니다.';return;}
  try{await navigator.clipboard.writeText(text);$(status).textContent='복사했습니다.';}
  catch(e){if(field){$(field).value=text;$(field).hidden=false;$(field).focus();$(field).select();$(status).textContent='자동 복사가 제한되었습니다. 선택된 내용을 Ctrl+C 또는 길게 눌러 복사하세요.';}else{$(status).textContent='클립보드에 복사하지 못했습니다. 본문을 직접 선택해 복사하세요.';}}
}
function wire(){
  $('book').onchange=()=>changeLocation($('book').value,1);$('chapter').onchange=()=>changeLocation(state.book,Number($('chapter').value));$('previous').onclick=()=>move(-1);$('next').onclick=()=>move(1);
  for(const side of ['left','right'])$(side+'-version').onchange=()=>{state[side]=$(side+'-version').value;render();};
  for(const mode of ['read','compare'])$('mode-'+mode).onclick=()=>{state.mode=mode;render();};
  $('show-hebrew').onchange=()=>{state.hebrew=$('show-hebrew').checked;render();};
  const range=()=>{const a=Number($('from-verse').value),b=Number($('to-verse').value);if(!Number.isInteger(a)||!Number.isInteger(b)||a<1||b<a||b>maximum()){error(`절 범위는 1–${maximum()} 안에서 시작 절 ≤ 끝 절로 입력해 주세요.`);return;}state.from=a;state.to=b;render();};
  $('apply-range').onclick=range;for(const id of ['from-verse','to-verse'])$(id).onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();range();}};$('whole-chapter').onclick=()=>{state.from=1;state.to=maximum();render();};
  $('chapter-filter').oninput=()=>{clearTimeout(filterTimer);filterTimer=setTimeout(render,120);};
  $('select-visible').onclick=()=>{visible.forEach(r=>selected.add(r.number));$('verses').querySelectorAll('input').forEach(n=>n.checked=true);preview();};
  $('clear-selection').onclick=()=>{selected.clear();$('verses').querySelectorAll('input').forEach(n=>n.checked=false);preview();};
  for(const id of ['copy-source','copy-format','copy-credit'])$(id).onchange=()=>{$('copy-status').textContent='';preview();};
  $('copy-text').onclick=()=>copy($('copy-preview').value,'copy-status','copy-preview');
  $('copy-quick').onclick=()=>copy($('copy-preview').value,'quick-status','copy-preview');
  $('share-link').onclick=()=>copy(query().href,'share-status','share-url');
  $('download-text').onclick=()=>{const text=$('copy-preview').value;if(!text){$('copy-status').textContent='내려받을 본문이 없습니다.';return;}const url=URL.createObjectURL(new Blob(['\ufeff'+text],{type:'text/plain;charset=utf-8'})),a=node('a');a.href=url;a.download=`${state.book}-${state.chapter}-${state.from}-${state.to}.txt`;a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);$('copy-status').textContent='텍스트 파일을 준비했습니다.';};
  $('paste-target').onchange=loadPaste;
  $('apply-paste').onclick=async()=>{try{const raw=$('paste-text').value,rows=parsePasted(raw,state.from,maximum()),key=pasteKey($('paste-target').value);pasted.set(key,{raw,rows});await render();$('paste-status').textContent=`${Object.keys(rows).length}절을 이번 장에 적용했습니다.`;}catch(e){$('paste-status').textContent=e.message;}};
  $('clear-paste').onclick=()=>{pasted.delete(pasteKey($('paste-target').value));render();};
  $('reference-form').onsubmit=e=>{e.preventDefault();const input=$('reference').value.trim(),m=input.match(/^(.+?)\s*(\d+)\s*(?:[:：]\s*(\d+)(?:\s*[-–]\s*(\d+))?)?$/),normalize=s=>s.toLowerCase().replace(/[\s.]/g,'');
    const b=m&&catalog.books.find(b=>[b.id,b.name,b.abbr,b.english].some(s=>normalize(s)===normalize(m[1])));const c=m?Number(m[2]):0,max=b?.chapters[c],a=m&&m[3]?Number(m[3]):1,z=m&&m[4]?Number(m[4]):m&&m[3]?a:max;
    if(!b||!max||a<1||z<a||z>max){$('reference-status').textContent='책·장·절을 확인해 주세요. 예: 창 1:1-5, 요 3:16';return;}$('reference-status').textContent='';changeLocation(b.id,c,a,z);};
}
async function init(){
  try{
    [catalog,original]=await Promise.all([getJSON('catalog.json'),getJSON('original.json')]);
    versions=[...Object.entries(labels).map(([lang,label])=>({id:'original-'+lang,label:'원문성경 · '+label,lang,type:'original'})),...catalog.versions,...custom];
    for(const b of catalog.books)option($('book'),b.id,`${b.testament==='OT'?'구약':'신약'} · ${b.name}`);
    for(const id of ['left-version','right-version'])for(const v of versions)option($(id),v.id,v.label);
    const q=new URLSearchParams(location.search),b=catalog.books.find(b=>b.id===q.get('book'))||catalog.books[0],c=Number(q.get('chapter'))||1,ch=Object.hasOwn(b.chapters,c)?c:1,max=b.chapters[ch],a=Math.max(1,Math.min(max,Number(q.get('from'))||1)),z=Math.max(a,Math.min(max,Number(q.get('to'))||max));
    state={book:b.id,chapter:ch,from:Math.floor(a),to:Math.floor(z),left:version(q.get('left'))?q.get('left'):'original-ko',right:version(q.get('right'))?q.get('right'):'krv',mode:q.get('mode')==='read'?'read':'compare',hebrew:q.get('hebrew')==='1'};
    for(const v of catalog.versions){const p=node('p');p.append(node('strong',v.label),' — '+v.upstream_title+' · Public Domain · ');const a=node('a','배포처·권리 표기 ↗');a.href=safeHTTP(v.rights_url);p.append(a);$('source-list').append(p);}
    wire();$('reader-controls').hidden=false;await render();
  }catch(e){$('reader-loading').hidden=true;$('reader').setAttribute('aria-busy','false');error('성경 목록을 불러오지 못했습니다. 연결을 확인하고 다시 시도해 주세요.');}
}
if(typeof document!=='undefined')init();
