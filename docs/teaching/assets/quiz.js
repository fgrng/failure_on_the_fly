/* Wiederverwendbares Quiz-Widget für alle Lektionen.
 *
 * Markup:
 *   <div class="quiz" data-answer="b" data-why="Begründung nach dem Klick.">
 *     <p class="q">Frage?</p>
 *     <button data-opt="a">Antworttext</button>
 *     ...
 *   </div>
 *
 * Antwortoptionen sollten möglichst gleich lang sein — Länge darf kein
 * Hinweis auf die Lösung sein.
 */
(function () {
  const style = document.createElement("style");
  style.textContent = `
    .quiz { margin: 1.8rem 0; max-width: 38rem; }
    .quiz .q { font-weight: 500; margin: 0 0 0.7rem; }
    .quiz button { display: block; width: 100%; text-align: left; margin: 0.35rem 0; }
    .quiz button.right { border-color: var(--ok); background: #eef5f0; color: var(--ok); }
    .quiz button.wrong { border-color: var(--accent); background: var(--accent-soft); color: var(--accent); }
    .quiz .why { margin: 0.7rem 0 0; font-size: 0.9rem; color: var(--ink-soft); display: none; }
    .quiz.done .why { display: block; }
    .quiz .score { font-size: 0.85rem; color: var(--ink-soft); }
    .reveal { margin: 0.6rem 0 0; font-size: 0.92rem; display: none; }
    .reveal.open { display: block; }
  `;
  document.head.appendChild(style);

  document.querySelectorAll(".quiz").forEach((quiz) => {
    const answer = quiz.dataset.answer;
    const why = document.createElement("p");
    why.className = "why";
    why.textContent = quiz.dataset.why || "";
    quiz.appendChild(why);

    quiz.querySelectorAll("button[data-opt]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const correct = btn.dataset.opt === answer;
        btn.classList.add(correct ? "right" : "wrong");
        if (!correct) {
          // Richtige Option mitzeigen: Feedback soll sofort lernwirksam sein.
          const right = quiz.querySelector(`button[data-opt="${answer}"]`);
          if (right) right.classList.add("right");
        }
        quiz.classList.add("done");
        quiz.querySelectorAll("button[data-opt]").forEach((b) => (b.disabled = true));
      });
    });
  });

  // Musterlösungen erst nach eigenem Versuch aufdecken.
  document.querySelectorAll("[data-reveal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.dataset.reveal);
      if (!target) return;
      target.classList.toggle("open");
      btn.textContent = target.classList.contains("open")
        ? "Musterlösung ausblenden"
        : "Musterlösung ansehen";
    });
  });
})();
