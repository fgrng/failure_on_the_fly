function wechseln(richtung) {
    const switcher = document.querySelector(".prototype-switcher");
    window.location.search = `?variant=${switcher.dataset[richtung]}`;
}

document.addEventListener("keydown", (event) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    if (event.target.matches("input, textarea, [contenteditable]")) return;
    wechseln(event.key === "ArrowLeft" ? "vorherige" : "naechste");
});

document.querySelector(".prototype-switcher__zurueck")?.addEventListener("click", (event) => {
    event.preventDefault();
    wechseln("vorherige");
});

document.querySelector(".prototype-switcher__vor")?.addEventListener("click", (event) => {
    event.preventDefault();
    wechseln("naechste");
});
