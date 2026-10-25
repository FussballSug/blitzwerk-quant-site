const fallback={schema_version:1,snapshot_at:null,freshness:"unverified",mode:"simulation validation",desk_state:"status unavailable",traders:[{name:"Maximilian Braun",strategy:"Trend",symbol:"F",state:"research"},{name:"Felix Hartmann",strategy:"Momentum",symbol:"BAC",state:"research"},{name:"Tobias Krüger",strategy:"Mean reversion",symbol:"SOFI",state:"research"}],stages:[{name:"Research",state:"active"},{name:"Independent validation",state:"required"},{name:"Deterministic risk",state:"enforced"},{name:"Broker simulation",state:"gated"}]};
const $=id=>document.getElementById(id);const escape=value=>{const n=document.createElement("span");n.textContent=String(value);return n.innerHTML};
function render(data){
  $("desk-state").textContent=data.desk_state;$("system-state").textContent=`${data.mode} · ${data.freshness}`;
  $("system-state").parentElement.querySelector("i").style.background=data.freshness==="current"?"var(--acid)":"var(--orange)";
  $("snapshot-time").textContent=data.snapshot_at?new Date(data.snapshot_at).toLocaleString("en-US",{timeZone:"America/Chicago",month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})+" CT":"UNVERIFIED";
  $("freshness").textContent=data.freshness.toUpperCase();$("freshness").className=data.freshness==="current"?"current":"warning";
  $("process-rail").innerHTML=data.stages.map((s,i)=>`<article class="stage"><span class="stage-index">0${i+1}</span><span class="stage-state">${escape(s.state)}</span><h3>${escape(s.name)}</h3><p>${["Hypotheses move through reproducible evidence.","Independent checks challenge every candidate.","Hard limits gate progression without model discretion.","Bounded experiments remain in broker simulation."][i]||"Verified workflow stage."}</p><div class="flow"></div></article>`).join("");
  $("traders").innerHTML=data.traders.map((t,i)=>`<article class="trader"><span class="number">DESK / 0${i+1}</span><span class="symbol">${escape(t.symbol)}</span><h3>${escape(t.name)}</h3><span class="strategy">${escape(t.strategy).toUpperCase()}</span><div class="activity"><span>${escape(t.state)}</span><i></i></div></article>`).join("");
}
async function load(){if(window.BLITZWERK_DATA){render(window.BLITZWERK_DATA);return}for(const url of ["/api/public-status","snapshot.json"]){try{const r=await fetch(url,{cache:"no-store"});if(r.ok){render(await r.json());return}}catch{}}render(fallback)}
setInterval(()=>{$("clock").textContent=new Intl.DateTimeFormat("en-US",{timeZone:"America/Chicago",hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:false}).format(new Date())+" CT"},1000);load();

const pageSections=[...document.querySelectorAll("main > section")];
function showPage(hash){
 const id=hash.replace("#","");
 const overview=id==="home"||id==="operations"||!id;
 pageSections.forEach(section=>section.hidden=!overview&&section.id!==id);
 document.body.classList.toggle("page-view",!overview);
 document.querySelectorAll("nav a").forEach(link=>link.classList.toggle("active",link.getAttribute("href")===`#${id}`));
 window.scrollTo({top:0,behavior:"instant"});
}
document.querySelectorAll('a[href^="#"]').forEach(link=>link.addEventListener("click",event=>{
 event.preventDefault();
 showPage(link.getAttribute("href"));
}));
showPage(`#${document.body.dataset.page||"home"}`);

