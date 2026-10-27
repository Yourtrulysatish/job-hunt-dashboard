(function(){
'use strict';
var STAT=[['to_apply','To apply','--s0'],['applied','Applied','--s1'],['replied','Replied','--s2'],['interview','Interview','--s3'],['offer','Offer','--s4'],['rejected','Rejected','--s5'],['skipped','Skipped','--s6']];
var LABEL={},VAR={};STAT.forEach(function(s){LABEL[s[0]]=s[1];VAR[s[0]]=s[2]});
var TIER={apply:'Apply now',stretch:'Stretch',lead:'Lead'};
var KEY='jobhunt-track-v1';
var jobs=[],track={},meta={},scan=null,loaded=false,dirty=false,scanRegion='all';
var ui={status:'active',region:'all',tier:'all',country:'all',q:'',sort:'fit',open:{}};
var R={};var app=document.getElementById('app');

try{track=JSON.parse(localStorage.getItem(KEY)||'{}')||{}}catch(e){track={}}
function persist(){try{localStorage.setItem(KEY,JSON.stringify(track))}catch(e){note('This browser would not save your changes. Use Backup to keep a copy.')}}

function h(tag,attrs){
  var e=document.createElement(tag),post=null,i,k,v;
  if(attrs){for(k in attrs){v=attrs[k];if(v==null||v===false)continue;
    if(k==='class')e.className=v;else if(k==='text')e.textContent=v;
    else if(k==='value')post=v;else if(k.slice(0,2)==='on')e.addEventListener(k.slice(2),v);
    else e.setAttribute(k,v===true?'':v)}}
  for(i=2;i<arguments.length;i++){add(e,arguments[i])}
  if(post!=null)e.value=post;return e}
function add(e,c){if(c==null||c===false)return;if(Array.isArray(c)){c.forEach(function(x){add(e,x)});return}
  e.appendChild(typeof c==='string'?document.createTextNode(c):c)}
function clear(e){while(e.firstChild)e.removeChild(e.firstChild)}

var T0=new Date();T0.setHours(0,0,0,0);
function dd(iso){if(!iso||typeof iso!=='string')return null;var p=iso.slice(0,10).split('-');if(p.length<3)return null;var d=new Date(+p[0],+p[1]-1,+p[2]);return isNaN(d)?null:d}
function until(iso){var d=dd(iso);return d?Math.round((d-T0)/864e5):null}
function fmt(iso){var d=dd(iso);return d?d.toLocaleDateString('en-GB',{day:'numeric',month:'short'}):''}
function todayIso(){var d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
function rel(n){return n===0?'today':n===1?'tomorrow':n===-1?'yesterday':n>0?'in '+n+' days':(-n)+' days ago'}
function st(j){var t=track[j.id];return (t&&t.status)||'to_apply'}
function activeStatus(s){return s!=='skipped'&&s!=='rejected'}

function build(){
  clear(app);
  R.banner=h('p',{class:'banner',hidden:true});
  R.meta=h('p',{class:'sub'});
  app.appendChild(h('div',{class:'top'},h('div',null,h('h1',{text:'Job hunt dashboard'}),R.meta),
    h('div',{class:'bk'},
      h('button',{class:'btn ghost',type:'button',onclick:exportCsv},'Export CSV'),
      h('button',{class:'btn ghost',type:'button',onclick:backup},'Backup'),
      h('button',{class:'btn ghost',type:'button',onclick:function(){R.file.click()}},'Restore'),
      R.file=h('input',{type:'file',accept:'application/json',hidden:true,onchange:restore}))));
  app.appendChild(R.banner);
  R.tiles=h('div',{class:'tiles',role:'group','aria-label':'Filter by stage'});app.appendChild(R.tiles);
  R.att=h('ul',{class:'att'});R.bars=h('div',{class:'bars'});
  app.appendChild(h('div',{class:'panels'},
    h('section',{class:'panel'},h('h2',{text:'Needs attention'}),R.att),
    h('section',{class:'panel'},h('h2',{text:'Where the roles are'}),R.bars)));
  R.q=h('input',{type:'search',placeholder:'Search title, company, city or notes','aria-label':'Search',oninput:function(){ui.q=R.q.value;render(true)}});
  R.reg=sel('Region',[['all','All regions'],['n','Northern Europe'],['r','Remote']],'region');
  R.tier=sel('Tier',[['all','All tiers'],['apply','Apply now'],['stretch','Stretch']],'tier');
  R.stat=sel('Status',[['active','Open, not skipped'],['all','Everything']].concat(STAT.map(function(s){return [s[0],s[1]]})),'status');
  R.country=sel('Country',[['all','All countries']],'country');
  R.sort=sel('Sort',[['fit','Best fit first'],['posted','Newest first'],['closes','Closing soonest'],['company','Company A to Z']],'sort');
  R.count=h('span',{class:'count'});
  app.appendChild(h('div',{class:'tool'},R.q,R.reg,R.tier,R.stat,R.country,R.sort,R.count));
  R.list=h('div',{class:'list'});app.appendChild(R.list);
  R.list.addEventListener('focusout',function(){setTimeout(function(){if(dirty&&!editing()){dirty=false;render(true)}},0)});
  R.scanHead=h('div',{class:'scanhead'});R.scan=h('ul',{class:'scan'});
  app.appendChild(h('section',{class:'panel'},R.scanHead,R.scan));
  app.appendChild(h('p',{class:'foot',text:'Statuses and notes are saved in this browser only, nothing is sent anywhere. Use Backup and Restore to move them to another device. The roles above were read posting by posting; the daily scan list below was not.'}));
}
function sel(label,opts,key){
  var s=h('select',{'aria-label':label,onchange:function(){ui[key]=s.value;render(true)}});
  opts.forEach(function(o){s.appendChild(h('option',{value:o[0],text:o[1]}))});s.value=ui[key];return s}
function setOptions(s,opts,key){
  var cur=ui[key];clear(s);opts.forEach(function(o){s.appendChild(h('option',{value:o[0],text:o[1]}))});
  if(!opts.some(function(o){return o[0]===cur})){ui[key]='all'}s.value=ui[key]}
function editing(){var a=document.activeElement;return !!(a&&R.list&&R.list.contains(a)&&(a.tagName==='TEXTAREA'||a.tagName==='INPUT'))}

function visible(){
  var q=ui.q.trim().toLowerCase();
  var list=jobs.filter(function(j){
    var s=st(j);
    if(ui.status==='active'){if(!activeStatus(s))return false}else if(ui.status!=='all'&&s!==ui.status)return false;
    if(ui.region!=='all'&&j.region!==ui.region)return false;
    if(ui.tier!=='all'&&j.tier!==ui.tier)return false;
    if(ui.country!=='all'&&j.country!==ui.country)return false;
    if(q){var hay=[j.title,j.company,j.country,j.city,(track[j.id]||{}).notes].join(' ').toLowerCase();if(hay.indexOf(q)<0)return false}
    return true});
  var by={
    fit:function(a,b){return (b.fit||0)-(a.fit||0)||String(b.posted||'').localeCompare(String(a.posted||''))},
    posted:function(a,b){return String(b.posted||'').localeCompare(String(a.posted||''))},
    closes:function(a,b){return String(a.closes||'9999').localeCompare(String(b.closes||'9999'))},
    company:function(a,b){return String(a.company).localeCompare(String(b.company))}};
  return list.sort(by[ui.sort]||by.fit)}

function render(force){
  if(!R.list)return;
  if(!force&&editing()){dirty=true;return}
  var a=document.activeElement,fk=a&&a.getAttribute&&a.getAttribute('data-fk');
  R.meta.textContent='Northern Europe and remote roles'+(meta.updated?'. Roles last checked by hand '+meta.updated:'')+(scan&&scan.generated?'. Daily scan '+scan.generated:'')+'.';
  var counts={};STAT.forEach(function(s){counts[s[0]]=0});jobs.forEach(function(j){counts[st(j)]++});
  clear(R.tiles);
  STAT.forEach(function(s){
    R.tiles.appendChild(h('button',{type:'button',class:'tile',style:'--c:var('+s[2]+')','aria-pressed':String(ui.status===s[0]),
      onclick:function(){ui.status=(ui.status===s[0])?'active':s[0];R.stat.value=ui.status;render(true)}},
      h('b',{text:String(counts[s[0]])}),h('span',{text:s[1]})))});
  var items=[];
  jobs.forEach(function(j){
    var s=st(j),t=track[j.id]||{};if(!activeStatus(s)||s==='offer')return;
    var c=until(j.closes);
    if(s==='to_apply'&&c!=null&&c>=0&&c<=10)items.push({d:c,j:j,txt:'Closes '+fmt(j.closes)+'. Apply: '+j.title+', '+j.company});
    var n=until(t.nextDate);
    if(n!=null&&n<=7)items.push({d:n,j:j,txt:(t.nextStep||'Next step')+': '+j.title+', '+j.company});
    else if(s==='applied'&&t.appliedOn&&!t.nextDate){var ago=-until(t.appliedOn);if(ago>=7)items.push({d:-ago+7,j:j,txt:'Applied '+ago+' days ago, no reply yet. Follow up: '+j.title+', '+j.company})}
  });
  items.sort(function(x,y){return x.d-y.d});
  clear(R.att);
  if(!items.length){R.att.appendChild(h('li',null,h('p',{class:'empty',text:loaded?'Nothing due. Deadlines, next steps and follow ups will show here.':'Loading...'})))}
  items.slice(0,8).forEach(function(it){
    R.att.appendChild(h('li',null,h('span',{class:'when '+(it.d<0?'late':it.d<=2?'soon':''),text:it.d<0?(-it.d)+'d late':it.d===0?'today':'in '+it.d+'d'}),
      h('button',{type:'button',onclick:function(){jump(it.j.id)},text:it.txt})))});
  var cc={};jobs.forEach(function(j){if(activeStatus(st(j)))cc[j.country]=(cc[j.country]||0)+1});
  var names=Object.keys(cc).sort(function(x,y){return cc[y]-cc[x]||x.localeCompare(y)}),max=names.length?cc[names[0]]:1;
  clear(R.bars);
  names.forEach(function(n){R.bars.appendChild(h('button',{type:'button',class:'bar','aria-pressed':String(ui.country===n),onclick:function(){ui.country=(ui.country===n)?'all':n;R.country.value=ui.country;render(true)}},
    h('span',{text:n}),h('div',null,h('i',{style:'width:'+Math.max(4,Math.round(100*cc[n]/max))+'%'})),h('em',{text:String(cc[n])})))});
  if(!names.length)R.bars.appendChild(h('p',{class:'empty',text:'No open roles yet.'}));
  var allC=Object.keys(jobs.reduce(function(o,j){o[j.country]=1;return o},{})).sort();
  setOptions(R.country,[['all','All countries']].concat(allC.map(function(c){return [c,c]})),'country');
  var vis=visible();R.count.textContent=vis.length+' of '+jobs.length+' shown';
  clear(R.list);
  if(!loaded)R.list.appendChild(h('p',{class:'loading',text:'Loading jobs...'}));
  else if(!jobs.length)R.list.appendChild(h('p',{class:'empty',text:'The job list did not load. Reload the page.'}));
  else if(!vis.length)R.list.appendChild(h('p',{class:'empty',text:'No role matches these filters.'}));
  vis.forEach(function(j){R.list.appendChild(card(j))});
  renderScan();
  if(fk){var again=app.querySelector('[data-fk="'+fk+'"]');if(again&&again!==document.activeElement)again.focus()}
}

function renderScan(){
  clear(R.scanHead);clear(R.scan);
  R.scanHead.appendChild(h('h2',{text:'New from the daily scan'}));
  if(!scan||!scan.items){R.scan.appendChild(h('li',null,h('p',{class:'empty',text:'No scan data yet.'})));return}
  var chips=h('div',{class:'bk'},[['all','All'],['n','Northern Europe'],['r','Remote']].map(function(o){
    return h('button',{type:'button',class:'mini','aria-pressed':String(scanRegion===o[0]),style:scanRegion===o[0]?'background:var(--accent);color:var(--accent-ink)':'',onclick:function(){scanRegion=o[0];renderScan()}},o[1])}));
  R.scanHead.appendChild(chips);
  var list=scan.items.filter(function(x){return scanRegion==='all'||(scanRegion==='n')===!!x.north});
  if(!list.length){R.scan.appendChild(h('li',null,h('p',{class:'empty',text:'Nothing in this view.'})));return}
  list.slice(0,60).forEach(function(x){
    R.scan.appendChild(h('li',null,
      h('span',{class:'d',text:fmt(x.date)}),
      h('div',null,h('a',{href:x.url,target:'_blank',rel:'noopener',text:x.title}),' ',h('span',{class:'fl',text:x.company+(x.loc?', '+x.loc:'')}),
        x.flags&&x.flags.length?h('div',{class:'fl',text:x.flags.join(', ')}):null),
      h('span',{class:'chip '+(x.north?'n':'r'),text:x.north?'Northern Europe':'Remote'})))});
}

function card(j){
  var s=st(j),t=track[j.id]||{},open=!!ui.open[j.id];
  var cl=until(j.closes),age=j.posted?-until(j.posted):null;
  var fit=j.fit?h('div',{class:'fit '+(j.fit>=8?'hi':j.fit>=6?'mid':''),'aria-label':'Fit '+j.fit+' out of 10'},h('b',{text:String(j.fit)}),h('span',{text:'/10'})):null;
  var where=[j.city,j.country].filter(Boolean).join(', ');
  var chips=h('div',{class:'chips'},
    h('span',{class:'chip '+(j.region==='r'?'r':'n'),text:j.region==='r'?'Remote':'Northern Europe'}),
    h('span',{class:'chip',text:TIER[j.tier]||'Role'}),
    j.mode?h('span',{class:'chip',text:j.mode}):null,
    j.visaState==='none'?h('span',{class:'chip bad',text:'No visa support'}):null);
  var dates=[];
  if(j.posted)dates.push('Posted '+fmt(j.posted)+(age!=null?' ('+age+' days)':''));
  if(j.closes)dates.push('Closes '+fmt(j.closes)+' ('+rel(cl)+')');
  var statusSel=h('select',{class:'stsel',style:'--c:var('+VAR[s]+')','aria-label':'Status of '+j.title,'data-fk':j.id+'-status',
    onchange:function(e){var v=e.target.value,p={status:v};if(v==='applied'&&!t.appliedOn)p.appliedOn=todayIso();save(j.id,p)}},
    STAT.map(function(x){return h('option',{value:x[0],text:x[1]})}));statusSel.value=s;
  var fields=h('div',{class:'fields'},
    fld('Applied on','date',t.appliedOn,'appliedOn',j),
    fld('Next step date','date',t.nextDate,'nextDate',j),
    fld('Next step','text',t.nextStep,'nextStep',j,true),
    fld('Contact','text',t.contact,'contact',j,true),
    fld('Notes','area',t.notes,'notes',j,true));
  var facts=h('dl',{class:'facts'},
    j.exp?h('div',null,h('dt',{text:'Asks for'}),h('dd',{text:j.exp})):null,
    j.lang?h('div',null,h('dt',{text:'Language'}),h('dd',{text:j.lang})):null,
    j.visa?h('div',null,h('dt',{text:'Visa'}),h('dd',{text:j.visa})):null,
    j.pay?h('div',null,h('dt',{text:'Pay'}),h('dd',{text:j.pay})):null,
    j.source?h('div',null,h('dt',{text:'Found on'}),h('dd',{text:j.source})):null);
  var mail=j.email?h('div',null,h('span',{text:'Apply by email: '}),h('code',{text:j.email}),' ',h('button',{type:'button',class:'mini',onclick:function(e){copy(e.target,j.email)}},'Copy'),j.emailNote?h('div',{class:'co',text:j.emailNote}):null):null;
  return h('article',{class:'card st-'+s,id:'job-'+j.id},
    h('div',{class:'chead'},fit,h('div',null,h('h3',{text:j.title}),h('p',{class:'co',text:j.company+(where?', '+where:'')}))),
    chips,
    dates.length?h('p',{class:'co',text:dates.join('. ')}):null,
    j.why||j.flag?h('p',{class:'why',text:j.why||j.flag}):null,
    h('div',{class:'row2'},statusSel,
      h('span',null,j.url?h('a',{class:'btn',href:j.url,target:'_blank',rel:'noopener',text:'Open posting'}):null)),
    h('button',{type:'button',class:'tog','aria-expanded':String(open),'data-fk':j.id+'-tog',onclick:function(){ui.open[j.id]=!open;render(true)}},open?'Hide details':'Details and notes'),
    open?h('div',{class:'det'},facts,mail,fields):null)}
function fld(label,type,val,key,j,wide){
  var inp=type==='area'?h('textarea',{value:val||''}):h('input',{type:type,value:val||''});
  inp.addEventListener('change',function(){var p={};p[key]=inp.value;save(j.id,p)});
  return h('label',{class:wide?'wide':null},label,inp)}

function save(id,patch){
  var cur=Object.assign({},track[id]||{},patch,{updatedAt:new Date().toISOString()});
  Object.keys(cur).forEach(function(k){if(cur[k]===undefined)delete cur[k]});
  track[id]=cur;persist();render(true)}
function note(t){R.banner.hidden=!t;R.banner.textContent=t||''}
function jump(id){
  ui.status='all';ui.region='all';ui.tier='all';ui.country='all';ui.q='';
  R.stat.value='all';R.reg.value='all';R.tier.value='all';R.q.value='';ui.open[id]=true;render(true);
  var el=document.getElementById('job-'+id);if(el){el.scrollIntoView({behavior:'smooth',block:'center'})}}
function copy(btn,text){
  try{navigator.clipboard.writeText(text).then(function(){btn.textContent='Copied'},function(){btn.textContent='Select the address'})}catch(e){btn.textContent='Select the address'}}
function saveFile(name,text,type){
  var b=new Blob([text],{type:type}),u=URL.createObjectURL(b),a=document.createElement('a');
  a.href=u;a.download=name;document.body.appendChild(a);a.click();document.body.removeChild(a);setTimeout(function(){URL.revokeObjectURL(u)},1000)}
function csvCell(v){v=v==null?'':String(v);return /[",\n]/.test(v)?'"'+v.replace(/"/g,'""')+'"':v}
function exportCsv(){
  var cols=[['Company','company'],['Title','title'],['Country','country'],['City','city'],['Mode','mode'],['Tier','tier'],['Fit','fit'],['Posted','posted'],['Closes','closes'],['URL','url']];
  var tc=[['Status','status'],['Applied on','appliedOn'],['Next step','nextStep'],['Next step date','nextDate'],['Contact','contact'],['Notes','notes']];
  var rows=[cols.map(function(c){return c[0]}).concat(tc.map(function(c){return c[0]}))];
  jobs.forEach(function(j){var t=track[j.id]||{};rows.push(cols.map(function(c){return j[c[1]]}).concat(tc.map(function(c){return c[1]==='status'?LABEL[st(j)]:t[c[1]]})))});
  saveFile('job-hunt-'+todayIso()+'.csv',rows.map(function(r){return r.map(csvCell).join(',')}).join('\n'),'text/csv')}
function backup(){saveFile('job-hunt-backup-'+todayIso()+'.json',JSON.stringify({version:1,track:track},null,1),'application/json')}
function restore(){
  var f=R.file.files&&R.file.files[0];if(!f)return;
  var r=new FileReader();r.onload=function(){
    try{var d=JSON.parse(r.result);if(!d||typeof d.track!=='object')throw 0;track=d.track;persist();render(true);note('Backup restored.')}
    catch(e){note('That file is not a backup from this dashboard.')}
    R.file.value=''};
  r.readAsText(f)}

function getJson(u){return fetch(u,{cache:'no-cache'}).then(function(r){if(!r.ok)throw new Error(r.status);return r.json()})}
build();render(true);
getJson('data/jobs.json').then(function(d){jobs=d.jobs||[];meta=d;loaded=true;render(true)}).catch(function(){loaded=true;render(true)});
getJson('data/scan.json').then(function(d){scan=d;render()}).catch(function(){});
})();
