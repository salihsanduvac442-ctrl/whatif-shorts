# What If Shorts — daily challenge (Oct 26 → Dec 31, 2026)

One 3D "What if...?" YouTube Short per day, published through Metricool.
`calendar.json` holds the 67 topics (day, date, title, category, status).

## Format (keep it identical every day)
- 1080x1920, 22–28 s, 30 fps. Hook question in the first 2 s, no intro.
- Stylized low-poly 3D in Blender (Cycles), bright cartoon colors, cross-section / diorama look
  (reference: viral "What if" house + soil cut-away shorts). Camera keeps moving the whole time
  (dolly, push-in, descent or orbit) — never a static shot longer than ~2 s.
- Something new appears on screen every 2–3 s (objects, creatures, effects) tied to the narration.
- Narration: Kokoro `am_michael`, speed 1.34, 9–13 short punchy lines, last line is a question
  to drive comments ("So... would you ...?").
- One-word pop captions centre screen, numbers + key nouns in yellow; a pill badge at the top
  counting the key metric (depth, distance, size, temperature, time...).
- Impact zoom/shake + whoosh/boom on each line, 128 bpm music bed (all done by `pipeline/compose.py`).

## Daily runbook
1. `git pull`. Pick the first calendar entry whose date is today (or the oldest `todo` if a day was missed).
2. `episodes/NNN-slug/script.json` — write the lines (facts must be accurate; hedge where science is uncertain).
3. `pip install bpy kokoro-onnx soundfile --break-system-packages` then `python3 pipeline/tts.py episodes/NNN-slug`
   → `timing.json` (line start times). Target 22–28 s total.
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