const employees=[
 {name:"Alexander von Stein",title:"EVP / COO · AI Innovation",department:"Executive",code:"EX-01",summary:"Coordinates verified work, owner briefings, decisions, and cross-team handoffs.",state:"Coordinator defined"},
 {name:"Klaus Reinhardt",title:"Chief Investment Officer",department:"Executive",code:"EX-02",summary:"Frames portfolio research priorities and compares strategy evidence without overriding risk controls.",state:"Role defined"},
 {name:"Matthias Vogel",title:"Chief Financial Officer",department:"Operations",code:"OP-01",summary:"Owns sanitized accounting, reconciliation evidence, expenses, and measured paper results.",state:"Workflow partial"},
 {name:"Friedrich Weber",title:"Chief Risk Officer",department:"Risk",code:"RK-01",summary:"Maintains independent veto authority and reviews deterministic exposure, loss, and halt controls.",state:"Controls implemented"},
 {name:"Stefan Hoffmann",title:"Chief Technology Officer",department:"Operations",code:"OP-02",summary:"Owns reliability, secure releases, monitoring, recovery, and technical incident handling.",state:"Workflow implemented"},
 {name:"Dr. Lukas Fischer",title:"Quantitative Research",department:"Research",code:"RS-01",summary:"Develops reproducible hypotheses and compares cost-aware out-of-sample evidence.",state:"Research workflow"},
 {name:"Johanna Becker",title:"Market Intelligence",department:"Research",code:"RS-02",summary:"Organizes cited market, macro, earnings, and event intelligence as research evidence.",state:"Role defined"},
 {name:"Dr. Anna Schneider",title:"Independent Validation",department:"Risk",code:"RK-02",summary:"Challenges methodology, leakage, stability, assumptions, and failure modes before progression.",state:"Validation workflow"},
 {name:"Maximilian Braun",title:"Trend Research Trader",department:"Trading",code:"TR-01",summary:"Runs the bounded trend research lane assigned to F in the current simulation candidate set.",state:"Offline tested"},
 {name:"Felix Hartmann",title:"Momentum Research Trader",department:"Trading",code:"TR-02",summary:"Runs the bounded momentum research lane assigned to BAC in the current simulation candidate set.",state:"Offline tested"},
 {name:"Tobias Krüger",title:"Mean-Reversion Research Trader",department:"Trading",code:"TR-03",summary:"Runs the bounded mean-reversion research lane assigned to SOFI in the current simulation candidate set.",state:"Offline tested"},
 {name:"Dr. Katharina Müller",title:"Agent Resources & Governance",department:"Governance",code:"GV-01",summary:"Tracks workflow ownership, evidence quality, workload limits, and role accountability.",state:"Role defined"},
 {name:"Dr. Markus Adler",title:"Legal & Compliance",department:"Governance",code:"GV-02",summary:"Maintains compliance questions and routes decisions requiring qualified professional review.",state:"Advisory role"},
 {name:"Sabine Richter",title:"Securities Compliance Analyst",department:"Governance",code:"GV-03",summary:"Documents securities-control questions, records boundaries, and escalation needs.",state:"Advisory role"},
 {name:"Thomas Bergmann",title:"Corporate & Tax Compliance",department:"Governance",code:"GV-04",summary:"Tracks corporate and tax research questions without representing professional advice.",state:"Advisory role"}
];
function renderEmployees(filter="All"){
 $("employees").innerHTML=employees.filter(e=>filter==="All"||e.department===filter).map(e=>`<article class="employee"><span class="department">${escape(e.department.toUpperCase())}</span><span class="role-code">${escape(e.code)}</span><h3>${escape(e.name)}</h3><h4>${escape(e.title)}</h4><p>${escape(e.summary)}</p><div class="employee-state"><span>${escape(e.state)}</span><i></i></div></article>`).join("");
}
const departments=["All",...new Set(employees.map(e=>e.department))];
$("team-filters").innerHTML=departments.map((d,i)=>`<button class="${i===0?"active":""}" data-filter="${escape(d)}">${escape(d.toUpperCase())}</button>`).join("");
$("team-filters").addEventListener("click",event=>{if(event.target.tagName!=="BUTTON")return;document.querySelectorAll("#team-filters button").forEach(b=>b.classList.remove("active"));event.target.classList.add("active");renderEmployees(event.target.dataset.filter)});renderEmployees();
