// PROTOTYPE #288 – Bildfeld-Varianten. Wegwerfen, sobald entschieden ist.
// Das echte <input type="file"> bleibt die Grundlage; Alpine zeigt nur Vorschau
// und Zustand. Ablegen per Drag & Drop schreibt die Datei in dasselbe Eingabefeld.

document.addEventListener("alpine:init", () => {
    Alpine.data("bildfeld", ({ zustand, gespeichert, bild, verloren = "", textId = "", beschreibung = "" }) => ({
        zustand,
        gespeichertUrl: gespeichert ? bild : "",
        gespeichertName: "lernauftrag.png",
        vorschau: zustand === "gewaehlt" ? bild : "",
        dateiname: zustand === "gewaehlt" ? "bruchrechnung_neu.png" : "",
        groesse: zustand === "gewaehlt" ? "10 KB" : "",
        ziehen: false,
        text: "",
        textId,
        beschreibung,
        meldung: {
            fehler: "»rechnung.pdf« ist kein Bild. Erlaubt sind PNG, JPG, GIF und WebP.",
            verloren: `Ihre Auswahl »${verloren || "bruch.png"}« wurde nicht übernommen, weil das Formular noch Fehler enthält. Bitte wählen Sie das Bild erneut aus.`,
            entfernen: "Das Bild wird beim Speichern entfernt.",
            gewaehlt: "Neues Bild gewählt. Es wird beim Speichern hochgeladen.",
        }[zustand] || "",

        init() {
            const feld = this.textId && document.getElementById(this.textId);
            if (feld) this.text = feld.value;
        },

        get bildUrl() {
            if (this.zustand === "gewaehlt") return this.vorschau;
            return this.gespeichertUrl;
        },
        get anzeigename() {
            return this.zustand === "gewaehlt" ? this.dateiname : this.gespeichertName;
        },
        get istNeu() { return this.zustand === "gewaehlt"; },
        get wirdEntfernt() { return this.zustand === "entfernen"; },
        get istFehler() { return this.zustand === "fehler" || this.zustand === "verloren"; },
        get markerGesetzt() { return this.text.includes("[bild]"); },
        get statusText() {
            if (this.istNeu) return "Neu · noch nicht gespeichert";
            if (this.wirdEntfernt) return "Wird beim Speichern entfernt";
            if (this.bildUrl) return "Gespeichert";
            return "";
        },

        auswaehlen() { this.$refs.eingabe.click(); },
        gewaehlt(eingabe) {
            const datei = eingabe.files[0];
            if (!datei) return;
            if (!datei.type.startsWith("image/")) {
                eingabe.value = "";
                this.zustand = "fehler";
                this.meldung = `»${datei.name}« ist kein Bild. Erlaubt sind PNG, JPG, GIF und WebP.`;
                return;
            }
            this.vorschau = URL.createObjectURL(datei);
            this.dateiname = datei.name;
            this.groesse = `${Math.max(1, Math.round(datei.size / 1024))} KB`;
            this.zustand = "gewaehlt";
            this.meldung = `${datei.name} gewählt. Es wird beim Speichern hochgeladen.`;
        },
        abgelegt(event) {
            this.ziehen = false;
            this.$refs.eingabe.files = event.dataTransfer.files;
            this.gewaehlt(this.$refs.eingabe);
        },
        verwerfen() {
            this.$refs.eingabe.value = "";
            this.zustand = this.gespeichertUrl ? "gespeichert" : "leer";
            this.meldung = "Auswahl verworfen.";
        },
        entfernen() {
            this.$refs.eingabe.value = "";
            this.zustand = "entfernen";
            this.meldung = "Das Bild wird beim Speichern entfernt.";
        },
        behalten() {
            this.zustand = "gespeichert";
            this.meldung = "Das Bild bleibt erhalten.";
        },
    }));
});

// Variantenleiste wie beim Itemseiten-Prototyp.
function wechseln(richtung) {
    const leiste = document.querySelector(".prototype-switcher");
    window.location.search = `?variant=${leiste.dataset[richtung]}`;
}

document.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    if (event.target.matches("input, textarea, [contenteditable]")) return;
    wechseln(event.key === "ArrowLeft" ? "vorherige" : "naechste");
});
