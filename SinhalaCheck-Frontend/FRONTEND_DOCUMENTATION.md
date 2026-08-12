# SinhalaCheck — Mobile App (Frontend)

## Client Walkthrough & Code Explanation Guide

*Project: SinhalaCheck — Sri Lankan news credibility checker*
*This module: Mobile App (Frontend)*
*Stack: React Native · Expo · JavaScript*
*Companion module: FastAPI backend (see `backend/PROJECT_DOCUMENTATION.md`)*

---

## How to Use This Document

This is a **presenter's guide**. Read top-to-bottom with the client and you will have explained the entire frontend codebase. Each step has:

1. **What it is** — plain-English purpose.
2. **Why it exists** — the problem it solves.
3. **Where it lives** — file path.
4. **How it works** — the key code, explained.

A typical walkthrough takes **20–30 minutes**.

---

## 1. What the App Does (1 minute)

SinhalaCheck is a mobile app that lets a user **paste a news article URL** (and optionally the article text in **English, Sinhala, or Singlish**) and instantly get a verdict on:

- **Is the source trustworthy?** — Trusted / Moderate / Risky
- **Is the news still current?** — Fresh / Recent / Old / Very Old
- **Why?** — A human-readable list of reasons backed by a trust score, freshness score, and confidence score.

The frontend is a **thin, beautiful UI layer**. All the intelligence (rule-based scoring + Random Forest ML model) lives in the FastAPI backend. The frontend's job is to:

- Capture user input cleanly.
- Talk to the backend over HTTP.
- Display the result in a way that's easy to read and act on.

---

## 2. Live Demo Script (the "happy path")

Walk the client through this before opening any code. It frames everything that follows.

1. **Open the app.** They see a header `SinhalaCheck`, a card titled *Check an article*, and a hint at the bottom: *"How it works"*.
2. **Paste a URL** (e.g. `https://www.adaderana.lk/news/123/sample`).
3. **(Optional) Paste the article text** — Sinhala, English, or Singlish all work.
4. **Tap *Analyze*.** A spinner appears.
5. **Result appears** as:
   - A coloured **verdict banner** with a big trust-score percentage.
   - Quick **badges** (e.g. `Trusted`, `Fresh`, `.lk source`, `Detected: Sinhala`).
   - **Source** card (publisher + domain + age).
   - **Why this verdict** — bullet-point reasons.
   - **Scores** — three progress bars (credibility, freshness, confidence).
   - **Feature breakdown** — registration, domain age, history, editorial, cross-coverage.
   - **Diagnostics** — collapsible advanced details for technical users.

Everything that follows is *how* we built that experience.

---

## 3. Technology Stack

| Layer | Choice | Why |
|---|---|---|
| Mobile framework | **React Native 0.81** | One codebase → iOS + Android + Web. |
| Tooling | **Expo SDK 54** | Zero-config dev server, easy device testing via QR code, no Xcode/Android Studio needed for iteration. |
| Language | **JavaScript (ES2022)** | Fast onboarding, lowest barrier for the client's team to extend later. |
| Networking | Native `fetch` + `AbortController` | No external HTTP library — keeps the bundle small. |
| State | React `useState` | Pure local state; no Redux, MobX, or Context — kept intentionally simple for a single-screen app. |
| Styling | `StyleSheet` + custom theme tokens | Native performance, consistent design system. |

> **Talking point for the client:** *"We deliberately kept the frontend dependency list minimal. It boots fast, is easy to maintain, and any React Native developer can pick it up in an afternoon."*

---

## 4. Project Structure (the map)

```
frontend/
├── App.js                    ← Top-level screen (the only screen)
├── index.js                  ← Expo entry point (boots App.js)
├── app.json                  ← Expo config (app name, icons, splash)
├── package.json              ← Dependencies & npm scripts
└── src/
    ├── config.js             ← API base URL detection
    ├── theme.js              ← Colors, spacing, typography, badge tones
    ├── api/
    │   └── sinhalaCheck.js   ← HTTP client for the backend
    └── components/
        ├── AnalyzeForm.js    ← Input form (URL, text, advanced fields)
        ├── ResultView.js     ← The full verdict screen
        ├── Card.js           ← White rounded container (re-usable)
        ├── Badge.js          ← Pill-shaped tag (re-usable)
        ├── ScoreBar.js       ← Labeled progress bar (re-usable)
        └── ErrorBanner.js    ← Red error box at the top
```

