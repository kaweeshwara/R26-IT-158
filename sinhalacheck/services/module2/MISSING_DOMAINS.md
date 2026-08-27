# Knowledge-base coverage gap

The curated knowledge base currently contains **24 domains**. Across the
LIRNEasia corpus (n=3000) it recognises only **19.9%** of publishers, so roughly four
in five documents fall back to `UNKNOWN_DEFAULTS` — a constant. A feature that is constant for
most inputs cannot contribute much to a fused score, which is measurable: source score alone
reaches only 0.535 ROC-AUC against the corpus labels, against 0.5 for chance.

These are the highest-impact domains to add, ordered by how many corpus documents they cover.
Several are major national newspapers (Aruna, Ravaya, Divaina, Dinamina), so their absence is a
coverage gap rather than a design flaw.

| # | domain | documents | cumulative coverage if added |
|---|---|---|---|
| 1 | `gosip-lankanews.com` | 219 | 27.2% |
| 2 | `gosip.hirufm.lk` | 193 | 33.6% |
| 3 | `aruna.lk` | 191 | 40.0% |
| 4 | `ravaya.lk` | 156 | 45.2% |
| 5 | `divaina.lk` | 150 | 50.2% |
| 6 | `deshaya.lk` | 136 | 54.7% |
| 7 | `bbc.com/sinhala` | 135 | 59.2% |
| 8 | `samabima.com` | 117 | 63.1% |
| 9 | `dinamina.lk` | 106 | 66.6% |
| 10 | `lankaenews.lk` | 101 | 70.0% |
| 11 | `ada.lk` | 101 | 73.4% |
| 12 | `vikalpa.org` | 99 | 76.7% |
| 13 | `nethnews.lk` | 98 | 79.9% |
| 14 | `sarasaviya.lk` | 97 | 83.2% |
| 15 | `roar.media` | 95 | 86.3% |
| 16 | `newshub.lk` | 94 | 89.5% |
| 17 | `anidda.lk` | 88 | 92.4% |
| 18 | `mawbima.lk` | 87 | 95.3% |
| 19 | `asianmirror.lk` | 86 | 98.2% |
| 20 | `praja.lk` | 55 | 100.0% |

Adding the top 10 raises coverage from 19.9% to 70.0%.

Note also that `bbc.com/sinhala` is stored with a path segment, so it never matches a host-only
lookup. Either normalise it to `bbc.com` or add a path-aware entry.
