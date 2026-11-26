# Master thesis — confidence score study app

Study app for a within-subjects experiment on how a numeric AI confidence score
(agreement between five AI models) affects trust, reliance and trust calibration on
correct and incorrect AI answers.

## Before real data collection

- `study-config.js` → `beta: false` (the **BETA SWITCH**, near the top of `STUDY`). With `beta: true`
  everyone sees the researcher view; keep it `false` for participants. You can still open the
  researcher view yourself with `?debug=1`.
- Move the old `data/` folder away (earlier test files have different CSV columns and use numbers P001–P021).
- Run `python check_questions.py` → it must end with `ALL CHECKS PASSED`.
- Update `estimatedMinutes` in `study-config.js` after the pilot.

## Run a session

```
python server.py --open
```

This opens http://localhost:8000. Nothing needs to be installed besides Python 3.8+.

The first screen is for the researcher:

1. **Participant number**: the same as in Qualtrics. Leave empty to get the next free number (P001, P002, …).
2. **Group** (Group 1–4; stored as 1–4 in the `group` column). The screen only shows the group name, not which part has the confidence score,
   so a participant who sees the screen learns nothing about the design. What each group means:

   | Group | First block | Second block |
   |---|---|---|
   | Group 1 | Base, set A | Conf, set B |
   | Group 2 | Base, set B | Conf, set A |
   | Group 3 | Conf, set A | Base, set B |
   | Group 4 | Conf, set B | Base, set A |

   Base = without confidence score, Conf = with confidence score, "Show details" (agreement per model)
   and pointing at a model to see all 20 of its answers.
3. **Start**: *New participant* (start at Part 1) or *Resume at Part 2* (see below).

If you start a new participant with a number that already exists, the app does not start: it shows
what is stored for that number and asks you to resume or use another number (there is a button to
start anyway; the server console then prints a warning).

Researcher URL options:

| Option | Effect |
|---|---|
| `?pid=P012` | pre-fill the participant number |
| `?group=2` | pre-select Group 2 |
| `?debug=1` | researcher view: live event log, measures, "skip to the end of this part" |

## Study flow

Researcher setup → instructions Part 1 → block 1 (15 questions) → break (the participant fills in the
Qualtrics questionnaire, then clicks "Continue to Part 2" and confirms in a small dialog) → instructions
Part 2 → block 2 (15 questions) → back to the questionnaire. Within a block the questions are shown in a
FIXED order, the same for every participant: the order in `questions.js` (set A: Q02, Q04, Q07, Q08, Q09,
Q13, Q15, Q17, Q19, Q20, Q21, Q22, Q26, Q28, Q29; set B: the other 15 in number order). The order shown is
stored as `trial_plan`. (`randomizeOrder: true` in `study-config.js` would give a random order per participant.)

Per question the participant clicks **Accept** (the answer is correct) or **Decline** (it is wrong). There
is no feedback. Base and Conf use exactly the same question, answer text, "Thinking…" time and typing speed;
the only difference is the confidence score and its details.

Consent, debrief and the questionnaires (GAAIS-10, Jian trust scale, final questions) run in Qualtrics; match
them to the app data with the participant number. Consent/debrief in the app can be switched on in
`study-config.js` (`showConsent`, `showDebrief`).

## Resume after a reload or closed window

If the browser window is reloaded or closed during the break or Part 2:

1. Open http://localhost:8000 again.
2. Enter the **same participant number** and choose the **same group**.
3. Choose **Resume at Part 2** and click the button.

The app goes back to the break screen (if Part 2 had not started) or to the Part 2 instructions, and
shows only the Part 2 questions that were not answered yet (numbering continues, e.g. 6 of 15). Nothing
is overwritten: rows are appended to the same files, `participants.csv` gets a `resumed` row and the
events file a `session_resumed` event. A wrong number or group is refused with an explanation.
(A reload during Part 1 cannot be resumed: start Part 1 again with a new number, or decide how to handle it.)

## When you see an error during a session

- **Red banner "Connection to the study server lost — retrying (N unsent)"**: the page could not send data to
  `server.py`. Do NOT close or reload the page: the unsent data are still in the page and are sent
  automatically as soon as the connection works. Check that the PowerShell window with `python server.py`
  is still open and running (if not, start it again with `python server.py`). The banner disappears when
  everything is sent.
- **Red banner "Not connected to the study server — data are NOT being saved"** at the start: the server was
  not running. Start `python server.py`, reload the page and start the participant again.