**Two folders to remember:**

- `src/api/` → talks to the backend.
- `src/components/` → builds what the user sees.

Everything else is a single-file responsibility.

---

## 5. Step-by-Step Code Walkthrough

The order below is the order to present in. Each step builds on the previous one.

### Step 1 — Entry Point: `index.js` + `app.json`

**File:** `index.js`

```js
import { registerRootComponent } from 'expo';
import App from './App';

registerRootComponent(App);
```

**Explain:** *"Expo needs to know which component is the root of the app. This file is two lines that say 'start with `App`'. We never touch it again."*

**File:** `app.json` — non-code config: app name, icons, splash screen color, orientation. Show it briefly so the client knows where branding/icons are configured.

---

### Step 2 — The Single Screen: `App.js`

**File:** `App.js`

This is the **whole app in one screen**. It owns three pieces of state:

```js
const [loading, setLoading] = useState(false);
const [result, setResult] = useState(null);
const [error, setError] = useState(null);
```

**Explain to the client:** *"At any moment the app is in exactly one of four states: idle, loading, showing a result, or showing an error. Three booleans/objects describe all of them. That simplicity is intentional."*

The screen is composed top-to-bottom of:

1. **Header** — logo (`SC`), app name, tagline, and a tiny `API: ...` line so we always know which backend the app is hitting (handy during demos).
2. **`<AnalyzeForm>`** — the input card (Step 6).
3. **`<ErrorBanner>`** — only shown if `error` is set.
4. **`<ResultView>`** — only shown if `result` is set.
5. **Empty-state hint** — the *"How it works"* card; only shown when there is nothing else.
6. **Footer** — a small credit line.

The brain of `App.js` is a single async function:

```js
async function handleAnalyze(payload) {
  setLoading(true);
  setError(null);
  try {
    const data = await analyze(payload);    // call the backend
    setResult(data);
  } catch (e) {
    setResult(null);
    if (e instanceof ApiError) {
      setError({ message: e.message, status: e.status });
    } else {
      setError({ message: e?.message || 'Unexpected error', status: 0 });
    }
  } finally {
    setLoading(false);
  }
}
```

**Explain:** *"Submit → call backend → put either the result or the error on screen → stop the spinner. That's the entire control flow."*

The form is wrapped in a `KeyboardAvoidingView` + `ScrollView` so the keyboard never hides the inputs and long results scroll naturally — a common usability win on mobile.

---

### Step 3 — Where to Find the Backend: `src/config.js`

**Why this file exists:** during development, the app may run on a phone, an Android emulator, or a web browser. Each one needs a different way to reach `localhost:8000`. We auto-detect.

```js
const PORT = 8000;

function deriveDevHost() {
  // 1. Use the LAN host Expo gives us when running on a real device.
  // 2. Fall back to 10.0.2.2 on Android emulator (special alias for host).
  // 3. Fall back to 'localhost' on web/iOS simulator.
}

export const API_BASE_URL = `http://${deriveDevHost()}:${PORT}`;
```

**Talk to the client:** *"For production we just change one line — point this at the deployed backend URL — and the app is ready to ship. No environment variables, no rebuild gymnastics."*

---

### Step 4 — The Design System: `src/theme.js`

This single file is the **design language** of the app: colors, spacing scale, border radii, typography presets.

Three things to highlight:

1. **Semantic color tokens.** Instead of using raw hex codes everywhere, we name what they mean:
   - `colors.trusted` (green), `colors.moderate` (amber), `colors.risky` (red)
   - `colors.info` (blue), `colors.warn` (orange), `colors.neutral` (slate)

2. **Spacing scale** (`xs: 4 → xxl: 32`). Every margin/padding in the app uses one of these values, which makes the layout feel rhythmically consistent.

3. **Tone helper functions.** Three pure functions decide what color a verdict, freshness label, or alert should appear in:

```js
export function tierTone(label) {
  // 'Trusted' → green, 'Moderate' → amber, 'Risky'/'Blacklisted' → red
}

