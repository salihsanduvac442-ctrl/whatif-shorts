# What If Shorts — daily challenge (Oct 26, 2026 → Feb 1, 2027, then ongoing)

Oct 26 → Jan 1 is the trial period; the calendar runs to Feb 1 (day 99) and the channel keeps going at least until
100 Shorts and beyond. When the calendar runs out, append the next day yourself: keep the rotation
money → tiny army → body → weird animal, take topics from `backlog.json` (remove them there) or write new ones in the
same style (never repeat a title), then produce as usual.

One 3D "What if...?" YouTube Short per day, published through Metricool.
`calendar.json` holds one topic per day (day, date, title, category, status). From day 3, odd days are body / extreme-science
topics, rotating daily from 2026-10-28: money → tiny army → body → weird animal (rare accidents take a slot when a
series runs out). Christmas / New Year specials are slotted in on fixed dates (Nov 1 test, Dec 6, 13, 20, 24, 25, 31,
Jan 1). Always go by the `category` field of the entry.

## Christmas / New Year specials (categories `christmas`, `new year special`)
Added 2026-10-27. Same format; snowy night diorama, warm lights, cosy colors. Real numbers again (ornament weight,
how many homes Santa would visit and how fast he'd have to go, bulb wattage, snow density...), playful tone.
- Santa is the generic folk figure (red suit, white beard) in our own style — no brand-specific look and no named
  trademarked characters (e.g. don't name or copy a famous red-nosed reindeer); reindeer are generic.

## Tiny army (category `tiny army`)
Added 2026-10-27. "What if 1 billion <tiny animal> ...?" — the smallest animals, multiplied until they matter.
- Start from ONE animal with its real numbers (mass in mg, bite volume, lift power, light output, speed), then
  multiply live on screen with a counter badge (1 → 1,000 → 1 million → 1 billion) and show the total next to
  something familiar (car, house, blue whale, stadium). Real examples help: locust swarms really reach billions.
- Cute cartoon insects / krill / plankton, never scary-realistic; no gore. For mosquitoes etc. show
  "why it's dangerous" in simple terms, not injury detail.

## Money scale (category `money`)
Added 2026-10-27. "How big / heavy / long is this much money?" — a counter badge climbs ($1K → $10K → $1M → $1B)
while stacks of cartoon bills / pallets / piles grow next to a person, house, truck, stadium for scale.
- Use real, checked numbers. US bills: ~1 g each, 15.6 cm long, ~0.11 mm thick. So in $100 bills:
  $1,000 ≈ 10 g, $100K ≈ 1 kg, $1M ≈ 10 kg, $1B ≈ 10 tonnes (in $1 bills it is 100x heavier/longer).
  A US penny weighs 2.5 g.
- For "a billion dollars of X" (rice, water, gold, trees) look up a current typical price with WebSearch on the
  day, say "about", and give the result in a relatable unit (Olympic pools, trucks, football fields, Earth laps).
  Gold price changes daily: always search it.
- Bills are generic cartoon money (no real banknote designs, portraits or serial numbers).

## Rare accidents (category `rare accident`) and weird animals (category `weird animal`)
Added 2026-10-27, same format and safety rules as the body series below.
- Rare accidents: real but very unlikely events (meteorite strikes, plane window failures, ball lightning,
  molasses flood, limnic gas eruptions...). Give the real odds or the real number of known cases, what happens
  physically, and how people survived. Never name or depict real victims; no gore — cartoon diorama only.
- Weird animals: "What if you had <animal>'s superpower?" Show the real animal's ability with real numbers
  (speed, force, temperature it survives), then scale it to a human in the backyard diorama. Invent your own
  cartoon animals — never copy known characters or mascots.

## Format (keep it identical every day)
- 1080x1920, 30 fps, **25–28 s, never shorter than 25 s**.
- **Pace = 1.5x the day-1 cut** (videos/2026-10-26-dig-forever.mp4): same length, but 1.5x more beats.
  Script has 15–18 very short lines (4–9 words each), a new visual beat on screen every ~1.5 s,
  and the camera never holds still (fast dolly / push-in / orbit / descent, whip moves between beats).
  Hook question in the first 1.5 s, no intro.
- Stylized low-poly 3D in Blender (Cycles), bright cartoon colors, cross-section / diorama look
  (reference: viral "What if" house + soil cut-away shorts).
- **Clarity rules (Salih, 2026-10-27):** keep this exact design, but every shape and text must read clearly.
  `pipeline/render.py` applies `pipeline/clarity.py` automatically: bold dark outline on every shape, and
  **nothing see-through on screen** — transparent / glass / water materials are made opaque and light beams,
  halos and light cones become solid glowing bars. In new scenes don't use `alpha < 1` or transmission at all;
  show beams as solid glowing bars/rings. Captions and the top badge are solid (thick stroke, opaque pill).
  The "v2" look (`look_v2.py`, `grade.py`, `compose_v2.py`) was tried and rejected: don't use it.
- Narration: Kokoro `am_michael`, speed 1.45 (tts.py default), last line is a question
  to drive comments ("So... would you ...?"). Do not push speech faster than ~1.5 — it stops being clear;
  get the extra pace from more lines and more on-screen events instead.
- One-word pop captions centre screen, numbers + key nouns in yellow; a pill badge at the top
  counting the key metric (depth, distance, size, temperature, time...).
- Dynamic transitions on every line (punch zoom, shake, flash, whoosh/boom) and a 128 bpm bed — all done by `pipeline/compose.py`.

## Body / extreme-science episodes (category `body`, every other day from day 3)
Added 2026-10-27 because "what happens to your body if..." facts get a lot of views. Same format as above, plus:
- **Facts first.** Real physiology, in order of what happens (seconds → minutes → hours). Use real numbers
  (temperatures, seconds, distances) and hedge where it varies by person ("for most people", "can").
  Bust myths when the truth is surprising (e.g. tiny IV bubbles are usually harmless).
- **Stay YouTube-safe.** No gore or realistic injuries: stylized cartoon cut-away bodies, glowing organs,
  "inside the vein / lungs / brain" fly-throughs, cells and blood as colorful low-poly shapes.
  Never give doses, amounts or step-by-step methods that could be used to hurt someone; frame dangerous
  topics as "why it's dangerous and what doctors do". End on a light, curious question.
- Visual beats: zoom from the person into the body part, show the process with simple shapes
  (bubbles, red cells, oxygen dots, heat glow), a counter badge for the key metric (seconds, °C, meters, volts).
- Unused original topics are kept in `backlog.json`.

## Daily runbook
1. `git pull`. Pick the first calendar entry whose date is today (or the oldest `todo` if a day was missed).
2. `episodes/NNN-slug/script.json` — write the lines (facts must be accurate; hedge where science is uncertain).
3. `pip install bpy kokoro-onnx soundfile --break-system-packages` then `python3 pipeline/tts.py episodes/NNN-slug`
   → `timing.json` (line start times). Target 25–28 s total; if shorter than 25 s, add lines (don't slow the voice).
4. Write `episodes/NNN-slug/scene.py` (Blender, start from `episodes/001-dig-forever/scene.py`
   for helpers: mat/box/cyl/sphere/tube, layered ground shader, house, trees, sky, camera rig).
   Scene length = narration length + 0.7 s at 24 fps, keyframes placed at the `timing.json` line starts.
   Camera framing: 9:16 portrait, lens 26 mm ⇒ only about ±4.3 units are visible horizontally at 11 units distance;
   put every detail inside that window and IN FRONT of cut faces (not buried behind them).
   Save `scene.blend`, render previews `python3 pipeline/render.py episodes/NNN-slug 40 8 <frames...>`,
   look at them, fix, then full render `python3 pipeline/render.py episodes/NNN-slug` (~10 s/frame).
5. Optional `style.json` (badge + highlight words), then `python3 pipeline/compose.py episodes/NNN-slug videos/DATE-slug.mp4`.
   Check a contact sheet of frames before publishing.
6. Commit scripts + video (not frames/blend/wav), push. Video URL:
   `https://raw.githubusercontent.com/salihsanduvac442-ctrl/whatif-shorts/main/videos/DATE-slug.mp4`
7. Metricool `createScheduledPost`, blogId 7400439, network youtube, type `short`, public, madeForKids false,
   category ENTERTAINMENT, title = calendar title + " #shorts", 3–5 tags, timezone Europe/Istanbul,
   time from `getBestTimeToPostByNetwork` (fallback 19:00). Then set the calendar entry to `published`
   with the planner URL, commit, push.