- **Window closed or reloaded by accident**: start the server if needed, open http://localhost:8000 and use
  "Resume at Part 2" (see above).
- **At the end the page shows "Download data backup"**: click it and keep the `.json` file; it contains all
  data of that participant.
- Note the participant number and what happened in your logbook, so you can check that participant's CSV files.

## Questions

`questions.js` holds the 30 questions with all 3,000 model answers (Claude Sonnet 5.5, GPT-6.1 Sol,
Gemini 3.8 Flash, DeepSeek V4.1 Flash, Qwen3-8B; 20 runs each). The AI assistant shows the majority answer
of all runs plus one real, unedited model explanation: always the first GPT-6.1 Sol run (`aSource`; in all 30 questions this run gives the majority answer). The confidence score is
the share of all valid runs that give the majority answer (one Gemini run on Q08 had no Yes/No: it is listed
but not counted). The AI is correct on 21 of 30 questions (70%): set A 10 correct + 5 incorrect, set B 11
correct + 4 incorrect. Q14 was rephrased and re-run ("Is the maximum duration of Dutch unemployment benefit
(werkloosheidsuitkering) 36 months?" → No, 89%, correct).

Check the file with:

```
python check_questions.py
```

It verifies the 30 questions, the set split, 20 runs per model, the `agrees` flags, every confidence score
(against the expected values in the script), `correct` vs. the ground truth, and that each shown answer
starts with the majority answer, is at most two sentences and has no hedging or markdown.

## Files

- `index.html` — the participant app (logic and layout)
- `study-config.js` — settings (incl. the beta switch), groups (Group 1–4) and all texts
- `questions.js` — the 30 questions and model answers
- `check_questions.py` — checks `questions.js`
- `server.py` — local server; writes CSVs to `data/` (ignored by git). `--data test_data` writes to another
  folder, e.g. for a test run (`test_data/` is ignored by git as well).

## Output (`data/`)

| File | Contents |
|---|---|
| `participants.csv` | pid, session_id, group, status (started / resumed / finished / withdrew), time, browser, screen size |
| `P001_events.csv` | every event with group, block, set, condition, trial, question and timing (see below) |
| `P001_trials.csv` | one row per question (see below) |
| `P001_responses.csv` | consent statements (only if consent is shown in the app) |

**Trials** (one row per question): pid, session_id, group, block, set, condition, trial, question_id, part,
ai_answer, ai_correct, overall_confidence (also in Base, where it was hidden), decision, appropriate (1/0),
answer_ready_ms (thinking + typing time), rt_ms (from when the full answer was visible), details_opened,
details_toggles, hover_count, hovered_models, hover_total_ms, viewed_models, view_total_ms (detail, hover
and view fields are empty in Base).

**Events**: `group_assigned`, `session_start`, `session_resumed`, `screen_shown`, `trial_plan` (question order
shown per block), `trial_shown`, `answer_shown`, `details_open` / `details_close`, `hover` (pointing at a model row),
`hover_list` (pointing at that model's list of answers), `answers_view` (a model's answers on screen),
`model_click`, `decision`, `part2_confirm_shown` /
`part2_confirm_cancelled`, `pause_end` (break length in `duration_ms`), `tab_hidden` / `tab_visible`,
`stop_clicked`, `page_closed`.

Hovers (both `hover` and `hover_list`) shorter than 400 ms (`hoverThresholdMs`) are logged with
`value = short` and not counted in the trial summary; counted ones have `value = counted`. Hover time per
model per question = the sum of `duration_ms` of counted `hover` + `hover_list` events with that `target`.

**Answer-view time** (`answers_view`, `viewed_models`, `view_total_ms`): participants often move the mouse away
to read a model's answers, so the app also measures how long each model's answers are ON SCREEN, whatever the
mouse does. It runs from the moment a model's answers appear (pointing at or clicking the model) until another
model is shown, the details close, a dialog opens, the tab is hidden or the participant decides, and goes on
again when the details / tab / dialog come back. Brushing past a model (< 400 ms) is logged as `short` and not
counted; a continued stretch after the details / tab / dialog come back is always counted. View time per model
per question = the sum of `duration_ms` of counted `answers_view` events with that `target`.

Measures this supports: AcceptRate, detail-inspection rate (details_opened), TrustCalibration =
AcceptRate(correct) − AcceptRate(incorrect), Accuracy (mean of `appropriate`), and hover time and answer-view
time per model per question.
