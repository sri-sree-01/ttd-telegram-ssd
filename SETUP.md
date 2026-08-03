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
