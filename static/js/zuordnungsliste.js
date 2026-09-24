function zuordnungsdaten(id) {
    return JSON.parse(document.getElementById(id).textContent);
}

function zuordnungsliste({ datenId, verfuegbarId, randomisierungId, fest }) {
    return {
        rows: zuordnungsdaten(datenId),
        verfuegbar: verfuegbarId ? zuordnungsdaten(verfuegbarId) : [],
        randomisierung: randomisierungId ? zuordnungsdaten(randomisierungId) : fest,
        fest,
        wahl: "",
        position: "",
        meldung: "",

        init() {
            document.addEventListener("zuordnung:aktualisiert", (event) => {
                this.rows = event.detail[datenId];
                if (verfuegbarId) this.verfuegbar = event.detail[verfuegbarId];
                if (randomisierungId) this.randomisierung = event.detail[randomisierungId];
            });
        },
        get geordnet() {
            return this.randomisierung === this.fest;
        },
        kurz(text) {
            return text.length > 40 ? `${text.slice(0, 39)}…` : text;
        },
        einfuegen() {
            const eintrag = this.verfuegbar.find((e) => String(e.pk) === this.wahl);
            if (!eintrag) return;
            const felder = this.geordnet && this.position ? { position: this.position } : {};
            this.wahl = "";
            this.position = "";
            this.senden(eintrag.einfuegen_url, felder, `${eintrag.label} eingefügt.`);
        },
        verschieben(zeile, position, knopf = null) {
            this.senden(
                zeile.verschieben_url,
                { position },
                `${zeile.label}: Position ${Math.min(position, this.rows.length)} von ${this.rows.length}.`,
                { pk: zeile.pk, knopf }
            );
        },
        async senden(url, felder, meldung, fokus = null) {
            const formData = new FormData();
            formData.append(
                "csrfmiddlewaretoken",
                document.querySelector("[name=csrfmiddlewaretoken]").value
            );
            for (const [name, wert] of Object.entries(felder)) {
                formData.append(name, wert);
            }
            const response = await fetch(url, { method: "POST", body: formData });
            if (!response.ok) {
                this.meldung = "";
                this.$nextTick(() => {
                    this.meldung = "Das hat nicht geklappt. Bitte laden Sie die Seite neu.";
                });
                return;
            }
            const doc = new DOMParser().parseFromString(await response.text(), "text/html");
            const aktualisierteDaten = Object.fromEntries(
                Array.from(document.querySelectorAll("[data-zuordnung-daten] script")).map(
                    (element) => [element.id, JSON.parse(doc.getElementById(element.id).textContent)]
                )
            );
            document.dispatchEvent(
                new CustomEvent("zuordnung:aktualisiert", { detail: aktualisierteDaten })
            );
            // Leeren und neu setzen, damit Screenreader auch Wiederholungen ansagen.
            this.meldung = "";
            this.$nextTick(() => {
                this.meldung = meldung;
                if (fokus) this.fokussieren(fokus);
            });
        },
        fokussieren({ pk, knopf }) {
            // x-for verschiebt die Zeile; der Fokus geht dabei verloren.
            const zeile = this.$root.querySelector(`[data-pk="${pk}"]`);
            const knoepfe = Array.from(zeile?.querySelectorAll("button") ?? []);
            const ziel =
                knoepfe.find((b) => b.title === knopf && !b.disabled) ??
                knoepfe.find((b) => !b.disabled);
            ziel?.focus();
        },
    };
}

