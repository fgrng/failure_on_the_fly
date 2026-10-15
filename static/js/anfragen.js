// Gemeinsame Behandlung abgeschickter Formulare, ohne Inline-Handler (#486).
// - htmx tauscht 4xx/5xx-Antworten nicht ein; ohne Hinweis bliebe die Seite
//   stumm. Scheitert eine htmx-Anfrage, erscheint #anfragefehler aus dem
//   Basistemplate, die nächste gelungene Anfrage blendet ihn wieder aus.
// - data-schreibschutz-waehrend-anfrage: Textfelder des Formulars sind
//   während seiner htmx-Anfrage schreibgeschützt und danach wieder frei.
// - data-einmal-absenden: Ohne htmx löst ein zweiter Klick keinen zweiten
//   Post aus, solange der erste läuft.
(() => {
    const hinweisZeigen = () => {
        const hinweis = document.getElementById("anfragefehler");
        if (!hinweis) return;
        hinweis.textContent = "Die Anfrage ist nicht angekommen. Bitte versuchen Sie es erneut.";
        hinweis.hidden = false;
    };
    document.addEventListener("htmx:responseError", hinweisZeigen);
    document.addEventListener("htmx:sendError", hinweisZeigen);

    const textfelder = (formular) => formular.querySelectorAll("textarea, input:not([type=hidden])");
    document.addEventListener("htmx:beforeRequest", (ereignis) => {
        const formular = ereignis.detail.elt;
        if (!formular.hasAttribute?.("data-schreibschutz-waehrend-anfrage")) return;
        textfelder(formular).forEach((feld) => { feld.readOnly = true; });
    });
    document.addEventListener("htmx:afterRequest", (ereignis) => {
        const formular = ereignis.detail.elt;
        if (formular.hasAttribute?.("data-schreibschutz-waehrend-anfrage")) {
            textfelder(formular).forEach((feld) => { feld.readOnly = false; });
        }
        if (ereignis.detail.successful) {
            const hinweis = document.getElementById("anfragefehler");
            if (hinweis) hinweis.hidden = true;
        }
    });

    const knoepfe = (formular) => formular.querySelectorAll("button[type=submit], button:not([type])");
    document.addEventListener("submit", (ereignis) => {
        const formular = ereignis.target;
        if (!formular.hasAttribute("data-einmal-absenden")) return;
        if (formular.dataset.wirdAbgesendet) {
            ereignis.preventDefault();
            return;
        }
        // htmx hat die Anfrage übernommen und sperrt selbst über hx-disabled-elt.
        if (ereignis.defaultPrevented) return;
        formular.dataset.wirdAbgesendet = "ja";
        // Erst nach dem Absenden sperren: gesperrte Knöpfe fehlen in den Formulardaten.
        setTimeout(() => knoepfe(formular).forEach((knopf) => { knopf.disabled = true; }));
    });
    // Zurück aus dem Seitencache: das Formular ist wieder frei.
    window.addEventListener("pageshow", (ereignis) => {
        if (!ereignis.persisted) return;
        document.querySelectorAll("form[data-wird-abgesendet]").forEach((formular) => {
            delete formular.dataset.wirdAbgesendet;
            knoepfe(formular).forEach((knopf) => { knopf.disabled = false; });
        });
    });
})();