export function timeTone(label) {
  // 'Fresh' → green, 'Recent' → blue, 'Old' → orange, 'Very Old' → red
}

export function alertTone(label, sourceScore) {
  // Maps the source_score (0..1) to red/amber/green if available;
  // otherwise falls back to tierTone(label).
}
```

**Why it matters to the client:** *"To re-skin the app or align it with a brand guideline later, you change this one file. No hunting through 200 components."*

---

### Step 5 — Talking to the Backend: `src/api/sinhalaCheck.js`

**Job:** make HTTP requests to FastAPI cleanly, with timeouts and helpful error messages.

The file has three exports:

| Export | Purpose |
|---|---|
| `analyze(payload)` | The main call. Sends `POST /analyze`. |
| `getHealth()` | Sends `GET /` — used for diagnostics. |
| `getSources()` | Sends `GET /sources` — lists the curated knowledge base. |
| `ApiError` | Custom error class so the UI can react to backend errors specifically. |

The internal `request()` helper does four things worth highlighting:

1. **Timeout protection (25 s).** If the backend is unreachable, we abort and show a clear message instead of hanging the UI.
   ```js
   const ctrl = new AbortController();
   const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
   ```

2. **Friendly network errors.** If the request fails to even reach the server, we explain the most common cause:
   ```js
   throw new ApiError(
     `Could not reach the backend at ${API_BASE_URL}.\n` +
     'On a physical device, make sure your phone and PC are on the same Wi-Fi.',
     0,
   );
   ```

3. **Smart error parsing.** FastAPI returns errors as `{ detail: "..." }` for simple cases and `{ detail: [...] }` for validation errors. `extractErrorMessage()` handles both formats so the user sees a readable message either way.

4. **Whitelisted payload.** `analyze()` only forwards the fields the backend actually expects, dropping anything undefined:
   ```js
   const body = { url: payload.url };
   if (payload.text) body.text = payload.text;
   if (payload.published_date) body.published_date = payload.published_date;
   if (payload.recirculated !== undefined && payload.recirculated !== null)
     body.recirculated = payload.recirculated;
   if (payload.cross_count !== undefined && payload.cross_count !== null)
     body.cross_count = payload.cross_count;
   if (payload.seen_count !== undefined && payload.seen_count !== null)
     body.seen_count = payload.seen_count;
   ```

**Talking point:** *"This is the only file that knows the backend exists. If we ever swap the backend (say, to GraphQL or to a different microservice), this is the one file we change."*

---

### Step 6 — The Input Form: `src/components/AnalyzeForm.js`

This is the card the user fills in. It owns its **own** local state — the parent (`App.js`) only sees the final, validated payload when the user taps *Analyze*.

#### Fields

- **Article URL or domain** *(required)*
- **Article text or claim** *(optional, multi-line, supports Sinhala script and Latin)*
- **Published date** *(optional; accepts `YYYY-MM-DD` or full ISO timestamp)*
- **Show advanced** toggle reveals:
  - **Cross sources** (numeric — how many other outlets reported the same story)
  - **Seen count** (numeric — internal de-duplication signal)
  - **Mark as recirculated** (manual override Switch + a *Clear override* link so the override can be unset cleanly)

#### Logic worth showing

**1. Lightweight validation.** The form blocks submission only if the URL is empty:

```js
function handleSubmit() {
  const cleanedUrl = url.trim();
  if (!cleanedUrl) {
    setValidation('Please enter an article URL or domain.');
    return;
  }
  // …assemble payload and call onSubmit(payload)…
}
```

**2. Numeric inputs are sanitized.**

```js
onChangeText={(v) => setCrossCount(v.replace(/[^0-9]/g, ''))}
```

The user can type freely; we only keep the digits. No regex error messages, no fuss.

**3. Date normalization.** If the user types `2026-04-01`, we silently turn it into `2026-04-01T00:00:00Z` so the backend's strict ISO parser is happy:

```js
function normalizeDate(input) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(input)) return `${input}T00:00:00Z`;
  return input;
}
```

**4. Recirculated has three states, not two.** Unset, true, or false. We track `recirculatedSet` separately so we never lie to the backend — if the user didn't touch the switch, we **don't** send the field at all. The backend can then use its own logic to decide.

**5. Disabled while loading.** Every input takes `editable={!loading}` and the submit button shows a spinner instead of the *Analyze* label. The form cannot be double-submitted.

**6. The `Field` sub-component** at the bottom of the file is a tiny helper that renders a label + a red asterisk if the field is required. It removes 90% of the boilerplate from the field declarations above.

---

### Step 7 — The Verdict Screen: `src/components/ResultView.js`

This is the most visually rich component. It takes one prop — `result` — and renders six sections.

#### Section 1: Verdict banner

A big colored card at the top with:

- The tone (green/amber/red) chosen by `alertTone(source_label, source_score)`.
- The label `result.alert || result.source_label` (e.g. *"Trusted Source"*).
- A huge percentage — the trust score — so the verdict is readable at arm's length.

#### Section 2: Badges

A row of pills that summarize secondary signals at a glance:

- The source tier (`Trusted` / `Moderate` / `Risky`).
- The freshness label (`Fresh` / `Recent` / `Old` / `Very Old`) with a small `◷` icon.
- `Republished` if the backend detected recirculation.
- `Unverified source` if the domain is not in the knowledge base.
- `Outdated` if the article is old or very old.
- `.lk source` if the domain ends in `.lk`.
- `Mentions Sri Lanka` if the text mentions the country.
- `Detected: Sinhala / Singlish / English` from the backend's language detector.

Each badge picks its color from `theme.js` so design stays consistent.

#### Section 3: Source card

Publisher name (bold), domain, and a humanized publication age:

```js
function formatAge(days) {
  if (days < 1) return `${hours} hour(s) ago`;
  if (days < 30) return `${d} day(s) ago`;
  if (days < 365) return `${m} month(s) ago`;
  return `${y} year(s) ago`;
}
```

Saying *"3 months ago"* is friendlier than *"92.4 days"*.

#### Section 4: "Why this verdict"

A bullet list of the strings the backend returns in `result.reasons`. Each bullet uses the verdict's tone color so the whole verdict reads as one visual unit.

#### Section 5: Scores

Three `<ScoreBar>` instances showing:

| Bar | Value (0–1) | Color |
|---|---|---|
| Source credibility | `result.source_score` | Verdict tone |
| Temporal freshness | `result.temporal_score` | Freshness tone |
| Assessment confidence | `result.confidence` | Brand primary |

Below them, a single one-liner summary: *"82% trust · 95% fresh · 88% confident"*.

#### Section 6: Feature breakdown

If the backend returns a `breakdown` object, we render five additional bars — one per feature the ML model uses:

```js
const BREAKDOWN_LABELS = {
  registration: 'Registration',
  domain_age:   'Domain age',
  history:      'History',
  editorial:    'Editorial',
  cross:        'Cross-coverage',
};
```

These reveal **why** the score landed where it did. Useful for explainability.

#### Section 7: Diagnostics (collapsible)

A *Show / Hide* toggle that reveals raw model outputs for power users / QA:

- ML prediction (1 = trusted, 0 = not)
- ML confidence
- ML probability of being trusted
- Rule score
- Source tier
- Known-source flag
- Sri Lankan flag
- Mentions-Sri-Lanka flag
- Recirculated flag
- Age in days (numeric)

Hidden by default to keep the main UI calm.

---

### Step 8 — Reusable UI Building Blocks

Three tiny components are used across the app. Each one does one thing well.

#### `Card.js`

A white rounded container with a subtle shadow and border. **Used everywhere** there's a section of content. Saves us from redefining the same `View` styling six times.

```js
export default function Card({ children, style }) {
  return <View style={[styles.card, style]}>{children}</View>;
}
```

#### `Badge.js`

A pill-shaped tag with optional icon. Takes `label`, `fg` (text color), `bg` (background), and optional `icon`. Returns `null` if `label` is empty so callers can render badges conditionally without ternaries everywhere.

#### `ScoreBar.js`

A labeled, colored progress bar for a `0..1` value. Internally clamps the value to `[0, 1]` and renders the percentage to the right of the label, with the bar itself underneath:

```js
const v = clamp(typeof value === 'number' ? value : 0, 0, 1);
const pct = Math.round(v * 100);
```

The clamp is defensive — even if the backend ever sends a slightly out-of-range number, the UI never breaks.

#### `ErrorBanner.js`

A red box at the top of the screen with a title (`Error 400`, `Error 503`, or generic *"Could not analyze"*), the message, and a `×` close button that clears the error in `App.js`.

---

## 6. End-to-End Data Flow (Sequence Diagram)

```
User                AnalyzeForm           App.js              sinhalaCheck.js        FastAPI Backend
 │                       │                  │                       │                       │
 │ types URL + taps      │                  │                       │                       │
 │  Analyze              │                  │                       │                       │
 │──────────────────────▶│                  │                       │                       │
 │                       │ validates URL    │                       │                       │
 │                       │ assembles payload│                       │                       │
 │                       │ onSubmit(payload)│                       │                       │
 │                       │─────────────────▶│                       │                       │
 │                       │                  │ setLoading(true)      │                       │
 │                       │                  │ analyze(payload)      │                       │
 │                       │                  │──────────────────────▶│                       │
 │                       │                  │                       │ POST /analyze         │
 │                       │                  │                       │──────────────────────▶│
 │                       │                  │                       │                       │ rule + ML
 │                       │                  │                       │                       │ + temporal
 │                       │                  │                       │ AnalyzeResponse JSON  │
 │                       │                  │                       │◀──────────────────────│
 │                       │                  │ setResult(data)       │                       │
 │                       │                  │ setLoading(false)     │                       │
 │   ResultView renders  │                  │                       │                       │
 │◀──────────────────────│ ◀────────────────│                       │                       │
