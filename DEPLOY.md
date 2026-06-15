# Self-hosting for family use (private, via Tailscale)

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
git checkout claude/ceo-health-records-xc2kgo
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

## 5. Keep it running
- **macOS/Linux:** run under `tmux`/`screen`, or make a `systemd` service / `launchd` agent.
- **Raspberry Pi:** a `systemd` unit that runs the uvicorn command on boot is ideal.
- Updates: `git pull` then restart.

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
