# Option A — Online (Render), reachable from any browser

This deploys the **full app** to the cloud so you get a public URL (with login).
Tradeoff: your data lives on the host's server, and the persistent disk needs a
paid instance (Render Starter, ~$7/mo) so data survives restarts.

1. Push this repo to GitHub (can be **private**). It includes `Dockerfile` + `render.yaml`.
2. Go to **https://render.com**, sign up, and connect your GitHub.
3. **New + → Blueprint** → pick this repo → choose the branch
   `claude/iceland-trip-webpage-nsmw6e` → **Apply**. Render reads `render.yaml`
   and creates the service + a 1 GB disk + a session secret.
4. Before or right after the first deploy, go to the service's **Environment** tab
   and set `ICELAND_TRIP_PASSWORD` to a real passphrase — the blueprint leaves it
   unset on purpose so the shared default (`vatnajokull`) isn't sitting in public
   source once the app is reachable from the internet.
5. Wait for the build, then open the URL it gives you (e.g. `https://ceo-health.onrender.com`).
6. **Create your profile**, then go to **Upload → Import data files** and load your
   CSVs + reports JSON (from the data bundle) — or upload lab PDFs directly.
7. (Optional) In the Render dashboard → Environment, add `ANTHROPIC_API_KEY` to
   enable the AI features.

**Iceland trip photos:** once deployed, the album is at `<your-url>/iceland-trip/`
(e.g. `https://ceo-health.onrender.com/iceland-trip/`) — share that link with family.
It's gated by `ICELAND_TRIP_PASSWORD` (step 4 above), completely separate from the
health app's per-patient login, and photos persist on the same disk as everything else.

To host other family members: each one just **creates their own profile** at the same
URL (data is isolated per person). You're the admin (first profile).

Privacy note: on a public host, treat the data as sensitive — use strong passwords,
keep the URL private, and prefer the Tailscale option below if you'd rather keep data
entirely off third-party servers.

---

# Option B — Self-hosting for family use (private, via Tailscale)

This runs the **full app** on one always-on machine at home and lets family members
reach it from anywhere over **Tailscale** — a free private network (WireGuard VPN).
Your health data never touches the public internet, and each person has their own
login + isolated data.

## Why this setup
- **Private:** the server binds locally; only devices on *your* Tailscale network can reach it.
- **Multi-user:** each family member registers a profile; data is isolated per profile.
- **Low effort:** no domains, certificates, or cloud servers to manage.

## 1. Pick a host
Any always-on computer works: a spare laptop/mini-PC, a Mac, or a Raspberry Pi (4/5).
Install **Python 3.11+**, **Node 18+**, **git**.

## 2. Set up the app
```bash
git clone https://github.com/luizros2010-max/Ceo_health.git
cd Ceo_health
git checkout claude/iceland-trip-webpage-nsmw6e
cp .env.example .env
# edit .env: set a strong SECRET_KEY (so logins survive restarts), keep REQUIRE_AUTH=true.
# python -c "import secrets;print(secrets.token_hex(32))"   # generates one
```

By default the server binds to `127.0.0.1`. To let other devices on your Tailscale
network reach it, bind to all interfaces — start it with:
```bash
./start.sh            # builds, then serves on 127.0.0.1:8000
# For Tailscale access, run uvicorn on 0.0.0.0 instead:
source .venv/bin/activate && (cd frontend && npm run build)
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```
> Binding to `0.0.0.0` is safe here **only because Tailscale gates who can connect.**
> Don't port-forward 8000 on your router.

## 3. Install Tailscale (free)
1. Create a free account at https://tailscale.com and install Tailscale on the **host**
   and on each **family member's phone/laptop**. Add them to your tailnet (or share the
   machine via Tailscale's device sharing).
2. On the host, run `tailscale ip -4` to get its Tailscale address (e.g. `100.x.y.z`).
3. Family opens **`http://100.x.y.z:8000`** in any browser — from anywhere.
   (Optional: enable **MagicDNS** and use `http://<hostname>:8000`.)

## 4. First run — accounts
- The **first** profile registered claims any data already loaded (your records).
- Each additional family member taps **"Create a new profile"** → their data is separate.
- Everyone signs in with their own username/password.

## 5. Keep it running (auto-start on boot)
A ready-made **systemd** service is included:
```bash
sudo cp deploy/ceo-health.service /etc/systemd/system/
# edit User= and WorkingDirectory= in the file to match your machine
sudo systemctl daemon-reload && sudo systemctl enable --now ceo-health
journalctl -u ceo-health -f          # logs
```
It runs `deploy/serve.sh` (builds the frontend if needed, then serves on `0.0.0.0:8000`).
Updates: `git pull` then `sudo systemctl restart ceo-health`.
- **macOS:** a ready **launchd** agent is included:
  ```bash
  cp deploy/com.ceohealth.app.plist ~/Library/LaunchAgents/
  # edit the YOURNAME paths inside the plist, then:
  launchctl load -w ~/Library/LaunchAgents/com.ceohealth.app.plist
  ```
  Update after `git pull`: `launchctl kickstart -k gui/$(id -u)/com.ceohealth.app`.

## Managing family members (admin)
The **first** profile created is the **family admin**. Signed in as admin, a
**"Family Profiles"** page appears where you can **add members, reset passwords, and
remove profiles** (deleting a profile removes that person's data). Members only ever
see their own data.

## 6. Back up your data
Everything lives in `data/` (the SQLite DB + uploaded files). Back it up regularly:
```bash
cp -r data ~/ceo_health_backup_$(date +%F)
```

## Notes & limits
- This is auth for a **small trusted group on a private network**, not a hardened public
  service. Keep `SECRET_KEY` secret; use real passwords.
- For AI features set `ANTHROPIC_API_KEY`; for Oura set `OURA_TOKEN` (each profile syncs
  its own Oura data on demand).
- Prefer not to expose this to the public internet. If you must, put it behind HTTPS + a
  reverse proxy and treat it as sensitive PHI.
