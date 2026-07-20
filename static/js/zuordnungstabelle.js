function zuordnungstabelle({
    datenId,
    positionsId,
    sortierSchluessel,
    suchSchluessel,
}) {
    return {
        rows: JSON.parse(document.getElementById(datenId).textContent),
        suchbegriff: "",
        sortierSchluessel,
        sortierRichtung: 1,
        suchSchluessel,

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
                        this.suchSchluessel.map((schluessel) => zeile[schluessel])
                            .join(" ")
                            .toLowerCase()
                            .includes(suche)
                )
                .sort((a, b) => {
                    const links = (a[this.sortierSchluessel] ?? "")
                        .toString()
                        .toLowerCase();
                    const rechts = (b[this.sortierSchluessel] ?? "")
                        .toString()
                        .toLowerCase();
                    return (
                        links.localeCompare(rechts, "de", { numeric: true }) *
                        this.sortierRichtung
                    );
                });
        },
        sortiere(schluessel) {
            if (this.sortierSchluessel === schluessel) {
                this.sortierRichtung *= -1;
            } else {
                this.sortierSchluessel = schluessel;
                this.sortierRichtung = 1;
            }
        },
        pfeilKlasse(schluessel) {
            if (this.sortierSchluessel !== schluessel) {
                return "";
            }
            return this.sortierRichtung === 1
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
