# SinhalaCheck mobile app

React Native + Expo app for Android and iOS. The three primary screens are:

- **Home** — paste text, optionally enter URL/date/corroboration, choose a score-only or
  enhanced result, and submit to the Fusion API.
- **Result** — score/verdict; enhanced mode also shows signal breakdown, temporal warning,
  and up to five bilingual LIME reasons. Research mode adds a decision/trust response form.
- **History** — open the last 100 analyses, share anonymous study rows as CSV text, or clear local
  data.

The app calls the Fusion API's `POST /analyze` endpoint. That API continues to call Module 1
and Module 2 through their HTTP contracts; the model is not bundled into the app.

## Run locally

1. Start the existing backend from `sinhalacheck` with `python run_all.py`.
2. Install mobile dependencies once:

```powershell
Set-Location .\wishmitha\mobile
npm install
```

3. To allow a physical phone to connect, set `SINHALACHECK_HOST=0.0.0.0` before starting
   the backend, and permit port 8000 through the development computer's firewall on a
   trusted private network only:

```powershell
$env:SINHALACHECK_HOST = "0.0.0.0"
python .\run_all.py
```

   The services have no authentication; do not bind them to a public network.
4. Copy `.env.example` to `.env`. For Expo Go on an actual phone, replace
   `EXPO_PUBLIC_API_URL` with the development computer's reachable LAN address, for example
   `http://192.168.1.20:8000`. `localhost` on the phone points to the phone itself.
5. Start Expo:

```powershell
npm start -- --lan
```

Scan the QR code in Expo Go on Android or iOS. Ensure the phone and computer share a network.

## User-study mode

The study UI is compiled out unless `EXPO_PUBLIC_ENABLE_RESEARCH=true`,
`EXPO_PUBLIC_ETHICS_APPROVED=true`, and `EXPO_PUBLIC_STUDY_GROUP` is set to `A` or `B`.
It also requires the exact approved participant consent wording in
`EXPO_PUBLIC_CONSENT_TEXT`; otherwise study collection remains disabled.
Build two separate app variants with their assigned group fixed; participants cannot switch
conditions. Keep study/approval flags false until approval is confirmed. A populated,
reviewed `assets/study-items.json` pack is also required. Build that pack using
[`../research/prepare_study_items.py`](../research/prepare_study_items.py); the participant
pack excludes gold labels and the evidence key.

The facilitator assigns Group A (score only) or Group B (score + LIME + temporal warning).
Participants enter an anonymous code supplied by the facilitator and must consent before
each recorded trial. The app records item ID, group, participant decision, 1–7 trust rating,
and result-view-to-submit duration in local AsyncStorage only. No research response is sent
to the Fusion API. Share CSV text from History and analyse alongside the private answer key
using the research scripts. These are implementation tools, not ethics approval or evidence that the
planned n=40 study has happened.
