function zuordnungstabelle({ datenId, positionsId, sortierschluessel }) {
    return {
        rows: JSON.parse(document.getElementById(datenId).textContent),
        suchbegriff: "",
        sortierschluessel,
        sortierrichtung: 1,

        init() {
            document.addEventListener("zuordnung:aktualisiert", (event) => {
                this.rows = event.detail[datenId];
            });
        },
        get sichtbareZeilen() {
            const suche = this.suchbegriff.trim().toLowerCase();
            return this.rows
                .filter(
                    (zeile) =>
                        !suche ||
                        [zeile.label, zeile.fach, zeile.thema]
                            .join(" ")
                            .toLowerCase()
                            .includes(suche)
                )
                .sort((a, b) => {
                    const links = (a[this.sortierschluessel] ?? "")
                        .toString()
                        .toLowerCase();
                    const rechts = (b[this.sortierschluessel] ?? "")
                        .toString()
                        .toLowerCase();
                    return (
                        links.localeCompare(rechts, "de", { numeric: true }) *
                        this.sortierrichtung
                    );
                });
        },
        sortiere(schluessel) {
            if (this.sortierschluessel === schluessel) {
                this.sortierrichtung *= -1;
            } else {
                this.sortierschluessel = schluessel;
                this.sortierrichtung = 1;
            }
        },
        pfeilKlasse(schluessel) {
            if (this.sortierschluessel !== schluessel) {
                return "";
            }
            return this.sortierrichtung === 1
                ? "table__sort-arrow--auf"
                : "table__sort-arrow--ab";
        },
        async umschalten(url) {
            const csrfToken = document.querySelector(
                "[name=csrfmiddlewaretoken]"
            ).value;
            const formData = new FormData();
            formData.append("csrfmiddlewaretoken", csrfToken);
            const response = await fetch(url, { method: "POST", body: formData });
            const doc = new DOMParser().parseFromString(
                await response.text(),
                "text/html"
            );
            const aktualisierteDaten = Object.fromEntries(
                Array.from(
                    document.querySelectorAll("[data-zuordnung-daten] script")
                ).map((element) => [
                    element.id,
                    JSON.parse(doc.getElementById(element.id).textContent),
                ])
            );
            document.dispatchEvent(
                new CustomEvent("zuordnung:aktualisiert", { detail: aktualisierteDaten })
            );

            if (positionsId) {
                const neuePositionen = doc.getElementById(positionsId);
                const aktuellePositionen = document.getElementById(positionsId);
                if (neuePositionen && aktuellePositionen) {
                    aktuellePositionen.innerHTML = neuePositionen.innerHTML;
                }
            }
        },
    };
}
