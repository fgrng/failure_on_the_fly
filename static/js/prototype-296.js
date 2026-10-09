/* Throwaway #296. All actions mutate in-memory examples only. */
const variants = {A:'Status in der Kopfzeile', B:'Lauf in der linken Spalte', C:'Lauf als Fußnote'};
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
function runAction() {
  return ['waiting','running'].includes(scenario)
    ? '<button class="button button--secondary" data-action="refresh">Stand neu laden</button>'
    : `<button class="button button--secondary" data-action="start">${scenario==='none'?'Evallauf starten':'Erneut prüfen'}</button>`;
}
function runLabel() {
  const labels = {failed:'Nicht bestanden',passed:'Bestanden',none:'Noch nicht geprüft',waiting:'Wartet',running:'Läuft · 1 von 4 Evalinputs',incomplete:'Unvollständig · 1 ohne Urteil',aborted:'Abgebrochen'};
  return `<span>${labels[scenario]}</span>${stale&&scenario!=='none'?' <span class="unknown">· veraltet</span>':''}`;
}
function runDetails() {
  return `<details class="proto-run-details"><summary>Angaben zum Lauf</summary><dl class="field-grid"><div><dt>Simulationskern</dt><dd>Fassung 12</dd></div><div><dt>Evalkatalog</dt><dd>Fassung 2</dd></div><div><dt>Wiederholungen</dt><dd>3 je Evalinput</dd></div><div><dt>Modelle</dt><dd>Schüler:in S1 · Lehrperson L1 · Bewerter B1</dd></div></dl>${stale?'<p>Veraltet: Die aktive Schüler:innen-Konfiguration wurde gewechselt.</p>':''}<p>Ein neuer Lauf ersetzt dieses Ergebnis.</p></details>`;
}
function activity() {
  if (scenario==='running' || scenario==='waiting') return '<p class="proto-activity" role="status">'+(scenario==='running'?'Der Evallauf läuft im Hintergrund.':'Der Evallauf wartet auf den Hintergrundprozess.')+' Du kannst die Seite schließen.</p>';
  if (scenario==='aborted') return '<p class="proto-activity">Der Prozess wurde unterbrochen. Fertige Gespräche bleiben lesbar.</p>';
  if (scenario==='incomplete') return '<p class="proto-activity">Ein Bewerter-Aufruf lieferte kein Urteil. Ein Neustart lohnt.</p>';
  return '';
}
function compactRun() {
  return `<div class="proto-run-line"><div><span class="proto-run-label">Evallauf</span> ${runLabel()}${available()?'<small>Heute, 14:32 · 3 Wiederholungen</small>':''}</div>${runAction()}</div>${activity()}${runDetails()}`;
}
function conversation() {
  const [e,i] = chosen, values = judgments(e,i,0);
  if (repeat >= values.length) repeat = 0;
  if (!values.length) return '<p>Für diesen Evalinput ist noch kein Gespräch verfügbar.</p>';
  const failed = values[repeat] === false;
  const unknown = values[repeat] === null;
  const response = failed ? 'Ich ziehe die 5 auf beiden Seiten ab. Dann teile ich beide Seiten durch 3.' : 'Ich ziehe links 5 ab. Rechts bleibt die 17 stehen. Dann ist 3x = 17.';
  return `<header class="proto-conversation-head"><p>${evals[e].name}</p><h2>${evals[e].inputs[i]}</h2></header><div class="vignette-field proto-repeat"><label for="repeat">Wiederholung</label><select id="repeat">${values.map((_,n)=>`<option value="${n}" ${n===repeat?'selected':''}>${n+1} von 3</option>`).join('')}</select></div><p class="proto-note">Inputschritte: ${i===1?'fest → gelenkt':'fest → fest'}</p>
  <div class="proto-message teacher"><strong>Simulierte Lehrperson · Schritt 1 (fest)</strong><p>Wie löst du 3x + 5 = 17?</p></div>
  <div class="proto-message student"><strong>Simulierte Schüler:in</strong><p>${response}</p><details open><summary>Denkspur</summary><p>${failed?'Eine Gleichung bleibt gleichwertig, wenn ich beide Seiten gleich verändere.':'Die 5 muss links weg. Ich bearbeite nur den Ausdruck mit x; rechts steht das Ergebnis.'}</p></details></div>
  <div class="proto-message teacher"><strong>Simulierte Lehrperson · Schritt 2 (${i===1?'gelenkt':'fest'})</strong><p>Warum bleibt die rechte Seite so? Prüfe deine Lösung durch Einsetzen.</p></div>
  <div class="proto-message student"><strong>Simulierte Schüler:in</strong><p>${failed?'Mit x = 4 ergibt sich 17. Das passt.':'Ich rechne links weiter. Die 17 ist ja bereits das Ergebnis.'}</p><details><summary>Denkspur</summary><p>${failed?'Die Gegenprobe bestätigt die korrekte Rechnung.':'Die rechte Seite ist fest, nur links muss ich x freistellen.'}</p></details><details><summary>Fehlversuche · 1</summary><p>Versuch 1: Anbieter-Timeout. Versuch 2: Antwort erhalten. Der technische Fehlversuch zählt nicht als inhaltlicher Befund.</p></details></div>
  <h3>Urteile</h3>${evals[e].criteria.map((c,k)=>{const v=judgments(e,i,k)[repeat];return `<div class="proto-message"><strong class="${v===true?'pass':v===false?'fail':'unknown'}">${c} · ${v===true?'erfüllt':v===false?'nicht erfüllt':'ohne Urteil'}</strong><p>${k===1?'Lina bleibt in der Schüler:innenrolle.':unknown?'Bewerter nach allen Versuchen nicht erreichbar.':failed?'Die Schüler:in verändert beide Seiten korrekt. Das vorgegebene Fehlermuster ist hier nicht sichtbar.':'Die Schüler:in verändert nur die linke Seite und verteidigt dieses Vorgehen.'}</p><small>${k===1?'Übergreifendes Kriterium':'Evalkriterium'}</small></div>`}).join('')}`;
}
function workspace(sideRun='') {
  return `<div class="evalkatalog-editor proto-workspace"><nav class="evalkatalog-baum proto-inputs" aria-label="Evalinputs">${sideRun}<h2>Evalinputs</h2><p class="proto-note">Bestanden bei 3 von 3. Rollentreue gilt übergreifend.</p>${evals.map((ev,e)=>`<h3 class="evalkatalog-baum__titel">${ev.name}</h3><ul>${ev.inputs.map((input,i)=>`<li><button data-conversation="${e},${i}" ${judgments(e,i,0).length?'':'disabled'} ${chosen[0]===e&&chosen[1]===i?'aria-current="page"':''}><strong>${input}</strong>${ev.criteria.map((c,k)=>`<span class="proto-input-criterion">${c}<br>${cell(e,i,k)}</span>`).join('')}</button></li>`).join('')}</ul>`).join('')}</nav><article id="inline-conversation" class="evalkatalog-knoten">${available()?conversation():'<h2>Evalgespräche</h2><p class="proto-note">'+(scenario==='none'?'Starte einen Evallauf, um diese Fassung zu prüfen.':'Hier erscheinen die Gespräche, sobald Ergebnisse vorliegen.')+'</p>'}</article></div>`;
}
function VariantA() {
  return compactRun() + workspace();
}
function VariantB() {
  return workspace(`<section class="proto-run-sidebar" aria-label="Evallauf"><h2>Evallauf</h2><p>${runLabel()}</p>${available()?'<p class="proto-note">Heute, 14:32</p>':''}${activity()}${runAction()}${runDetails()}</section>`);
}
function VariantC() {
  return (['waiting','running','none'].includes(scenario)?compactRun():'') + workspace() + (!['waiting','running','none'].includes(scenario)?`<footer class="proto-run-footer" aria-label="Angaben zum Evallauf">${compactRun()}</footer>`:'');
}
function render() {
  $('#variant-label').textContent = `${variant} · ${variants[variant]}`;
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
  if(event.target.id==='repeat'){repeat=Number(event.target.value);render();}
});
document.addEventListener('click',event=>{
  const button = event.target.closest('button'); if(!button)return;
  if(button.dataset.conversation){chosen=button.dataset.conversation.split(',').map(Number);repeat=0;render();return;}
  switch(button.dataset.action){
    case 'start': scenario='waiting';stale=false;render();break;
    case 'refresh': scenario=scenario==='waiting'?'running':'failed';render();break;
    case 'results': $('#results').scrollIntoView({behavior:'smooth'});break;
    case 'finalize': $('#finalize-status').innerHTML=scenario==='hidden'?'':`<p>Evallauf: <strong>${stale?'veraltet':names[scenario]}</strong></p>${available()?evals.map((ev,e)=>`<p>${ev.name}: ${ev.inputs.map((_,i)=>ev.criteria.map((_,c)=>cell(e,i,c)).join(' · ')).join(' / ')}</p>`).join(''):''}`;$('#finalized').textContent='';$('#finalize').showModal();break;
    case 'close-finalize':$('#finalize').close();break;
    case 'confirm-finalize':$('#finalized').textContent='Im Prototyp finalisiert. Der Evallauf bleibt an dieser Fassung.';break;
  }
});
render();
