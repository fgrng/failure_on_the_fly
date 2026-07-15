# Image Generation (`agy`)

How to (re)generate the framing-story illustrations (*Rahmenhandlung*) that live in
`static/images/session/`. The binding **style rules** are in
[`docs/bildsprache/README.md`](../bildsprache/README.md) — this file only covers the *tooling*.

Images are produced with the **`agy`** CLI (Antigravity, Google), which drives an internal
image tool (**Nano Banana**). Generation runs over the user's Google login and is
**quota-limited** (reset ~1.5 h). Treat every real generation as expensive.

## Model selection — read this first

`agy models` lists **agent/text driver models**, *not* image models:

```
Gemini 3.5 Flash (Low|Medium|High)   Gemini 3.1 Pro (Low|High)
Claude Sonnet 4.6   Claude Opus 4.6   GPT-OSS 120B
```

The `--model` flag picks the LLM that *drives* the CLI. The **image model (Nano Banana) is
fixed and cannot be downgraded** — it is the quota-limited resource, and there is no cheaper
test tier for it. So:

- **Every image costs image quota**, regardless of driver model. You cannot "test-generate cheap."
- For test/iteration runs, use the **weakest driver** to keep agent overhead minimal:
  `--model "Gemini 3.5 Flash (Low)"`.
- To validate auth + the agent loop **without** spending image quota, run a trivial text
  prompt first (e.g. `-p "Antworte nur mit: BEREIT"`).

## The workflow

```bash
# 1. Generate (the only step that costs image quota)
agy --dangerously-skip-permissions --model "Gemini 3.5 Flash (Low)" \
    --print-timeout 12m --add-dir docs/bildsprache/originale \
    -p "<prompt> ... speichere als PNG unter docs/bildsprache/originale/<name>-v2.png"

# 2. Copy the file out of agy's sandbox into the repo  (MANDATORY — see gotcha below)
cp ~/.gemini/antigravity-cli/scratch/docs/bildsprache/originale/<name>-v2.png \
   docs/bildsprache/originale/<name>-v2.png

# 3. Verify the alpha channel (for transparent output)
identify -verbose docs/bildsprache/originale/<name>-v2.png | rg -i "alpha|color_type"
#   expect: color_type 6 (RGBA), Type: TrueColorAlpha

# 4. Downscale + embed (WebP carries alpha). Originals stay 1024²; sessions use 800².
convert docs/bildsprache/originale/<name>-v2.png -resize 800x800 \
        static/images/session/<zielname>.webp

# 5. Render in the running session and eyeball it (see the `run` skill).
```

Only step 1 spends quota. Steps 2–5 are free — iterate on them without re-generating.

The three session images and their originals:

| Session WebP (`static/images/session/`) | Original (`docs/bildsprache/originale/`) | Beat |
| --- | --- | --- |
| `rahmenhandlung-einstieg.webp` | `hospitation-einstieg-b.png` | Hospitation / Einstieg |
| `gespraechsanlass.webp`        | `hospitation-pov-a.png`      | Gesprächsanlass |
| `rahmenhandlung-debrief.webp`  | `szene-debrief.png`          | Debrief |

Generate to a `-v2` filename first so the live set is untouched until you've compared results.

## Gotchas

- **`agy` writes to its own sandbox, not the repo.** Despite `--add-dir`, saved files land under
  `~/.gemini/antigravity-cli/scratch/<the path you asked for>`. **Always `cp` the result into the
  repo** (step 2). If a file "doesn't exist" after a successful run, look in the scratch dir.
- **Default `--print-timeout` (5 min) is too short.** Image generation through the agent loop
  regularly exceeds it; the run exits with `Error: timeout waiting for response` and **no file**.
  Use `--print-timeout 12m`.
- **`--dangerously-skip-permissions`** is required for headless runs — otherwise `agy` blocks on
  interactive permission prompts.
- **Long runs go to the background.** In this harness the foreground command is moved to a
  background task after ~2 min; wait for the completion notification, then check the output file
  and the scratch dir.
- **Auth is interactive.** `agy` uses the user's Google login; if auth fails, the *human* must
  re-authenticate interactively (suggest they run the login step via a `!` command). An agent
  cannot complete the login headlessly.

## Transparent backgrounds

The session illustrations use a **transparent** background so the watercolour sits on the page.

- **Ask the model for a real alpha channel** in the prompt (e.g. *"save as PNG with a genuinely
  transparent background, real alpha channel, no white fill"*). Nano Banana (via `agy`) produces
  proper RGBA with soft partial-alpha edges and no white halos. **IMPORTANT:** Ask the model to "auf reinweißem Grund malen, kein Schachbrett" (paint on a pure white background, no checkerboard). Otherwise, the image generation might bake a fake transparency checkerboard pattern directly into the image.
- **Do NOT freistellen a paper-ground image post-hoc.** Naive flood-fill background removal on the
  existing warm-paper originals produces white halos around the soft watercolour fades and leaves
  white islands in enclosed light regions. Transparency must come from generation.
- Verify with `identify` (step 3). WebP (step 4) preserves the alpha channel.
- Note the tension with the style rules: the established look specifies a *warm paper ground*
  ([`docs/bildsprache/README.md`](../bildsprache/README.md)); transparent output overrides that on
  purpose. Keep the two decisions consistent across the whole set.
