// PROTOTYPE – Variantenleiste (#287, #290): ←/→ wechseln die Variante.
document.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    if (event.target.matches("input, textarea, select, [contenteditable]")) return;
    const leiste = document.querySelector(".prototype-switcher");
    const ziel = leiste.dataset[event.key === "ArrowLeft" ? "vorherige" : "naechste"];
    window.location.search = `?variant=${ziel}`;
});
