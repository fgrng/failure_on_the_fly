import assert from "node:assert/strict";
import { test } from "node:test";
import { runIteration, updateIntegrationBranches } from "./iteration.mts";
import { FakeAgents, FakeRepo, FakeTracker, ticket } from "./testing/fakes.mts";

function setup(options: { spec?: number } = {}) {
  const tracker = new FakeTracker();
  const repo = new FakeRepo("main");
  const agents = new FakeAgents(repo);
  const run = () =>
    runIteration({ tracker, repo, agents, log: () => {}, ...options });
  return { tracker, repo, agents, run };
}

test("der Planner bekommt die Tickets aus dem Tracker-Filter", async () => {
  const { tracker, agents, run } = setup();
  tracker.addTicket(ticket(7, "Erstes"));
  tracker.addTicket(ticket(9, "Zweites"));

  await run();

  assert.deepEqual(
    agents.plannedWith.map((tickets) => tickets.map((t) => t.number)),
    [[7, 9]],
  );
});

test("ein fertiges Ticket wird reviewt, gemergt und geschlossen", async () => {
  const { tracker, agents, run } = setup();
  tracker.addTicket(ticket(7));

  await run();

  assert.deepEqual(
    { reviewed: agents.reviewed, merged: agents.mergedWith, open: tracker.isOpen(7) },
    {
      reviewed: ["7"],
      merged: [{ into: "sandcastle/standalone", branches: ["sandcastle/issue-7"] }],
      open: false,
    },
  );
});

test("ohne Abschlusssignal gibt es kein Review und keinen Merge, das Ticket bleibt offen", async () => {
  const { tracker, agents, run } = setup();
  tracker.addTicket(ticket(7));
  agents.implementers.set("7", { commits: 2, completed: false });

  await run();

  assert.deepEqual(
    { reviewed: agents.reviewed, merged: agents.mergedWith, open: tracker.isOpen(7) },
    { reviewed: [], merged: [], open: true },
  );
});

test("geschlossen werden nur Tickets, deren Branch nachweislich gemergt ist", async () => {
  const { tracker, agents, run } = setup();
  tracker.addTicket(ticket(7));
  tracker.addTicket(ticket(8));
  agents.unmergeable.add("sandcastle/issue-8");

  await run();

  assert.deepEqual(
    tracker.closed.map((c) => c.number),
    [7],
  );
});

test("ein fertiger Branch aus einer früheren Iteration wird ohne neue Commits gemergt", async () => {
  const { tracker, repo, agents, run } = setup();
  tracker.addTicket(ticket(7));
  await repo.createBranch("sandcastle/standalone", "main");
  await repo.createBranch("sandcastle/issue-7", "sandcastle/standalone");
  repo.commit("sandcastle/issue-7");
  agents.implementers.set("7", { commits: 0, completed: true });

  await run();

  assert.deepEqual(agents.mergedWith, [
    { into: "sandcastle/standalone", branches: ["sandcastle/issue-7"] },
  ]);
});

test("ein Branch ohne Arbeit wird weder reviewt noch gemergt", async () => {
  const { tracker, agents, run } = setup();
  tracker.addTicket(ticket(7));
  agents.implementers.set("7", { commits: 0, completed: true });

  await run();

  assert.deepEqual({ reviewed: agents.reviewed, merged: agents.mergedWith }, { reviewed: [], merged: [] });
});

test("Tickets einer Spec werden nach dem Merge in spec/<n> geschlossen, die Spec bleibt offen", async () => {
  const { tracker, agents, run } = setup();
  tracker.addSpec(30);
  tracker.addTicket(ticket(31), { parent: 30 });
  tracker.addTicket(ticket(32), { parent: 30 });
  agents.deferred.add("32");

  await run();
  agents.deferred.clear();
  await run();

  assert.deepEqual(
    { closed: tracker.closed.map((c) => c.number), specOpen: tracker.isOpen(30) },
    { closed: [31, 32], specOpen: true },
  );
});

test("ohne Tickets meldet die Iteration einen leeren Backlog", async () => {
  const { run } = setup();

  assert.deepEqual(await run(), { planned: 0 });
});

