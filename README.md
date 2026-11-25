# Master thesis — confidence score study app

Study app for a within-subjects experiment on how a numeric AI confidence score
(agreement between five AI models) affects trust, reliance and trust calibration.

## Run a session

```
python server.py --open
```

This opens http://localhost:8000. Nothing needs to be installed besides Python 3.8+.
Leave the participant number empty to get the next free ID (P001, P002, …).

The first screen is for the researcher: enter the participant number (the same as in Qualtrics; leave
empty for the next free number) and choose the group:

| Group | First block | Second block |
|---|---|---|
| P1 | Base, set A | Conf, set B |
| P2 | Base, set B | Conf, set A |
| P3 | Conf, set A | Base, set B |
| P4 | Conf, set B | Base, set A |

Base = without confidence score, Conf = with confidence score.

Researcher URL options:

| Option | Effect |
|---|---|
| `?pid=P012` | pre-fill the participant number |
| `?group=P2` | pre-select the group |
| `?debug=1` | live event log, skip to the end of a part |

## Study flow

Researcher setup → instructions part 1 → block 1 (15 questions) → break (participant fills in the Qualtrics
questionnaire, then clicks "Continue to part 2") → instructions part 2 → block 2 (15 questions) → back to the
questionnaire. Within a block the questions are shown in a random order.

Consent, debrief and the questionnaires (GAAIS-10, Jian trust scale, final questions) run in Qualtrics; match
them to the app data with the participant number. Consent/debrief in the app can be switched on in
`study-config.js` (`showConsent`, `showDebrief`).

## Questions

`questions.js` holds the 30 questions with all 3,000 model answers (Claude, GPT, Gemini, DeepSeek, Qwen;
20 runs each). The AI assistant shows the majority answer of all runs plus one real model explanation that
gives the same answer (`aSource`). The confidence score is the share of all valid runs that give the
majority answer (one Gemini run on Q08 had no Yes/No and is left out). Question sets A and B are in the
`set` field.

## Files

- `index.html` — the participant app (logic and layout)
- `study-config.js` — settings, groups (P1–P4) and all texts
- `questions.js` — the 30 questions and model answers
- `server.py` — local server; writes CSVs to `data/` (ignored by git)

## Output (`data/`)

| File | Contents |
|---|---|
| `participants.csv` | ID, group, status (started / finished / withdrew) |
| `P001_events.csv` | every event: group, the random order per block (`trial_plan`), screens, hovers (with duration), details, decisions, break length, tab switches |
| `P001_trials.csv` | one row per question: group, block, set, condition, decision, appropriate (1/0), RT, details/hover measures |
| `P001_responses.csv` | consent statements (only if consent is shown in the app) |

Hovers shorter than 400 ms are logged with `value = short` and not counted in the trial summary.

If you still have a `data/` folder from earlier tests, move it away before the real study: the CSV columns changed.