```

The whole round-trip is typically **under 1 second** on a healthy backend.

---

## 7. The Backend Contract (Quick Reference)

Frontend ↔ backend agreement, summarized for the client.

### Request — `POST /analyze`

```json
{
  "url": "https://www.adaderana.lk/news/123/sample",
  "text": "Optional article body in en/si/singlish",
  "published_date": "2026-04-01T08:30:00Z",
  "recirculated": false,
  "cross_count": 3,
  "seen_count": 0
}
```

Only `url` is required.

### Response — `AnalyzeResponse`

```json
{
  "alert": "Trusted Source",
  "source_label": "Trusted",
  "source_tier": "Trusted",
  "source_score": 0.87,
  "temporal_score": 0.95,
  "confidence": 0.88,
  "publisher": "Ada Derana",
  "domain": "adaderana.lk",
  "is_known_source": true,
  "is_sri_lankan_source": true,
  "mentions_sri_lanka": true,
  "detected_language": "sinhala",
  "time_label": "Fresh",
  "age_days": 0.42,
  "recirculated": false,
  "ml_prediction": 1,
  "ml_confidence": 0.91,
  "ml_probability_trusted": 0.91,
  "rule_score": 0.83,
  "reasons": [
    "Domain matches a curated trusted Sri Lankan publisher.",
    "Published less than a day ago — freshness is high.",
    "Cross-reported by 3 other sources."
  ],
  "breakdown": {
    "registration": 0.9,
    "domain_age":   0.95,
    "history":      0.88,
    "editorial":    0.8,
    "cross":        0.6
  }
}
```

The frontend renders every field above, but **degrades gracefully** if any of them is missing — every section in `ResultView.js` is guarded with a null/undefined check.

---

## 8. Running the App (Cheat Sheet)

1. **Start the backend** (in `backend/`):
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. **Install frontend deps once** (in `frontend/`):
   ```bash
   npm install
   ```
3. **Start Expo:**
   ```bash
   npm start
   ```
4. **Run on a device:**
   - **Phone:** scan the QR code with the Expo Go app.
   - **Android emulator:** press `a`.
   - **iOS simulator:** press `i`.
   - **Web browser:** press `w`.

The app will print the API base URL it auto-detected at the top of the screen — confirm it matches your machine's LAN IP for physical-device testing.

---

## 9. Talking Points for the Client (Cheat Sheet)

Use these one-liners during the walkthrough:

- **"One screen, three states."** Loading, result, or error — that's the entire app's state machine.
- **"Backend-agnostic UI."** Only `src/api/sinhalaCheck.js` knows the backend exists. Swap it freely.
- **"Themed, not hard-coded."** Every color comes from `theme.js`. Re-skinning is a one-file change.
- **"Multilingual by design."** Inputs accept Sinhala script, Latin, and Singlish; the language is detected on the server and shown back as a badge.
- **"Defensive rendering."** Every section in `ResultView` checks for missing fields before rendering, so the UI never crashes on a partial response.
- **"Zero heavy dependencies."** Just React Native + Expo. Bundle is small, builds are fast.
- **"Production-ready in one config change."** Switch `API_BASE_URL` to the deployed backend, build with EAS, ship.

---

## 10. Suggested Roadmap (Optional Slide)

If the client asks *"what's next?"*, these are natural extensions of the existing architecture:

1. **History tab** — store recent checks in `AsyncStorage` and show them in a second screen.
2. **Share button** — share the verdict card as an image / link.
3. **Push notifications** — alert users when a previously trusted article gets flagged as recirculated.
4. **Authentication & per-user thresholds** — let users tighten or loosen the credibility cut-offs.
5. **Offline mode** — cache the `/sources` list and show *known/unknown* even without a network.
6. **Dark mode** — already trivial because of the theme tokens.

---

## Appendix A — File-by-File One-Line Index

| File | One-line summary |
|---|---|
| `index.js` | Boots the Expo app and registers `App` as the root. |
| `App.js` | The single screen. Owns `loading`, `result`, `error` state. |
| `app.json` | Expo metadata (name, icons, splash). |
| `package.json` | Dependencies and `npm start` script. |
| `src/config.js` | Auto-detects the backend's base URL across phone / emulator / web. |
| `src/theme.js` | Colors, spacing, typography, and tone-mapping helpers. |
| `src/api/sinhalaCheck.js` | The HTTP client. Adds timeouts, parses errors, exposes `analyze()`. |
| `src/components/AnalyzeForm.js` | The input card with URL, text, date, and advanced fields. |
| `src/components/ResultView.js` | The verdict screen — banner, badges, source, reasons, scores, breakdown, diagnostics. |
| `src/components/Card.js` | Re-usable white rounded container with shadow. |
| `src/components/Badge.js` | Re-usable pill-shaped tag with optional icon. |
| `src/components/ScoreBar.js` | Re-usable labeled progress bar for a `0..1` value. |
| `src/components/ErrorBanner.js` | Red banner used when an API call fails. |

---

## Appendix B — Glossary for the Client

- **Hybrid score** — `(rule_score + ML probability) / 2`. The trust number the user sees.
- **Knowledge base** — curated list of Sri Lankan publishers tagged Trusted / Moderate / Blacklisted.
- **Recirculation** — when an old article is re-shared as if it were new.
- **Singlish** — Sinhala written in Latin characters (e.g. *"mama gedara yanawa"*).
- **Cross-coverage** — how many other outlets report the same story (a credibility signal).
- **Confidence** — how sure the model is in its own prediction, separate from how *trusted* the source is.

---

*End of frontend documentation. For backend internals (rule engine, ML model, temporal logic, language detection), refer to `backend/PROJECT_DOCUMENTATION.md`.*