test("ein Fehler bei einem Ticket hält die übrigen nicht auf", async () => {
  const { tracker, agents, run } = setup();
  tracker.addTicket(ticket(7));
  tracker.addTicket(ticket(8));
  agents.failing.add("7");

  await run();

  assert.deepEqual(tracker.closed.map((c) => c.number), [8]);
});

test("ein Ticket einer Spec zweigt von spec/<n> ab, das von main entsteht, und wird dorthin gemergt", async () => {
  const { tracker, repo, agents, run } = setup();
  repo.commit("main");
  tracker.addSpec(30);
  tracker.addTicket(ticket(31), { parent: 30 });

  await run();

  assert.deepEqual(
    {
      startedFrom: agents.startedFrom,
      merged: agents.mergedWith,
      specHasMain: await repo.contains("spec/30", "main"),
      specHasTicket: await repo.contains("spec/30", "sandcastle/issue-31"),
      mainHasTicket: await repo.contains("main", "sandcastle/issue-31"),
    },
    {
      startedFrom: [{ id: "31", base: "spec/30" }],
      merged: [{ into: "spec/30", branches: ["sandcastle/issue-31"] }],
      specHasMain: true,
      specHasTicket: true,
      mainHasTicket: false,
    },
  );
});

test("je Integrations-Branch läuft ein eigener Merger", async () => {
  const { tracker, agents, run } = setup();
  tracker.addSpec(30);
  tracker.addSpec(40);
  tracker.addTicket(ticket(7));
  tracker.addTicket(ticket(31), { parent: 30 });
  tracker.addTicket(ticket(41), { parent: 40 });
  tracker.addTicket(ticket(32), { parent: 30 });

  await run();

  assert.deepEqual(
    new Map(agents.mergedWith.map((m) => [m.into, m.branches.toSorted()])),
    new Map([
      ["sandcastle/standalone", ["sandcastle/issue-7"]],
      ["spec/30", ["sandcastle/issue-31", "sandcastle/issue-32"]],
      ["spec/40", ["sandcastle/issue-41"]],
    ]),
  );
});

function setupUpdate() {
  const { tracker, repo, agents } = setup();
  const update = () => updateIntegrationBranches({ tracker, repo, agents, log: () => {} });
  return { tracker, repo, agents, update };
}

test("zu Laufbeginn bekommt ein Spec-Branch main sauber hineingemergt, ohne Agent", async () => {
  const { tracker, repo, agents, update } = setupUpdate();
  tracker.addSpec(30);
  await repo.createBranch("spec/30", "main");
  repo.commit("main");

  await update();

  assert.deepEqual(
    { specHasMain: await repo.contains("spec/30", "main"), merged: agents.mergedWith },
    { specHasMain: true, merged: [] },
  );
});

test("bei einem Konflikt mit main löst der Merger auf genau diesem Branch auf", async () => {
  const { tracker, repo, agents, update } = setupUpdate();
  tracker.addSpec(30);
  await repo.createBranch("spec/30", "main");
  repo.commit("main");
  repo.conflicting.add("spec/30");

  await update();

  assert.deepEqual(
    { specHasMain: await repo.contains("spec/30", "main"), merged: agents.mergedWith },
    { specHasMain: true, merged: [{ into: "spec/30", branches: ["main"] }] },
  );
});

test("scheitert die Auflösung, bleibt der Branch unverändert und der Lauf meldet ihn", async () => {
  const { tracker, repo, agents, update } = setupUpdate();
  tracker.addSpec(30);
  await repo.createBranch("spec/30", "main");
  repo.commit("spec/30");
  repo.commit("main");
  repo.conflicting.add("spec/30");
  agents.unmergeable.add("main");
  const before = await repo.head("spec/30");

  const result = await update();

  assert.deepEqual(
    { head: await repo.head("spec/30"), failed: result.failed },
    { head: before, failed: ["spec/30"] },
  );
});

test("der Branch einer geschlossenen Spec bekommt main nicht mehr hineingemergt", async () => {
  const { tracker, repo, update } = setupUpdate();
  tracker.addSpec(30, { open: false });
  await repo.createBranch("spec/30", "main");
  repo.commit("main");

  await update();

  assert.equal(await repo.contains("spec/30", "main"), false);
});

