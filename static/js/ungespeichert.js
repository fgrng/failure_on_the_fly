// Warnt beim Verlassen der Seite, solange ein Formular mit
// data-ungespeichert-warnen vom geladenen Stand abweicht. Maßstab sind die
// Vorgabewerte des HTML, so gilt ein per »Abbrechen« zurückgesetzter Text
// wieder als gespeichert. Das Absenden eines Formulars hebt die Warnung auf.
(() => {
    const abweichend = (feld) => {
        if (feld instanceof HTMLSelectElement) {
            const optionen = Array.from(feld.options);
            return optionen.some((option) => option.defaultSelected)
                ? optionen.some((option) => option.selected !== option.defaultSelected)
                : feld.selectedIndex > 0;
        }
        if (feld.type === "checkbox" || feld.type === "radio") {
            return feld.checked !== feld.defaultChecked;
        }
        return "defaultValue" in feld && feld.value !== feld.defaultValue;
    };

    let wirdAbgesendet = false;
    document.addEventListener("submit", () => { wirdAbgesendet = true; });
    window.addEventListener("beforeunload", (event) => {
        if (wirdAbgesendet) return;
        const formulare = document.querySelectorAll("form[data-ungespeichert-warnen]");
        if (Array.from(formulare).some((formular) => Array.from(formular.elements).some(abweichend))) {
            event.preventDefault();
        }
    });
})();
