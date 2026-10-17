# Module 3 user-study materials

## Status and ethics

This folder prepares the planned two-group study; it does not contain participant records,
and the study has not been conducted. Obtain supervisor/institutional ethics approval before
recruitment, pilot sessions involving participants, or enabling app collection. The consent
wording below is a draft, not an approval or substitute for the institution's required form.
Do not recruit minors or collect names, phone numbers, or other direct identifiers using this
toolkit.

Use the [participant information draft](participant-information-template.md) and
[interview-notes template](interview-notes-template.md) only as inputs for supervisor/ethics
review; replace them with approved materials before recruitment.

## Proposed protocol

- Research question: do score + bilingual LIME explanations + temporal warnings improve
  participants' identification of misinformation compared with a score-only display?
- Target: 40 adults, assigned 20 per condition using a documented random allocation method.
- Items: the same ten pre-reviewed Sinhala items in both groups; include credible, uncertain,
  misinformation, and old/recirculated cases only when the evidence supports those labels.
- Group A sees the fused score and verdict only. Group B additionally sees the LIME reasons
  and available temporal warning. The application uses the same API analysis in both arms
  and hides the extra information for Group A.
- Primary outcome: each participant's proportion of correct decisions across the ten items.
- Secondary outcomes: per-item 1–7 trust rating and seconds from result display to saved
  decision. Analyse participant-level summaries; do not treat ten responses from one person
  as ten independent participants.
- Analysis: inspect distributions; use Welch's independent-samples t-test when both groups'
  participant-level observations are reasonably normal, otherwise a two-sided Mann–Whitney U
  test. Report group sizes, descriptive summaries, test choice, p-value, effect estimate,
  limitations, and missing/excluded records. Preregister whether the primary hypothesis is
  directional before seeing data.
- Data handling: use facilitator-issued anonymous participant codes, export CSV locally,
  transfer it to an approved access-controlled location, and delete local copies according
  to the approved retention schedule. The app stores history/response rows on-device only.

## Synthetic pipeline demo (not study results)

To exercise the allocation-independent analysis pipeline without real participants, generate
an explicitly synthetic 40-person/10-item fixture in a temporary folder:

```powershell
python generate_demo_data.py $env:TEMP\sinhalacheck-synthetic-demo
python analyze_user_study.py `
  $env:TEMP\sinhalacheck-synthetic-demo\synthetic_demo_trials.csv `
  $env:TEMP\sinhalacheck-synthetic-demo\synthetic_demo_answer_key.csv `
  --expected-items 10 --simulated-demo `
  --output $env:TEMP\sinhalacheck-synthetic-demo\synthetic_demo_report.json
```

The report is marked `simulated_demo` and says the generated rows are not real participants,
study results, or evidence. Do not cite or submit it as a user-study finding. This fixture only
tests the software pipeline; it does not complete the planned study.

## Preparing verified items

1. Copy `items-reviewed-template.csv` to a private working location.
2. Populate exactly ten full texts. For each, two reviewers should verify the appropriate
   label against primary reporting or reputable fact-check evidence and record reviewer/date.
3. Never treat a model prediction as ground truth. Record a publication date only when
   independently supported.
4. Build the participant pack and keep the key outside the mobile app:

```powershell
python prepare_study_items.py .\items-reviewed.csv `
  --public-output ..\mobile\assets\study-items.json `
  --answer-key-output .\private\answer-key.csv
```

The builder excludes gold labels and evidence URLs from the participant pack. The answer key
contains labels and audit evidence; do not commit or ship it to participants. A pack cannot be
built while fields are blank or if its URLs, labels, date, or reviewer metadata are invalid.

For a balanced allocation, prepare a CSV containing only facilitator-issued anonymous
`participant_id` codes, then run:

```powershell
python randomize_groups.py .\anonymous-codes.csv .\private\group-allocation.csv
```

The tool requires exactly 40 unique codes and assigns 20 to each group. Keep the allocation
file private. An optional `--seed` supports reproducibility; if used, record the seed in the
approved study log rather than in participant-facing materials.

## Enabling response collection

Only in an approved build, set `EXPO_PUBLIC_ENABLE_RESEARCH=true`,
`EXPO_PUBLIC_ETHICS_APPROVED=true`, `EXPO_PUBLIC_STUDY_GROUP=A` or `B`, and
`EXPO_PUBLIC_CONSENT_TEXT` to the exact approved consent wording. The app hides study controls
if any of these are missing. Create separate fixed-group builds; participants cannot self-select
their condition. Keep the study and approval flags false otherwise. Ask the participant to enter a facilitator-issued anonymous
code, select a reviewed study item, and consent. Collect one response per participant/item.
The app records
decision, trust, and decision time locally; it does not collect names or upload research
responses to the API.

Export `sinhalacheck-study-responses.csv` from the app's History screen. It contains no gold
labels. Keep the answer key separate, then analyse only after review of the exported CSV:

```powershell
python analyze_user_study.py .\trials.csv .\private\answer-key.csv `
  --expected-items 10 --output .\private\analysis-report.json
```

The script rejects duplicate/incomplete participant-item responses and mismatched answer
keys. Its report is a draft statistical summary; the research owner must verify assumptions,
preregistered methods, exclusions, and interpretation before using it in a paper.

## Consent statement draft

> I have read the institution-approved participant information, understand that participation
> is voluntary, and consent to take part in this study. I understand how anonymous responses
> will be stored and how I may withdraw under the approved protocol.

Replace this text with the exact approved version before enabling the study build.