// Umsortieren per Ziehen am Griff, nur innerhalb einer Liste. Pointer Events
// decken Maus, Touch und Stift ab; der Weg ohne Maus sind die Pfeil-Knöpfe.
(() => {
    let zug = null;
    let gezogenUm = 0;
    const marke = document.createElement("div");
    marke.className = "zuordnung-einfuegemarke";

    function zielIndex(y) {
        const zeilen = zug.liste.querySelectorAll(".zuordnungsliste__zeile");
        const andere = Array.from(zeilen).filter((z) => z !== zug.zeile);
        let index = andere.length;
        for (let i = 0; i < andere.length; i++) {
            const r = andere[i].getBoundingClientRect();
            if (y < r.top + r.height / 2) {
                index = i;
                break;
            }
        }
        const r = index < andere.length
            ? andere[index].getBoundingClientRect()
            : andere.at(-1)?.getBoundingClientRect();
        const lr = zug.liste.getBoundingClientRect();
        const top = !r ? lr.top + 4 : index < andere.length ? r.top - 3 : r.bottom + 1;
        Object.assign(marke.style, { top: `${top}px`, left: `${lr.left}px`, width: `${lr.width}px` });
        return index;
    }

    function beenden(abbrechen) {
        if (!zug) return;
        const { laeuft, komponente, zeile, index } = zug;
        if (laeuft) {
            zug.geist.remove();
            marke.remove();
            zeile.classList.remove("zuordnungsliste__zeile--gezogen");
            document.body.classList.remove("zuordnung-zieht");
            gezogenUm = Date.now();
            const pk = zeile.dataset.pk;
            const eintrag = komponente.rows.find((z) => String(z.pk) === pk);
            const bisher = komponente.rows.indexOf(eintrag);
            if (!abbrechen && eintrag && index !== bisher) {
                komponente.verschieben(eintrag, index + 1);
            }
        }
        zug = null;
    }

    document.addEventListener("pointerdown", (event) => {
        const griff = event.target.closest("[data-zuordnungsliste] [data-griff]");
        if (!griff || event.button > 0) return;
        const wurzel = griff.closest("[data-zuordnungsliste]");
        zug = {
            komponente: Alpine.$data(wurzel),
            liste: wurzel.querySelector(".zuordnungsliste__liste"),
            zeile: griff.closest(".zuordnungsliste__zeile"),
            startX: event.clientX,
            startY: event.clientY,
            laeuft: false,
            index: null,
        };
        griff.setPointerCapture(event.pointerId);
    });

    document.addEventListener("pointermove", (event) => {
        if (!zug) return;
        if (!zug.laeuft) {
            if (Math.hypot(event.clientX - zug.startX, event.clientY - zug.startY) < 4) return;
            zug.laeuft = true;
            const r = zug.zeile.getBoundingClientRect();
            zug.geist = zug.zeile.cloneNode(true);
            // Der Klon trägt Alpine-Attribute ohne x-for-Kontext.
            zug.geist.setAttribute("x-ignore", "");
            zug.geist.classList.add("zuordnung-geist");
            zug.geist.style.width = `${r.width}px`;
            zug.dy = event.clientY - r.top;
            zug.links = r.left;
            document.body.append(zug.geist, marke);
            zug.zeile.classList.add("zuordnungsliste__zeile--gezogen");
            document.body.classList.add("zuordnung-zieht");
        }
        zug.geist.style.transform = `translate(${zug.links}px, ${event.clientY - zug.dy}px)`;
        zug.index = zielIndex(event.clientY);
        // Am Fensterrand mitscrollen, damit lange Listen erreichbar bleiben.
        if (event.clientY < 60) window.scrollBy(0, -12);
        else if (event.clientY > innerHeight - 60) window.scrollBy(0, 12);
    });

    document.addEventListener("pointerup", () => beenden(false));
    document.addEventListener("pointercancel", () => beenden(true));
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") beenden(true);
    });
    // Beim Ziehen markiert der Browser sonst Text.
    document.addEventListener("selectstart", (event) => zug && event.preventDefault());
    // Der Klick nach dem Loslassen gehört zum Ziehen, nicht zu einem Knopf.
    window.addEventListener(
        "click",
        (event) => {
            if (Date.now() - gezogenUm < 100) {
                event.stopImmediatePropagation();
                event.preventDefault();
            }
        },
        true
    );
})();