test("ein bestehender sandcastle/standalone bekommt main hineingemergt", async () => {
  const { repo, update } = setupUpdate();
  await repo.createBranch("sandcastle/standalone", "main");
  repo.commit("main");

  await update();

  assert.equal(await repo.contains("sandcastle/standalone", "main"), true);
});

test("mit --spec <n> plant der Lauf nur die Sub-Issues von #n", async () => {
  const { tracker, agents, run } = setup({ spec: 30 });
  tracker.addSpec(30);
  tracker.addSpec(40);
  tracker.addTicket(ticket(7));
  tracker.addTicket(ticket(31), { parent: 30 });
  tracker.addTicket(ticket(41), { parent: 40 });

  await run();

  assert.deepEqual(
    agents.plannedWith.map((tickets) => tickets.map((t) => t.number)),
    [[31]],
  );
});

test("ein geschlossener Blocker aus derselben Spec gibt sein Ticket frei", async () => {
  const { tracker, agents, run } = setup();
  tracker.addSpec(30);
  tracker.addTicket(ticket(31), { parent: 30 });
  tracker.addTicket(ticket(32), { parent: 30, blockedBy: [31] });

  await run();
  await run();

  assert.deepEqual(
    agents.plannedWith.map((tickets) => tickets.map((t) => t.number)),
    [[31], [32]],
  );
});

test("ein geschlossener Blocker aus einer anderen Spec hält sein Ticket zurück, bis er auf main liegt", async () => {
  const { tracker, agents, run } = setup();
  tracker.addSpec(30);
  tracker.addSpec(40);
  tracker.addTicket(ticket(31), { parent: 30 });
  tracker.addTicket(ticket(41), { parent: 40, blockedBy: [31] });

  await run();
  await run();

  assert.deepEqual(
    agents.plannedWith.map((tickets) => tickets.map((t) => t.number)),
    [[31], []],
  );
});

test("ein Blocker aus einer anderen Spec gibt sein Ticket frei, sobald er auf main liegt", async () => {
  const { tracker, repo, agents, run } = setup();
  tracker.addSpec(30);
  tracker.addSpec(40);
  tracker.addTicket(ticket(31), { parent: 30 });
  tracker.addTicket(ticket(41), { parent: 40, blockedBy: [31] });

  await run();
  repo.merge("spec/30", "main");
  await run();

  assert.deepEqual(
    agents.plannedWith.map((tickets) => tickets.map((t) => t.number)),
    [[31], [41]],
  );
});

test("ein Blocker aus einer geschlossenen Spec gilt als erledigt, auch ohne Sandcastle-Branch", async () => {
  const { tracker, agents, run } = setup();
  tracker.addSpec(20, { open: false });
  tracker.addSpec(40);
  tracker.addTicket(ticket(21), { parent: 20 });
  await tracker.close(21, "von Hand umgesetzt");
  tracker.addTicket(ticket(41), { parent: 40, blockedBy: [21] });

  await run();

  assert.deepEqual(
    agents.plannedWith.map((tickets) => tickets.map((t) => t.number)),
    [[41]],
  );
});

test("ein Ticket ohne Spec zweigt von sandcastle/standalone ab, das von main entsteht, und wird dorthin gemergt", async () => {
  const { tracker, repo, agents, run } = setup();
  repo.commit("main");
  tracker.addTicket(ticket(7));

  await run();

  assert.deepEqual(
    {
      startedFrom: agents.startedFrom,
      standaloneHasMain: await repo.contains("sandcastle/standalone", "main"),
      standaloneHasTicket: await repo.contains("sandcastle/standalone", "sandcastle/issue-7"),
      mainHasTicket: await repo.contains("main", "sandcastle/issue-7"),
    },
    {
      startedFrom: [{ id: "7", base: "sandcastle/standalone" }],
      standaloneHasMain: true,
      standaloneHasTicket: true,
      mainHasTicket: false,
    },
  );
});

