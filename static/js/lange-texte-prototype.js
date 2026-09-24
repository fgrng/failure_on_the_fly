// PROTOTYPE #290 – lange Erhebungstexte. Wegwerfen, sobald entschieden ist.
// Alle Varianten teilen einen Alpine-Store: Quelle, gespeicherter Stand, Status.
// Speichern schreibt nichts, es übernimmt nur den Stand und meldet, was gesendet würde.

// Grobe Markdown-Vorschau statt des Server-Renderers aus texte/ (liegt nur auf main).
function markdownGrob(quelle) {
    const esc = (s) => s.replace(/[&<>"]/g, (z) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[z]);
    const inline = (s) => esc(s)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/\[(.+?)\]\(((?:https?|mailto):[^)]+)\)/g, '<a href="$2">$1</a>');
    return quelle.trim().split(/\n{2,}/).filter(Boolean).map((block) => {
        const kopf = block.match(/^(#{1,3}) (.*)/);
        if (kopf) return `<h${kopf[1].length + 2}>${inline(kopf[2])}</h${kopf[1].length + 2}>`;
        if (/^- /.test(block)) {
            return `<ul>${block.split("\n").map((z) => `<li>${inline(z.replace(/^- /, ""))}</li>`).join("")}</ul>`;
        }
        return `<p>${inline(block).replace(/\n/g, "<br>")}</p>`;
    }).join("");
}

document.addEventListener("alpine:init", () => {
    const texte = JSON.parse(document.getElementById("lange-texte-daten").textContent);
    Alpine.store("texte", {
        liste: texte.map((t) => ({ ...t, gespeichert: t.wert })),
        meldung: "",
        abschnitt02: 0,

        get(schluessel) { return this.liste.find((t) => t.schluessel === schluessel); },
        html(t) { return markdownGrob(t.wert); },
        leer(t) { return !t.wert.trim(); },
        geaendert(t) { return t.wert !== t.gespeichert; },
        fehlt(t) { return t.benoetigt && this.leer(t); },
        status(t) {
            if (this.geaendert(t)) return "Ungespeichert";
            if (this.fehlt(t)) return "Leer · wird benötigt";
            if (this.leer(t)) return "Leer";
            return `${t.wert.length} Zeichen`;
        },
        statusklasse(t) {
            if (this.geaendert(t)) return "lt-status--geaendert";
            if (this.fehlt(t)) return "lt-status--fehlt";
            return "";
        },
        ersteZeile(t) {
            const text = t.wert.replace(/[#*_>\-\[\]()]/g, " ").replace(/\s+/g, " ").trim();
            return text.length > 160 ? `${text.slice(0, 160)} …` : text;
        },
        speichern(schluessel) {
            const ziel = schluessel ? [this.get(schluessel)] : this.liste;
            const gesendet = ziel.filter((t) => this.geaendert(t)).map((t) => t.label);
            ziel.forEach((t) => { t.gespeichert = t.wert; });
            this.meldung = gesendet.length
                ? `Prototyp: würde speichern – ${gesendet.join(", ")}.`
                : "Prototyp: nichts geändert, nichts zu speichern.";
        },
        verwerfen(schluessel) {
            const t = this.get(schluessel);
            t.wert = t.gespeichert;
        },
        get ungespeichert() { return this.liste.some((t) => this.geaendert(t)); },
    });

    // Wo beginnt Abschnitt 02? Das ist die Höhe, um die es in #290 geht.
    const messen = () => {
        const a = document.getElementById("lt-konfiguration");
        const b = document.getElementById("lt-vignetten");
        if (a && b) Alpine.store("texte").abschnitt02 = Math.round(b.getBoundingClientRect().top - a.getBoundingClientRect().top);
    };
    const beobachter = new ResizeObserver(messen);
    document.addEventListener("DOMContentLoaded", () => {
        beobachter.observe(document.body);
        beobachter.observe(document.getElementById("lt-konfiguration"));
    });
    window.addEventListener("beforeunload", (event) => {
        if (Alpine.store("texte").ungespeichert) event.preventDefault();
    });
});
