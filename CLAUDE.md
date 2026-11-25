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
- Berend opens Claude Code in that folder: `C:\Users\beren\OneDrive\Documents\GitHub\Master-thesis`.
  Work there (not in a copy elsewhere), so his VS Code, GitHub Desktop and Claude Code all use the same files.
- Test changes before pushing: run `python server.py`, open http://localhost:8000/?debug=1 and click
  through at least one full run; check the CSV output in `data/`.

## The study (short)

Within-subjects experiment: does a numeric AI confidence score help people trust AI answers
appropriately (accept correct answers, decline incorrect ones)?

- 30 yes/no questions (Q01-Q10 SimpleQA, Q11-Q20 Dutch facts, Q21-Q30 StemWijzer 2025 party
  positions), split into sets A and B (15 each). The AI majority answer is correct on 21 of 30
  (70%): set A 10 correct + 5 incorrect, set B 11 correct + 4 incorrect. Q14 was rephrased and
  re-run on 25 Nov 2026 ("Is the maximum duration ... 36 months?" -> No, 89%, correct).
  Berend decided to keep all 30 and not replace questions to reach the originally planned 80%.
  `python check_questions.py` verifies questions.js (scores, sets, runs, answer texts).
- Confidence score = agreement between 5 models x 20 runs (Claude, GPT, Gemini, DeepSeek, Qwen3-8B
  via ChainForge, no web search): the share of all valid runs that give the majority answer.
  The AI assistant shows the majority answer plus one real model explanation (`aSource`).
  Correctness is not manipulated.
- Two blocks of 15 questions: one without score (baseline), one with score (confidence).
  Four counterbalanced groups, chosen by the researcher on the first screen:
  P1 Base A -> Conf B, P2 Base B -> Conf A, P3 Conf A -> Base B, P4 Conf B -> Base A.
  Question order within a block is FIXED (order in questions.js, same for everyone;
  Berend's choice, 25 Nov 2026; STUDY.randomizeOrder = false). The setup screen shows only
  P1-P4, not which part has the confidence score (so participants learn nothing about the design).
- Flow: researcher setup (participant number + group) -> instructions -> block 1 -> break
  (participant fills in a Qualtrics questionnaire) -> instructions -> block 2 -> back to Qualtrics.
- Consent, debrief, demographics, GAAIS-10, Jian trust scale and extra questions are all in
  Qualtrics (UvA), not in the app. They are matched to the app data by participant number.
  (`showConsent` / `showDebrief` in study-config.js can switch them on in the app, now off.)
- Per question the participant only clicks Accept or Decline. The fact-check button was removed
  on purpose (after supervisor feedback). In the confidence block, "Show details" lists the
  agreement per model; hovering a model lists all its 20 answers, split into "same answer as shown"
  and "opposite answer" (runs without a clear Yes/No are listed separately and not counted).
- Measures (trials CSV, one row per question): group, block, set, condition, question_id, part,
  ai_answer, ai_correct, overall_confidence, decision, appropriate (1/0), rt_ms (from when the
  full answer is visible), answer_ready_ms, details_opened, hover count/models/time. Use the term
  "detail-inspection rate", not "verification rate" (nothing is verified against an outside source).
- Each answer appears after a fixed "Thinking..." delay and is then typed out, with the same
  timing rules for every question, so the delay is never a cue.

## Files

- `index.html` - the participant app: layout, styling and all logic (well commented).
- `study-config.js` - settings, the groups P1-P4 and all texts.
- `questions.js` - the 30 questions with all 3,000 model answers (generated from the ChainForge
  export + local Qwen run; Q14 from Confidence_scores_all_models.xlsx). Format per run:
  `[1, "full answer", agrees, invalid?]`.
- `check_questions.py` - checks questions.js; must print ALL CHECKS PASSED.
- `server.py` - local Python server (standard library only). Serves the app and writes
  `data/participants.csv`, `data/Pxxx_events.csv`, `data/Pxxx_trials.csv`, `data/Pxxx_responses.csv`.
- `README.md` - how to run a session and what the output files contain.
- `Claude outputs/` - helper spreadsheets from earlier Claude sessions (not used by the app).

GitHub Pages also serves the app, but there is no server there, so nothing is saved (beta preview
shows a "nothing is saved" banner and offers a JSON backup download at the end).

- Resume: "Resume at Part 2" on the setup screen continues a participant after a reload/closed
  window (same number + group); only unanswered Part 2 questions are shown, rows are appended.
  A new start with an existing number is refused unless the researcher confirms.
- Testing without touching data/: `python server.py --data test_data` (test_data/ is gitignored).

## Open items / before real data collection

1. `beta` is now `false` in study-config.js (set 25 Nov 2026). The GitHub Pages demo therefore no
   longer shows the researcher view unless `?debug=1` is added to the address.
2. Update `estimatedMinutes` after the pilot.
3. Move/delete the old `data/` folder: earlier test files have different CSV columns.
4. Run an internal pilot with all four groups and check the CSVs (block/set/condition per row).
5. Note for the ethics/data plan: `data/` is inside OneDrive, so participant CSVs sync to the cloud.
