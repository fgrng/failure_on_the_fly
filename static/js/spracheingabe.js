(() => {
    const meldungen = {
        leeres_transkript: "Es wurde kein Text erkannt. Nehmen Sie bitte erneut auf.",
        anbieterfehler: "Die Transkription ist fehlgeschlagen. Nehmen Sie bitte erneut auf.",
        anbieter_nicht_erreichbar: "Die Transkription ist derzeit nicht erreichbar. Versuchen Sie es bitte erneut.",
    };

    const einrichten = (bereich) => {
        if (bereich.dataset.eingerichtet) return;
        bereich.dataset.eingerichtet = "true";

        const formular = document.getElementById(bereich.dataset.formularId);
        const eingabe = document.getElementById(bereich.dataset.eingabeId);
        const tastatureingabe = document.getElementById(bereich.dataset.tastatureingabeId);
        const steuerung = bereich.querySelector(".spracheingabe__steuerung");
        const status = bereich.querySelector(".spracheingabe__status");
        if (!formular || !eingabe || !steuerung || !status) return;

        let recorder;
        let stream;
        let audioTeile = [];

        const zustand = (text, aufnahme = false) => {
            status.textContent = text;
            bereich.classList.toggle("spracheingabe--aufnahme", aufnahme);
        };
        const zuruecksetzen = () => {
            steuerung.disabled = false;
            steuerung.textContent = "Aufnahme starten";
            steuerung.setAttribute("aria-pressed", "false");
        };
        const aufnahme_deaktivieren = (text) => {
            steuerung.hidden = true;
            zustand(text);
        };
        const mikrofon_verweigert = () => aufnahme_deaktivieren(
            "Der Mikrofonzugriff wurde nicht erteilt. Nutzen Sie die Tastatureingabe."
        );
        const transkribieren = async () => {
            zustand("Ihre Aufnahme wird transkribiert.");
            const daten = new FormData();
            daten.append("audio", new Blob(audioTeile, { type: recorder.mimeType || "audio/webm" }), "aufnahme.webm");
            try {
                const antwort = await fetch(bereich.dataset.transkriptionUrl, {
                    method: "POST",
                    body: daten,
                    headers: { "X-CSRFToken": formular.querySelector("[name=csrfmiddlewaretoken]").value },
                });
                const ergebnis = await antwort.json();
                if (!antwort.ok) throw new Error(ergebnis.status);
                const automatischAbsenden = bereich.dataset.automatischAbsenden === "true";
                if (automatischAbsenden) eingabe.readOnly = true;
                eingabe.value = automatischAbsenden
                    ? ergebnis.text
                    : `${eingabe.value}${eingabe.value ? "\n" : ""}${ergebnis.text}`;
                eingabe.hidden = false;
                zustand("Das Transkript wurde hinzugefügt. Sie können weiter aufnehmen oder tippen.");
                if (automatischAbsenden) formular.requestSubmit();
            } catch (fehler) {
                if (["einwilligung_verweigert", "zero_retention_fehlt"].includes(fehler.message)) {
                    aufnahme_deaktivieren("Die Transkription ist nicht verfügbar. Nutzen Sie die Tastatureingabe.");
                    return;
                }
                zustand(meldungen[fehler.message] || "Die Transkription ist fehlgeschlagen. Nehmen Sie Ihre Frage bitte erneut auf.");
                zuruecksetzen();
            }
        };
        const stoppen = () => {
            steuerung.disabled = true;
            recorder.stop();
            stream.getTracks().forEach((spur) => spur.stop());
        };
        const starten = async () => {
            if (!navigator.mediaDevices || !window.MediaRecorder) {
                mikrofon_verweigert();
                return;
            }
            try {
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioTeile = [];
                recorder = new MediaRecorder(stream);
                recorder.addEventListener("dataavailable", (ereignis) => audioTeile.push(ereignis.data));
                recorder.addEventListener("stop", transkribieren, { once: true });
                recorder.start();
                steuerung.textContent = "Aufnahme beenden";
                steuerung.setAttribute("aria-pressed", "true");
                zustand("Aufnahme läuft. Beenden Sie die Aufnahme, wenn sie vollständig ist.", true);
            } catch {
                mikrofon_verweigert();
            }
        };

        if (tastatureingabe) {
            formular.addEventListener("submit", () => {
                tastatureingabe.value += `${tastatureingabe.value && eingabe.value ? "\n" : ""}${eingabe.value}`;
            });
        }
        steuerung.addEventListener("click", () => (recorder?.state === "recording" ? stoppen() : starten()));
    };

    document.addEventListener("DOMContentLoaded", () => document.querySelectorAll("[data-spracheingabe]").forEach(einrichten));
    document.addEventListener("htmx:load", (ereignis) => ereignis.detail.elt.querySelectorAll?.("[data-spracheingabe]").forEach(einrichten));
})();
