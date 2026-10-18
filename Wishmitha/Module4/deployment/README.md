---
title: SinhalaCheck Wishmitha Fusion API
emoji: 🔎
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# Hugging Face Spaces deployment package

This directory packages the shared FastAPI gateway. It does **not** bundle either model or
pretend that an unconfigured local URL is a working cloud dependency.

## Build a Space-ready folder

From the repository root:

```powershell
python .\wishmitha\deployment\prepare_space.py C:\path\to\empty\sinhalacheck-space
```

Review the generated files, create a Docker Space, and push that generated folder to the
Space repository using your own Hugging Face account. The builder refuses to overwrite an
existing generated file unless `--force` is specified.

In Space Settings, configure **both** `MODULE1_URL` and `MODULE2_URL` as reachable HTTPS API
base URLs. The Module 1 deployment must provide `/predict`, `/predict/batch`, and `/info`;
Module 2 must provide `/analyze`. Check `/health` after deployment. Do not put access tokens
in source files or in a public mobile build.

The Space is a research/demo API, not a hardened public production service. Before exposing
it publicly, add an authenticated/rate-limited gateway, privacy review, and deployment
monitoring. Real model serving and Hugging Face hosting are external prerequisites and are
not included in this source-only package step.
