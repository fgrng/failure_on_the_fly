// Fügt den Platzhalter eines Knopfs mit data-platzhalter an der Schreibmarke
// des Textfelds data-ziel ein und lässt die Schreibmarke dahinter stehen.
document.addEventListener("click", (event) => {
    const knopf = event.target.closest("[data-platzhalter]");
    if (!knopf) return;
    const feld = document.getElementById(knopf.dataset.ziel);
    if (!feld) return;
    feld.focus();
    feld.setRangeText(knopf.dataset.platzhalter, feld.selectionStart, feld.selectionEnd, "end");
    feld.dispatchEvent(new Event("input", { bubbles: true }));
});
