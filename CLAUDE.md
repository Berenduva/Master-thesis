# Handover: Master-thesis study app

Context for Claude (Claude Code reads this file automatically). Written 25 Nov 2026 at the
handover from a Cowork chat session. Owner: Berend de Vries, MSc Information Science (IS/HCI),
University of Amsterdam. Supervisor: Katja Rogers.

## Working agreements

- Berend wants Claude to make the changes AND commit + push to GitHub (repo `Berenduva/Master-thesis`,
  branch `main`). He pulls / reloads to see them. Pull first before editing; he also edits files
  himself in VS Code.
- Explain things simply and briefly; he is not a professional developer.
- Never commit `data/` (participant data, in `.gitignore`). Do not put personal data in the repo
  (the repo is public).
- Thesis text he asks for: plain text, not LaTeX (unless he asks for LaTeX).
- He saves everything in OneDrive (not Dropbox anymore). The repo lives at
  `C:\Users\beren\OneDrive\Documents\GitHub\Master-thesis`.
- Test changes before pushing: run `python server.py`, open http://localhost:8000/?debug=1 and click
  through at least one full run; check the CSV output in `data/`.

## The study (short)

Within-subjects experiment: does a numeric AI confidence score help people trust AI answers
appropriately (accept correct answers, decline incorrect ones)?

- 30 yes/no questions (StemWijzer 2025 facts, StemWijzer party positions, SimpleQA politics),
  split into sets A and B (15 each). Each set has 10 questions where the AI majority answer is
  correct and 5 where it is incorrect (about 2/3 correct overall). Berend decided to keep all 30
  as they are and not replace questions to reach the originally planned 80% correct.
- Confidence score = agreement between 5 models x 20 runs (Claude, GPT, Gemini, DeepSeek, Qwen3-8B
  via ChainForge, no web search): the share of all valid runs that give the majority answer.
  The AI assistant shows the majority answer plus one real model explanation (`aSource`).
  Correctness is not manipulated.
- Two blocks of 15 questions: one without score (baseline), one with score (confidence).
  Four counterbalanced groups, chosen by the researcher on the first screen:
  P1 Base A -> Conf B, P2 Base B -> Conf A, P3 Conf A -> Base B, P4 Conf B -> Base A.
  Question order within a block is random per participant.
- Flow: researcher setup (participant number + group) -> instructions -> block 1 -> break
  (participant fills in a Qualtrics questionnaire) -> instructions -> block 2 -> back to Qualtrics.
- Consent, debrief, demographics, GAAIS-10, Jian trust scale and extra questions are all in
  Qualtrics (UvA), not in the app. They are matched to the app data by participant number.
  (`showConsent` / `showDebrief` in study-config.js can switch them on in the app, now off.)
- Per question the participant only clicks Accept or Decline. The fact-check button was removed
  on purpose (after supervisor feedback). In the confidence block, "Show details" lists the
  agreement per model; hovering a model lists all its 20 answers split into Yes (agrees) / No.
- Measures (trials CSV): decision, appropriate (1/0), rt_ms (from when the full answer is
  visible), answer_ready_ms, details_opened, hover count/models/time. Use the term
  "detail-inspection rate", not "verification rate" (nothing is verified against an outside source).
- Each answer appears after a fixed "Thinking..." delay and is then typed out, with the same
  timing rules for every question, so the delay is never a cue.

## Files

- `index.html` - the participant app: layout, styling and all logic (well commented).
- `study-config.js` - settings, the groups P1-P4 and all texts.
- `questions.js` - the 30 questions with all 3,000 model answers (generated from the ChainForge
  export + local Qwen run). Format per run: `[1, "full answer", agrees, invalid?]`.
- `server.py` - local Python server (standard library only). Serves the app and writes
  `data/participants.csv`, `data/Pxxx_events.csv`, `data/Pxxx_trials.csv`, `data/Pxxx_responses.csv`.
- `README.md` - how to run a session and what the output files contain.
- `Claude outputs/` - empty folder created by the Claude desktop app; can be ignored or deleted.

GitHub Pages also serves the app, but there is no server there, so nothing is saved (beta preview
shows a "nothing is saved" banner and offers a JSON backup download at the end).

## Open items / before real data collection

1. Set `beta: false` in study-config.js (beta shows the researcher view to everyone; it was on for
   demos to Katja). `?debug=1` still shows it for the researcher.
2. Update `estimatedMinutes` after the pilot.
3. Move/delete the old `data/` folder: earlier test files have different CSV columns.
4. Run an internal pilot with all four groups and check the CSVs (block/set/condition per row).
5. Note for the ethics/data plan: `data/` is inside OneDrive, so participant CSVs sync to the cloud.
