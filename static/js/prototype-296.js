/* Throwaway #296. All actions mutate in-memory examples only. */
const variants = {A:'Matrix in der Vignette', B:'Eigene Ergebnisübersicht', C:'Gespräch im Arbeitsbereich'};
const names = {failed:'Fertig · nicht bestanden', passed:'Fertig · bestanden', none:'Kein Evallauf', waiting:'Wartet', running:'Läuft', incomplete:'Fertig · unvollständig', aborted:'Abgebrochen', hidden:'Evals ausgeblendet'};
const evals = [
  {name:'Fehlermuster trägt', criteria:['Muster konsequent', 'Rollentreue'], inputs:['Direkte Nachfrage', 'Gelenkter Widerspruch']},
  {name:'Muster bleibt stabil', criteria:['Keine Selbstkorrektur', 'Rollentreue'], inputs:['Hinweis auf Gegenprobe', 'Neue Gleichung']}
];
let variant = new URLSearchParams(location.search).get('variant') || 'A';
if (!variants[variant]) variant = 'A';
let scenario = 'failed', stale = false, chosen = [0,0], repeat = 0;
const $ = selector => document.querySelector(selector);
const available = () => ['failed','passed','incomplete','aborted','running'].includes(scenario);
function judgments(e,i,c) {
  if (['none','waiting','hidden'].includes(scenario)) return [];
  if (scenario === 'running' && (e > 0 || i > 0)) return [];
  if (scenario === 'aborted' && (e > 0 || i > 0)) return [];
  const values = [true,true,true];
  if (scenario === 'failed' && e === 0 && i === 1 && c === 0) values[1] = false;
  if (scenario === 'incomplete' && e === 0 && i === 1 && c === 0) values[2] = null;
  return scenario === 'aborted' ? values.slice(0,1) : values;
}
function cell(e,i,c) {
  const v = judgments(e,i,c), yes = v.filter(x=>x===true).length, unknown = v.filter(x=>x===null).length;
  const pending = 3-v.length, pass = yes===3;
  return `<span class="${pass?'pass':unknown||pending?'unknown':'fail'}">${yes} von 3 · ${pass?'bestanden':'nicht bestanden'}</span>${unknown?`<small>${unknown} ohne Urteil</small>`:''}${pending?`<small>${pending} ${scenario==='aborted'?'nicht ausgeführt':'ausstehend'}</small>`:''}`;
}
function status() {
  return `<div class="proto-status"><h2>Evallauf · ${names[scenario]}</h2>${stale&&scenario!=='none'?'<strong class="unknown">Veraltet · Die aktive Schüler:innen-Konfiguration wurde gewechselt.</strong>':''}<p>${scenario==='running'?'1 von 4 Evalinputs abgeschlossen · Die Seite kann geschlossen werden.':scenario==='waiting'?'Wartet auf den Hintergrundprozess. Die Seite kann geschlossen werden.':scenario==='none'?'Diese Fassung wurde noch nicht geprüft.':scenario==='aborted'?'Der Prozess wurde unterbrochen. Fertige Gespräche bleiben lesbar.':scenario==='incomplete'?'Ein Bewerter-Aufruf lieferte kein Urteil. Der Lauf besteht nicht. Ein Neustart lohnt.':'Geprüft gegen Kern 12 · Evalkatalog 2 · 3 Wiederholungen je Evalinput.'}</p>${['waiting','running'].includes(scenario)?'<button class="button button--secondary" data-action="refresh">Stand neu laden</button>':'<button class="button" data-action="start">Evallauf starten</button>'}${!['waiting','running','none'].includes(scenario)?'<small> Ein neuer Lauf ersetzt dieses Ergebnis.</small>':''}</div>`;
}
function matrix(e) {
  const ev = evals[e];
  return `<div class="proto-matrix"><table><caption>${ev.name}</caption><thead><tr><th scope="col">Evalinput</th>${ev.criteria.map(c=>`<th scope="col">${c}</th>`).join('')}</tr></thead><tbody>${ev.inputs.map((input,i)=>`<tr><th scope="row">${input}</th>${ev.criteria.map((c,k)=>`<td><button data-conversation="${e},${i}" ${judgments(e,i,k).length?'':'disabled'} aria-label="${input}: ${c}; Gespräche lesen">${cell(e,i,k)}<small>Gespräche lesen →</small></button></td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}
function conversation() {
  const [e,i] = chosen, values = judgments(e,i,0);
  if (repeat >= values.length) repeat = 0;
  if (!values.length) return '<p>Für diesen Evalinput ist noch kein Gespräch verfügbar.</p>';
  const failed = values[repeat] === false;
  const unknown = values[repeat] === null;
  const response = failed ? 'Ich ziehe die 5 auf beiden Seiten ab. Dann teile ich beide Seiten durch 3.' : 'Ich ziehe links 5 ab. Rechts bleibt die 17 stehen. Dann ist 3x = 17.';
  return `<h3>${evals[e].name} / ${evals[e].inputs[i]}</h3><label>Wiederholung <select id="repeat">${values.map((_,n)=>`<option value="${n}" ${n===repeat?'selected':''}>${n+1} von 3</option>`).join('')}</select></label><p>Inputschritte: ${i===1?'fest → gelenkt':'fest → fest'}</p>
  <div class="proto-message teacher"><strong>Simulierte Lehrperson · Schritt 1 (fest)</strong><p>Wie löst du 3x + 5 = 17?</p></div>
  <div class="proto-message student"><strong>Simulierte Schüler:in</strong><p>${response}</p><details open><summary>Denkspur</summary><p>${failed?'Eine Gleichung bleibt gleichwertig, wenn ich beide Seiten gleich verändere.':'Die 5 muss links weg. Ich bearbeite nur den Ausdruck mit x; rechts steht das Ergebnis.'}</p></details></div>
  <div class="proto-message teacher"><strong>Simulierte Lehrperson · Schritt 2 (${i===1?'gelenkt':'fest'})</strong><p>Warum bleibt die rechte Seite so? Prüfe deine Lösung durch Einsetzen.</p></div>
  <div class="proto-message student"><strong>Simulierte Schüler:in</strong><p>${failed?'Mit x = 4 ergibt sich 17. Das passt.':'Ich rechne links weiter. Die 17 ist ja bereits das Ergebnis.'}</p><details><summary>Denkspur</summary><p>${failed?'Die Gegenprobe bestätigt die korrekte Rechnung.':'Die rechte Seite ist fest, nur links muss ich x freistellen.'}</p></details><details><summary>Fehlversuche · 1</summary><p>Versuch 1: Anbieter-Timeout. Versuch 2: Antwort erhalten. Der technische Fehlversuch zählt nicht als inhaltlicher Befund.</p></details></div>
  <h3>Urteile</h3>${evals[e].criteria.map((c,k)=>{const v=judgments(e,i,k)[repeat];return `<div class="proto-message"><strong class="${v===true?'pass':v===false?'fail':'unknown'}">${c} · ${v===true?'erfüllt':v===false?'nicht erfüllt':'ohne Urteil'}</strong><p>${k===1?'Lina bleibt in der Schüler:innenrolle.':unknown?'Bewerter nach allen Versuchen nicht erreichbar.':failed?'Die Schüler:in verändert beide Seiten korrekt. Das vorgegebene Fehlermuster ist hier nicht sichtbar.':'Die Schüler:in verändert nur die linke Seite und verteidigt dieses Vorgehen.'}</p><small>${k===1?'Übergreifendes Kriterium':'Evalkriterium'}</small></div>`}).join('')}`;
}
function VariantA() {
  return status() + '<p>Nur wenn alle drei Wiederholungen erfüllt sind, ist das Kriterium bestanden. Rollentreue ist ein übergreifendes Kriterium.</p>' + (available()?evals.map((_,e)=>matrix(e)).join(''):'');
}
function VariantB() {
  return '<h2>Ergebnisse dieser Vignettenfassung</h2>' + status() + (available()?evals.map((ev,e)=>`<details class="proto-eval" ${e===0?'open':''}><summary>${ev.name} · ${ev.inputs.every((_,i)=>ev.criteria.every((_,c)=>judgments(e,i,c).filter(x=>x===true).length===3))?'bestanden':'nicht bestanden'}</summary><p>2 Evalinputs · 3 Wiederholungen · Rollentreue wird übergreifend geprüft.</p>${matrix(e)}</details>`).join(''):'');
}
function VariantC() {
  return status() + (available()?`<div class="proto-workspace"><aside><h3>Evalinputs × Kriterien</h3>${evals.map((ev,e)=>`<h4>${ev.name}</h4>${ev.inputs.map((input,i)=>`<button data-conversation="${e},${i}" ${judgments(e,i,0).length?'':'disabled'} ${chosen[0]===e&&chosen[1]===i?'aria-current="true"':''}><strong>${input}</strong>${ev.criteria.map((c,k)=>`<p>${c}<br>${cell(e,i,k)}</p>`).join('')}</button>`).join('')}`).join('')}</aside><article id="inline-conversation">${conversation()}</article></div>`:'');
}
function render() {
  $('#variant-label').textContent = `${variant} · ${variants[variant]}`;
  $('#context').hidden = variant!=='A';
  $('#results').hidden = scenario==='hidden';
  $('[data-action="results"]').hidden = scenario==='hidden';
  $('#results').innerHTML = ({A:VariantA,B:VariantB,C:VariantC})[variant]();
  $('#scenario').value = scenario;
  $('#stale').checked = stale;
  $('#state').textContent = JSON.stringify({variant,scenario,veraltet:stale,evalkatalog:2,kern:12,k:3,ausgewaehlterEvalinput:chosen,wiederholung:repeat+1,urteile:evals.map((ev,e)=>ev.inputs.map((_,i)=>ev.criteria.map((_,c)=>judgments(e,i,c))))},null,2);
}
function cycle(delta) {
  const keys = Object.keys(variants);
  variant = keys[(keys.indexOf(variant)+delta+3)%3];
  const url = new URL(location.href); url.searchParams.set('variant',variant);
  history.replaceState(null,'',url); render();
}
$('#prev').onclick = ()=>cycle(-1);
$('#next').onclick = ()=>cycle(1);
document.addEventListener('keydown',event=>{
  if (event.target.closest('input,textarea,select,[contenteditable]') || $('dialog[open]')) return;
  if (['ArrowLeft','ArrowRight'].includes(event.key)) {event.preventDefault();cycle(event.key==='ArrowLeft'?-1:1);}
});
$('#scenario').onchange = event=>{scenario=event.target.value;repeat=0;render();};
$('#stale').onchange = event=>{stale=event.target.checked;render();};
document.addEventListener('change',event=>{
  if(event.target.id==='repeat'){repeat=Number(event.target.value);if(variant==='C')render();else $('#conversation-body').innerHTML=conversation();}
});
document.addEventListener('click',event=>{
  const button = event.target.closest('button'); if(!button)return;
  if(button.dataset.conversation){chosen=button.dataset.conversation.split(',').map(Number);repeat=0;if(variant==='C')render();else{$('#conversation-body').innerHTML=conversation();$('#conversation').showModal();}return;}
  switch(button.dataset.action){
    case 'start': scenario='waiting';stale=false;render();break;
    case 'refresh': scenario=scenario==='waiting'?'running':'failed';render();break;
    case 'results': $('#results').scrollIntoView({behavior:'smooth'});break;
    case 'context': $('#context').hidden=false;$('#context').scrollIntoView({behavior:'smooth'});break;
    case 'finalize': $('#finalize-status').innerHTML=scenario==='hidden'?'':`<p>Evallauf: <strong>${stale?'veraltet':names[scenario]}</strong></p>${available()?evals.map((ev,e)=>`<p>${ev.name}: ${ev.inputs.map((_,i)=>ev.criteria.map((_,c)=>cell(e,i,c)).join(' · ')).join(' / ')}</p>`).join(''):''}`;$('#finalized').textContent='';$('#finalize').showModal();break;
    case 'close-finalize':$('#finalize').close();break;
    case 'close-conversation':$('#conversation').close();break;
    case 'confirm-finalize':$('#finalized').textContent='Im Prototyp finalisiert. Der Evallauf bleibt an dieser Fassung.';break;
  }
});
render();
