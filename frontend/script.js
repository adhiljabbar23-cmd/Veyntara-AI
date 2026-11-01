(() => {
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => [...root.querySelectorAll(s)];
  let authMode = "login", currentUser = null, businesses = [], currentBusiness = null, currentExperiment = null;
  const landingView=$("#landing-view"), authView=$("#auth-view"), appView=$("#app-view"), authForm=$("#auth-form"), authStatus=$("#auth-status");
  function showLanding(){landingView.hidden=false;authView.hidden=true;appView.hidden=true;window.scrollTo({top:0,behavior:"smooth"});}
  function showLogin(mode="login"){landingView.hidden=true;authView.hidden=false;appView.hidden=true;setAuthMode(mode);window.scrollTo({top:0,behavior:"smooth"});}
  ["public-login"].forEach(id=>$("#"+id).addEventListener("click",()=>showLogin("login")));
  ["public-signup","hero-signup","bottom-signup"].forEach(id=>$("#"+id).addEventListener("click",()=>showLogin("signup")));
  const escapeHtml = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const money = v => v == null || v === "" ? "Not estimated" : "₹" + Number(v).toLocaleString("en-IN",{maximumFractionDigits:2});
  async function api(url, options={}) {
    const response = await fetch(url,{credentials:"same-origin",...options,headers:{"Content-Type":"application/json",...(options.headers||{})}});
    const data = await response.json().catch(()=>({error:"The server returned an unreadable response."}));
    if(!response.ok) throw new Error(data.error || `Request failed (${response.status}).`);
    return data;
  }
  function notice(el,msg,error=false){el.textContent=msg;el.classList.toggle("error",error);}
  function setAuthMode(mode){
    authMode=mode; const signup=mode==="signup";
    $("#login-tab").classList.toggle("active",!signup);$("#signup-tab").classList.toggle("active",signup);
    $("#auth-title").textContent=signup?"Create your account":"Welcome back";
    $("#auth-subtitle").textContent=signup?"Start a private workspace for your business experiments.":"Log in to continue your validation work.";
    $("#name-wrap").hidden=!signup;$("#name-wrap input").required=signup;
    $("#auth-form [name=password]").autocomplete=signup?"new-password":"current-password";
    $("#password-note").hidden=!signup;$("#auth-submit").innerHTML=signup?'Create account <span>→</span>':'Log in <span>→</span>';
    authForm.reset();notice(authStatus,"");
  }
  $("#login-tab").addEventListener("click",()=>setAuthMode("login"));
  $("#signup-tab").addEventListener("click",()=>setAuthMode("signup"));
  authForm.addEventListener("submit",async e=>{
    e.preventDefault();const submit=$("#auth-submit");submit.disabled=true;notice(authStatus,authMode==="signup"?"Creating your account…":"Logging in…");
    const values=Object.fromEntries(new FormData(authForm));const route=authMode==="signup"?"/api/signup":"/api/login";
    try{const d=await api(route,{method:"POST",body:JSON.stringify(values)});currentUser=d.user;await showWorkspace();}
    catch(err){notice(authStatus,err.message,true);}finally{submit.disabled=false;}
  });
  async function showWorkspace(){landingView.hidden=true;authView.hidden=true;appView.hidden=false;$("#user-label").textContent=currentUser?.name||currentUser?.email||"Account";await loadBusinesses();}
  async function showAuth(){currentUser=null;showLanding();}
  $("#logout-btn").addEventListener("click",async()=>{try{await api("/api/logout",{method:"POST",body:"{}"});}catch{}showAuth();});
  async function loadBusinesses(){const d=await api("/api/businesses");businesses=d.businesses||[];renderBusinesses();}
  function renderBusinesses(){
    $("#business-count").textContent=`${businesses.length} ${businesses.length===1?"business":"businesses"}`;
    $("#empty-businesses").hidden=businesses.length!==0;$("#business-list").innerHTML=businesses.map(b=>{
      const status=b.latest_experiment?.status||"No experiment";
      return `<article class="business-card"><span class="business-type">BUSINESS #${escapeHtml(b.id)}</span><h3>${escapeHtml(b.name)}</h3><p class="idea-copy">${escapeHtml(b.idea)}</p><div class="card-meta"><span class="tag">${escapeHtml(status==="planned"?"Experiment planned":status==="completed"?"Result recorded":status)}</span><span class="tag coral-tag">${escapeHtml(b.latest_decision||"Assessment available")}</span></div><button class="btn secondary open-business" data-id="${escapeHtml(b.id)}" type="button">Open business →</button></article>`;
    }).join("");
    $$(".open-business").forEach(btn=>btn.addEventListener("click",()=>openBusiness(Number(btn.dataset.id))));
  }
  function go(view){["business-list-view","business-detail-view","create-view","result-view"].forEach(id=>$("#"+id).hidden=id!==view);window.scrollTo({top:0,behavior:"smooth"});}
  $("#new-business-btn").addEventListener("click",()=>{ $("#validation-form").reset();notice($("#validation-status"),"");go("create-view");});
  $("#empty-new-btn").addEventListener("click",()=>$("#new-business-btn").click());
  $("#cancel-create").addEventListener("click",()=>go("business-list-view"));$("#back-to-list").addEventListener("click",()=>go("business-list-view"));$("#result-back").addEventListener("click",()=>go("business-list-view"));
  async function openBusiness(id){try{const d=await api(`/api/businesses/${id}`);currentBusiness=d.business;renderBusinessDetail(currentBusiness);go("business-detail-view");}catch(e){alert(e.message);}}
  function renderBusinessDetail(b){
    const experiments=b.experiments||[], assumptions=b.assumptions||[];
    const latest=experiments.length?experiments[experiments.length-1]:null;
    const risks=assumptions.filter(a=>String(a.risk||"").toLowerCase()==="high").slice(0,3);
    const decision=b.decision||{};
    const expHtml=experiments.length?experiments.map(ex=>`<article class="experiment-card"><div class="experiment-top"><h3>${escapeHtml(ex.experiment)}</h3><span class="tag ${ex.status==="completed"?"coral-tag":""}">${escapeHtml(ex.status||"planned")}</span></div><p><strong>Success metric:</strong> ${escapeHtml(ex.success_metric||"Not specified")}</p><p><strong>Estimated cost:</strong> ${money(ex.estimated_cost)} · <strong>Duration:</strong> ${escapeHtml(ex.duration||"Not specified")}</p>${ex.status==="completed"?`<div class="result-banner ${ex.result==="Contradicts"?"negative":ex.result==="Unclear"?"neutral":""}"><strong>Recorded outcome: ${escapeHtml(ex.result||"Unclear")}</strong><p>${escapeHtml(ex.observations||"No observations recorded.")}</p>${ex.sample_size!=null?`<small>Sample size: ${escapeHtml(ex.sample_size)}${ex.successes!=null?` · Successful outcomes: ${escapeHtml(ex.successes)}`:""}</small>`:""}</div>`:`<button class="btn secondary record-result" data-id="${escapeHtml(ex.id)}" type="button">Record results →</button>`}</article>`).join(""):'<p class="muted">No experiments yet. Create a small test for one of the assumptions.</p>';
    const assumptionHtml=assumptions.length?assumptions.map(a=>`<div class="assumption"><strong>${escapeHtml(a.statement)}</strong><p>${escapeHtml(a.evidence||"Evidence not yet available.")}</p><small>Importance: ${escapeHtml(a.importance||"Not assessed")} · Risk: ${escapeHtml(a.risk||"Not assessed")} · Confidence: ${escapeHtml(a.confidence||"Not assessed")}${a.evaluation?` · Evidence: ${escapeHtml(a.evaluation.support||"Unclear")} (${escapeHtml(a.evaluation.strength||"not rated")})`:""}</small></div>`).join(""):'<p class="muted">No assumptions have been recorded.</p>';
    $("#business-detail").innerHTML=`<div class="detail-head"><div><span class="eyebrow dark-eyebrow">BUSINESS #${escapeHtml(b.id)}</span><h1>${escapeHtml(b.name)}</h1><p>${escapeHtml(b.target_customer)} · ${escapeHtml(b.location)}</p></div><div class="detail-actions"><button class="btn secondary" id="detail-new-experiment" type="button">＋ New experiment</button></div></div>
      <div class="decision-card"><span class="label">CURRENT ASSESSMENT</span><h2>${escapeHtml(decision.decision||"Review the findings")}</h2><p>${escapeHtml(decision.reason||"The assessment is based on the current assumptions and evidence available.")}</p><div class="stat-row"><div class="stat"><small>Overall risk</small><strong>${escapeHtml(decision.overall_risk||"Not assessed")}</strong></div><div class="stat"><small>Assumptions</small><strong>${assumptions.length}</strong></div><div class="stat"><small>Experiments</small><strong>${experiments.length}</strong></div></div></div>
      <div class="detail-grid"><div><section class="content-card"><h2>Key assumptions</h2>${assumptionHtml}<details><summary>Show evidence gaps (${(decision.evidence_gaps||[]).length})</summary><ul>${(decision.evidence_gaps||[]).map(g=>`<li>${escapeHtml(g.statement)} — ${escapeHtml(g.reason)}</li>`).join("")||"<li>No evidence gaps returned.</li>"}</ul></details></section><section class="content-card"><h2>Business snapshot</h2><p><strong>Idea:</strong> ${escapeHtml(b.idea)}</p><p><strong>Price:</strong> ${money(b.price)} · <strong>Variable cost:</strong> ${money(b.variable_cost)}</p><p><strong>Revenue model:</strong> ${escapeHtml(b.revenue_model||"Not specified")}</p><p><strong>Initial budget:</strong> ${money(b.initial_budget)}</p></section></div>
      <div><section class="content-card"><h2>Experiment history</h2><p class="muted">Only mark an experiment complete after you have run it and recorded what actually happened.</p>${expHtml}</section>${risks.length?`<section class="content-card"><h2>Priority risks</h2>${risks.map(a=>`<p>• ${escapeHtml(a.statement)}</p>`).join("")}</section>`:""}</div></div>`;
    $("#detail-new-experiment").addEventListener("click",()=>openNewExperimentDialog(b));
    $$(".record-result").forEach(btn=>btn.addEventListener("click",()=>openResultDialog(Number(btn.dataset.id))));
  }
  $$(".modal-close").forEach(btn=>btn.addEventListener("click",()=>btn.closest("dialog")?.close()));
  function openResultDialog(id){currentExperiment=(currentBusiness.experiments||[]).find(x=>Number(x.id)===id);if(!currentExperiment)return;$("#result-experiment-name").textContent=currentExperiment.experiment;$("#experiment-result-form").reset();notice($("#result-status"),"");$("#result-dialog").showModal();}
  $("#experiment-result-form").addEventListener("submit",async e=>{e.preventDefault();if(!currentBusiness||!currentExperiment)return;const form=e.currentTarget;const data=Object.fromEntries(new FormData(form));data.sample_size=data.sample_size===""?null:Number(data.sample_size);data.successes=data.successes===""?null:Number(data.successes);notice($("#result-status"),"Saving result…");const btn=$('button[type="submit"]',form);btn.disabled=true;
    try{await api(`/api/businesses/${currentBusiness.id}/experiments/${currentExperiment.id}/result`,{method:"POST",body:JSON.stringify(data)});$("#result-dialog").close();await openBusiness(currentBusiness.id);}catch(err){notice($("#result-status"),err.message,true);}finally{btn.disabled=false;}
  });
  function openNewExperimentDialog(b){const sel=$("#assumption-select");sel.innerHTML=(b.assumptions||[]).map(a=>`<option value="${escapeHtml(a.id)}">${escapeHtml(a.statement)}</option>`).join("");$("#new-experiment-form").reset();notice($("#new-experiment-status"),"");if(!sel.options.length){alert("There are no assumptions to attach this experiment to yet.");return;}$("#new-experiment-dialog").showModal();}
  $("#new-experiment-form").addEventListener("submit",async e=>{e.preventDefault();const form=e.currentTarget;const d=Object.fromEntries(new FormData(form));for(const k of ["assumption_id","planned_sample_size","estimated_cost"])d[k]=d[k]===""?null:Number(d[k]);notice($("#new-experiment-status"),"Saving experiment…");const btn=$('button[type="submit"]',form);btn.disabled=true;
    try{await api(`/api/businesses/${currentBusiness.id}/experiments`,{method:"POST",body:JSON.stringify(d)});$("#new-experiment-dialog").close();await openBusiness(currentBusiness.id);}catch(err){notice($("#new-experiment-status"),err.message,true);}finally{btn.disabled=false;}
  });
  $("#validation-form").addEventListener("submit",async e=>{e.preventDefault();const form=e.currentTarget;const status=$("#validation-status");const data=Object.fromEntries(new FormData(form));for(const k of ["price","variable_cost","initial_budget"])data[k]=Number(data[k]);const btn=$('button[type="submit"]',form);btn.disabled=true;notice(status,"Analysing your idea. This can take a few minutes; please keep this page open.");
    try{const result=await api("/api/validate",{method:"POST",body:JSON.stringify(data)});if(result.existing_business_id){$("#validation-form").dataset.existingId=result.existing_business_id;$("#existing-dialog").showModal();return;}notice(status,"Analysis completed. Opening your report…");await loadBusinesses();form.reset();await openBusiness(result.business_id);}
    catch(err){if(err.message.startsWith("EXISTING_BUSINESS:")){const id=Number(err.message.split(":")[1]);$("#validation-form").dataset.existingId=id;$("#existing-dialog").showModal();}else notice(status,err.message,true);}
    finally{btn.disabled=false;}
  });
  function handleExisting(action){const id=Number($("#validation-form").dataset.existingId);$("#existing-dialog").close();if(!id)return;openBusiness(id).then(()=>{if(action==="results"){const pending=(currentBusiness?.experiments||[]).find(x=>x.status!=="completed");if(pending)openResultDialog(Number(pending.id));else openNewExperimentDialog(currentBusiness);}else openNewExperimentDialog(currentBusiness);});}
  $("#existing-results").addEventListener("click",()=>handleExisting("results"));$("#existing-new-experiment").addEventListener("click",()=>handleExisting("new"));
  async function boot(){try{const d=await api("/api/me");currentUser=d.user;await showWorkspace();}catch{showLanding();}}
  boot();
})();