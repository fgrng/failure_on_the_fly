// Bildkarte im Vignettenformular (#288): Vorschau, Ablegen, Ersetzen und Entfernen
// über dem echten <input type="file">. Der Startzustand kommt vom Server als
// data-Attribute der Karte (vignetten/includes/bildkarte_field.html).

document.addEventListener("alpine:init", () => {
    Alpine.data("bildkarte", () => ({
        zustand: "leer",
        gespeichertUrl: "",
        vorschau: "",
        dateiname: "",
        beschreibung: "",
        beschreibungVorher: "",
        textId: "",
        text: "",
        ziehen: false,
        meldung: "",

        init() {
            const daten = this.$el.dataset;
            this.zustand = daten.zustand;
            this.gespeichertUrl = daten.gespeichert;
            this.textId = daten.textId;
            // Vor der x-model-Bindung lesen, sonst überschreibt "" den Serverwert;
            // $refs gibt es in init() noch nicht.
            this.beschreibung = this.$el.querySelector("textarea").value;
            this.text = document.getElementById(this.textId)?.value ?? "";
            if (daten.verloren) {
                this.meldung = `Ihre Auswahl »${daten.verloren}« wurde nicht übernommen, weil das Formular noch Fehler enthält. Bitte wählen Sie das Bild erneut aus.`;
            }
        },

        get bildUrl() {
            return this.zustand === "gewaehlt" ? this.vorschau : this.gespeichertUrl;
        },
        get istNeu() { return this.zustand === "gewaehlt"; },
        get wirdEntfernt() { return this.zustand === "entfernen"; },
        get istFehler() { return this.zustand === "fehler" || this.zustand === "verloren"; },
        get markerGesetzt() { return /\[bild\]/i.test(this.text); },
        get statusText() {
            if (this.istNeu) return "Neu · noch nicht gespeichert";
            if (this.wirdEntfernt) return "Wird beim Speichern entfernt";
            return this.bildUrl ? "Gespeichert" : "";
        },

        auswaehlen() { this.$refs.eingabe.click(); },
        gewaehlt(eingabe) {
            const datei = eingabe.files[0];
            if (!datei) return;
            if (!datei.type.startsWith("image/")) {
                eingabe.value = "";
                this.zustand = "fehler";
                this.meldung = `»${datei.name}« ist kein Bild. Erlaubt sind zum Beispiel PNG, JPG, GIF und WebP.`;
                return;
            }
            if (this.wirdEntfernt) this.beschreibung = this.beschreibungVorher;
            this.vorschau = URL.createObjectURL(datei);
            this.dateiname = datei.name;
            this.zustand = "gewaehlt";
            this.meldung = `»${datei.name}« gewählt. Das Bild wird beim Speichern hochgeladen.`;
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
            this.beschreibungVorher = this.beschreibung;
            this.beschreibung = "";
            this.zustand = "entfernen";
            this.meldung = "Bild und Bildbeschreibung werden beim Speichern entfernt.";
        },
        behalten() {
            this.beschreibung = this.beschreibungVorher;
            this.zustand = "gespeichert";
            this.meldung = "Das Bild bleibt erhalten.";
        },
    }));
});
