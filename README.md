# Personal Embedded Job Tracker

Checks verified public ATS feeds (Comeet, Lever, Ashby, Greenhouse, plus an optional Jooble Israel aggregator) every ~2 hours, scores postings against your embedded/real-time profile in [`config/profile.yaml`](config/profile.yaml), stores every seen job in SQLite so you are **never alerted twice**, sends new matches to your phone via Telegram, and writes a static [`docs/index.html`](docs/index.html) dashboard.

## Quick start (Windows, Python 3.11+)

```powershell
cd D:\Projects\AI_Search_Work_Agent\job-tracker
pip install -r requirements.txt

# 1) Run unit tests (scoring + deduplication)
python -m unittest discover -s tests -t .

# 2) Dry run across all verified sources (prints matches; does NOT notify or save)
python -m src.main --dry-run

# Dry run a single company by name
python -m src.main --dry-run --only "Mobileye"
```

## Setting up Telegram alerts & optional Gemini

1. **Create a Telegram bot**: message `@BotFather` on Telegram, send `/newbot`, and copy the HTTP API token.
2. **Get your chat ID**: send any message to your new bot, then open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser and copy `"chat":{"id": ...}`.
3. **Save secrets as user environment variables** (never committed to git):

```powershell
setx TELEGRAM_BOT_TOKEN "123456:ABC-DEF..."
setx TELEGRAM_CHAT_ID "987654321"

# Optional: Gemini re-checks borderline jobs (score 30..49) when set
setx GEMINI_API_KEY "AIza..."
```

Open a new PowerShell window after `setx` so the variables take effect, then run:

```powershell
python -m src.main
```

This creates `data/jobs.db`, sends Telegram messages for new matches, and writes `docs/index.html` (open it in any browser).

## Schedule every 2 hours on Windows (Task Scheduler)

```powershell
powershell -ExecutionPolicy Bypass -File .\register_task.ps1
```

- Runs `run.ps1` every 2 hours in a hidden window, and runs immediately on wake if the PC was asleep (`StartWhenAvailable`).
- Logs each run to `data/tracker.log` and the `runs` table in `data/jobs.db`.
- Remove anytime with: `Unregister-ScheduledTask -TaskName JobTracker -Confirm:$false`.

## Adding a company (`config/sources.yaml` only)

Edit [`config/sources.yaml`](config/sources.yaml)—no code changes needed:

- **Greenhouse** (`https://boards.greenhouse.io/<board>`):
  ```yaml
  - name: Example Corp
    ats: greenhouse
    board: examplecorp
  ```
- **Lever** (`https://jobs.lever.co/<board>` or `https://jobs.eu.lever.co/<board>`):
  ```yaml
  - name: Example Corp
    ats: lever
    region: eu        # omit for global jobs.lever.co
    board: examplecorp
  ```
- **Ashby** (`https://jobs.ashbyhq.com/<board>`):
  ```yaml
  - name: Example Corp
    ats: ashby
    board: examplecorp
  ```
- **Comeet** (`https://www.comeet.com/jobs/<slug>/<uid>`): view page source on the public Comeet careers page and copy `company_uid` and `token` from `COMPANY_DATA`:
  ```yaml
  - name: Example Corp
    ats: comeet
    uid: "12.00A"
    token: "12A..."
  ```

## Aggregator evaluation (Israel coverage)

| Aggregator | Israel support | Verdict |
| :--- | :--- | :--- |
| **Adzuna API** | Not supported (`il` is not in the 19 supported country codes) | Skipped |
| **Careerjet API v4** | Has `he_IL` / `en_IL`, but requires forwarding a real web visitor's `user_ip`, `user_agent`, and publisher `Referer` URL | Not suitable for a local script |
| **Jooble REST API** (`il.jooble.org`) | Covers Israel via `POST https://il.jooble.org/api/{api_key}` | Implemented in [`src/sources/aggregator.py`](src/sources/aggregator.py), disabled by default (`enabled: false`) because free keys have a request quota. Set `JOOBLE_API_KEY` and flip `enabled: true` in `sources.yaml` if desired. |

## Needs manual check / unsupported ATS

These Israeli embedded/defense/semiconductor employers do **not** use public Greenhouse/Lever/Ashby/Comeet boards (they use custom portals, Workday, SuccessFactors, or Workable), so they are not in `sources.yaml`:

- **Elbit Systems** — custom portal (`https://elbitsystems.com/careers/`)
- **Israel Aerospace Industries (IAI)** — custom portal (`https://www.iai.co.il/careers`)
- **Rafael Advanced Defense Systems** — custom portal (`https://career.rafael.co.il/`)
- **NVIDIA Israel / Mellanox** — Workday (`https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite`)
- **Intel Israel** — Workday (`https://intel.wd1.myworkdayjobs.com/External`)
- **Qualcomm Israel (incl. Autotalks)** — Workday (`https://qualcomm.wd5.myworkdayjobs.com/External`)
- **Apple Israel** — custom portal (`https://jobs.apple.com/en-il/search?location=israel-ISR`)
- **Hailo** — custom WordPress/Comeet-embedded page without public token (`https://hailo.ai/careers/`)
- **Valens Semiconductor** — custom portal (`https://www.valens.com/careers/`)
- **Vayyar Imaging** — Workable (`https://vayyar.workable.com/`)
- **Pliops / Speedata / StoreDot / GuardKnox** — custom or unindexed boards; check company career pages directly.
