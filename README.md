# Master thesis — confidence score study app

Study app for a within-subjects experiment on how a numeric AI confidence score
(agreement between five AI models) affects trust, reliance and trust calibration.

## Run a session

```
python server.py --open
```

This opens http://localhost:8000. Nothing needs to be installed besides Python 3.8+.
Each new visit gets the next participant ID (P001, P002, …) and a counterbalancing group.

Researcher URL options:

| Option | Effect |
|---|---|
| `?pid=P012` | use this participant ID |
| `?group=1`…`4` | force a counterbalancing group (piloting) |
| `?debug=1` | live event log, skip a block |

## Study flow

Consent → block 1 → block 2 → debrief. The questionnaires (GAAIS-10, Jian trust scale, final
questions) run separately in Qualtrics; match them to the app data with the participant ID (P001, …).

| Group | Block 1 | Block 2 |
|---|---|---|
| 1 | baseline, set A | confidence, set B |
| 2 | confidence, set A | baseline, set B |
| 3 | baseline, set B | confidence, set A |
| 4 | confidence, set B | baseline, set A |

## Files

- `index.html` — the participant app (logic and layout)
- `study-config.js` — questions, consent and debrief texts
- `server.py` — local server; writes CSVs to `data/` (ignored by git)

## Output (`data/`)

| File | Contents |
|---|---|
| `participants.csv` | ID, group, block order, status (started / finished / withdrew / declined) |
| `P001_events.csv` | every event: screens, hovers (with duration), details, fact-check, decisions, tab switches |
| `P001_trials.csv` | one row per question: decision, appropriate (1/0), RT, details/hover/fact-check measures |
| `P001_responses.csv` | consent statements |

Hovers shorter than 300 ms are logged with `value = short` and not counted in the trial summary.
