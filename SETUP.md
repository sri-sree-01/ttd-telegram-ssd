# ttd-telegram-ssd — setup

This folder is a **complete, self-contained repo** for the Telegram SSD worker.
Push it as its own **private** GitHub repo (do NOT put it inside the FlutterFlow
project). Worker files are at the root; the schedule lives in
`.github/workflows/telegram-ssd.yml`.

## 1. Create the repo and push it

On GitHub (github.com/sri-sree-01) → **New repository** → name it
`ttd-telegram-ssd` → set **Private** → Create (don't add a README).

Then, from inside this folder on your computer:

```bash
git init
git add .
git commit -m "Telegram SSD worker"
git branch -M main
git remote add origin https://github.com/sri-sree-01/ttd-telegram-ssd.git
git push -u origin main
```

(If you prefer no command line: on the empty repo page use **uploading an
existing file**, drag in `worker.py`, `parser.py`, `generate_session.py`,
`requirements.txt`, `test_parser.py`, `.gitignore`; then **Add file → Create new
file**, type `.github/workflows/telegram-ssd.yml` as the name, and paste the
workflow contents.)

## 2. Add the 5 repository secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Value |
|---|---|
| `TG_API_ID` | `36856542` |
| `TG_API_HASH` | your api_hash |
| `TG_SESSION` | the long string from `generate_session.py` |
| `SUPABASE_URL` | `https://vglgleibqsrwlmrlwqhx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Settings → API → `service_role` key |

## 3. Run it

Repo → **Actions** tab → enable workflows if prompted → open **telegram-ssd** →
**Run workflow**. Open the run log — it prints how many status messages it
parsed and upserted. Then rows appear in `public.ssd_telegram_status`.

After that it runs automatically every 15 minutes.

## Test the parser offline (optional)
```bash
python test_parser.py
```

## Reminders
- Never commit `TG_SESSION` or the service-role key — secrets only.
- Use a dedicated Telegram account for the session (not your personal one).

## Sarva Darshan (free queue) — Tirumala Live Status bot

`sarva_worker.py` (second step of the same workflow) reads the posts that the
bot **@TirumalaLiveBot** pushes to our Telegram account, keeps only the Sarva
Darshan part (`sarva_parser.py`) and upserts it into `public.sarva_darshan_raw`.
The database then publishes a rounded, nudged snapshot for the app — exact bot
figures never reach the app.

- Uses the SAME 5 secrets — nothing new to add.
- First run: if our chat with the bot is empty it sends `/start` once so the
  bot starts pushing. After that it only listens (nothing is sent).
- Skips itself if it ran < 10 min ago, so the 2/5-min SSD bursts don't hit
  Telegram more often.
- Optional: if the bot ever stops pushing on its own, set env
  `SARVA_REFRESH_CMD` (e.g. the bot's status command from its Menu — the
  admin panel's Sarva Darshan tab shows the command list) to ask for a fresh
  post when the newest one is older than 150 min.
- Test the parser offline: `python test_sarva_parser.py`
- Health: ttd_admin.html → 🛕 Sarva Darshan → Worker.
