import assert from "node:assert/strict";
import { test } from "node:test";
import { runIteration } from "./iteration.mts";
import { FakeAgents, FakeRepo, FakeTracker, ticket } from "./testing/fakes.mts";

function setup() {
  const tracker = new FakeTracker();
  const repo = new FakeRepo("main");
  const agents = new FakeAgents(repo);
  const run = () =>
    runIteration({ tracker, repo, agents, targetBranch: "main", log: () => {} });
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
    { reviewed: ["7"], merged: [["sandcastle/issue-7"]], open: false },
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
  repo.createBranch("sandcastle/issue-7", "main");
  repo.commit("sandcastle/issue-7");
  agents.implementers.set("7", { commits: 0, completed: true });

  await run();

  assert.deepEqual(agents.mergedWith, [["sandcastle/issue-7"]]);
});

test("ein Branch ohne Arbeit wird weder reviewt noch gemergt", async () => {
  const { tracker, agents, run } = setup();
  tracker.addTicket(ticket(7));
  agents.implementers.set("7", { commits: 0, completed: true });

  await run();

  assert.deepEqual({ reviewed: agents.reviewed, merged: agents.mergedWith }, { reviewed: [], merged: [] });
});

test("die Spec wird geschlossen, sobald ihr letztes Sub-Issue gemergt ist", async () => {
  const { tracker, agents, run } = setup();
  tracker.addSpec(30);
  tracker.addTicket(ticket(31), { parent: 30 });
  tracker.addTicket(ticket(32), { parent: 30 });
  agents.deferred.add("32");

  await run();
  const afterFirst = tracker.isOpen(30);
  agents.deferred.clear();
  await run();

  assert.deepEqual({ afterFirst, afterSecond: tracker.isOpen(30) }, { afterFirst: true, afterSecond: false });
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
