# Wishmitha — Module 3 deliverables

This folder groups the Module 3 mobile client, deployment packaging, and user-study
materials owned by Wishmitha (IT22259752). The app calls the shared FastAPI fusion
service; it does not load model weights or bypass Modules 1 and 2.

## Components

- [`mobile/`](mobile/) — Expo app with Home, Result, and History screens, local analysis
  history, optional bilingual LIME output, and a gated anonymous study-response flow.
- [`research/`](research/) — ethics-aware study protocol, reviewed-item template, item-pack
  builder, and analysis of collected participant responses.
- [`deployment/`](deployment/) — packaging tools and Docker setup for a Hugging Face Space.

The shared fusion API and content-model batch endpoint remain in
[`../sinhalacheck/services/fusion/`](../sinhalacheck/services/fusion/) and
[`../sinhalacheck/services/module1/`](../sinhalacheck/services/module1/); keeping them there
preserves the existing integrated service boundaries and launcher.

## Important research status

The 40-person study has **not** been run and no participant data or verified ten-item Sinhala
test set is included. Do not enable research collection or recruit participants until the
supervisor/institution has approved the protocol and participant information. The template
requires source verification and keeps the answer key out of the mobile app. Do not report
the planned sample size or target hypothesis as completed results.

The Hugging Face deployment package is prepared locally, not hosted. Hosting requires a
Space account and working HTTPS endpoints for both Module 1 and Module 2.