test("neue Commits auf sandcastle/standalone werden gepusht und bekommen einen PR nach main", async () => {
  const { tracker, repo, run } = setup();
  tracker.addTicket(ticket(7, "Tippfehler beheben"));

  await run();

  assert.deepEqual(
    {
      pushed: await repo.isPushed("sandcastle/standalone"),
      prs: tracker.pullRequests.map(({ head, base, state }) => ({ head, base, state })),
      mentionsTicket: tracker.pullRequests[0]?.body.includes("#7: Tippfehler beheben"),
    },
    {
      pushed: true,
      prs: [{ head: "sandcastle/standalone", base: "main", state: "open" }],
      mentionsTicket: true,
    },
  );
});

test("ein offener Standalone-PR wird aktualisiert statt neu angelegt", async () => {
  const { tracker, repo, run } = setup();
  tracker.addTicket(ticket(7, "Erstes"));
  await run();
  tracker.addTicket(ticket(8, "Zweites"));

  await run();

  assert.deepEqual(
    {
      pushed: await repo.isPushed("sandcastle/standalone"),
      prs: tracker.pullRequests.map((pr) => pr.body.split("\n").filter((l) => l.startsWith("- "))),
    },
    { pushed: true, prs: [["- #7: Erstes", "- #8: Zweites"]] },
  );
});

test("ohne neue Commits auf sandcastle/standalone gibt es weder Push noch PR", async () => {
  const { tracker, repo, agents, run } = setup();
  tracker.addSpec(30);
  tracker.addTicket(ticket(31), { parent: 30 });
  tracker.addTicket(ticket(7));
  agents.implementers.set("7", { commits: 1, completed: false });

  await run();

  assert.deepEqual(
    { pushed: await repo.isPushed("sandcastle/standalone"), prs: tracker.pullRequests },
    { pushed: false, prs: [] },
  );
});

test("nach dem Merge des Standalone-PRs zweigt sandcastle/standalone im nächsten Lauf frisch von main ab", async () => {
  const { tracker, repo, agents, run } = setup();
  tracker.addTicket(ticket(7, "Erstes"));
  await run();
  tracker.mergePullRequest(tracker.pullRequests[0]!.number);
  tracker.addTicket(ticket(8, "Zweites"));

  await updateIntegrationBranches({ tracker, repo, agents, log: () => {} });
  await run();

  assert.deepEqual(
    {
      hasOldTicket: await repo.contains("sandcastle/standalone", "sandcastle/issue-7"),
      hasNewTicket: await repo.contains("sandcastle/standalone", "sandcastle/issue-8"),
      prs: tracker.pullRequests.map((pr) => ({
        state: pr.state,
        tickets: pr.body.split("\n").filter((l) => l.startsWith("- ")),
      })),
    },
    {
      hasOldTicket: false,
      hasNewTicket: true,
      prs: [
        { state: "merged", tickets: ["- #7: Erstes"] },
        { state: "open", tickets: ["- #8: Zweites"] },
      ],
    },
  );
});

test("scheitert der Push nach einem Neustart, gehen die neuen Commits nicht verloren", async () => {
  const { tracker, repo, agents, run } = setup();
  const update = () => updateIntegrationBranches({ tracker, repo, agents, log: () => {} });
  tracker.addTicket(ticket(7));
  await run();
  tracker.mergePullRequest(tracker.pullRequests[0]!.number);
  tracker.addTicket(ticket(8));
  repo.pushFails = true;
  await update();
  await run();
  repo.pushFails = false;

  await update();
  await run();

  assert.deepEqual(
    {
      hasTicket: await repo.contains("sandcastle/standalone", "sandcastle/issue-8"),
      pushed: await repo.isPushed("sandcastle/standalone"),
      prStates: tracker.pullRequests.map((pr) => pr.state),
    },
    { hasTicket: true, pushed: true, prStates: ["merged", "open"] },
  );
});

test("nach dem Merge des Standalone-PRs entsteht ohne neue Tickets kein weiterer PR, auch wenn main weiter ist", async () => {
  const { tracker, repo, agents, run } = setup();
  const update = () => updateIntegrationBranches({ tracker, repo, agents, log: () => {} });
  tracker.addTicket(ticket(7));
  await update();
  await run();
  tracker.mergePullRequest(tracker.pullRequests[0]!.number);
  repo.merge("sandcastle/standalone", "main");
  repo.commit("main");

  await update();
  await run();

  assert.deepEqual(
    tracker.pullRequests.map((pr) => pr.state),
    ["merged"],
  );
});
