# Deploying NOMinate on an Oracle Cloud "Always Free" VM

This runs the whole app — Postgres, the API, and the frontend — on one small
always-on server. Because nothing ever spins down, **there is no cold start**:
a visitor to your resume link hits a warm server every time, for $0/month.

The stack (one `docker compose up` brings it all up):

```
             ┌─────────────────────── your VM ───────────────────────┐
 visitor ──▶ │  Caddy (HTTPS)  ──/──▶ React static files              │
   :443      │       │          ──/api,/auth,/health──▶ API (gunicorn)│
             │       │                                      │         │
             │   Let's Encrypt                          Postgres      │
             └────────────────────────────────────────────────────────┘
```

Caddy terminates HTTPS (auto Let's Encrypt cert), serves the built React app,
and reverse-proxies API routes to gunicorn. The API runs the recommender in
**NumPy** (no PyTorch), so the image is small and boots in seconds.

---

## Why this setup

- **Oracle Always Free** gives a genuinely always-on VM at no cost (unlike
  Render/Railway free tiers, which sleep when idle → cold starts).
- **One domain, same origin** for site + API means no CORS headaches and one TLS
  cert. Google OAuth also needs a single stable HTTPS origin — this gives it one.
- **Everything in Docker Compose** so the box is reproducible and `restart:
  unless-stopped` brings it back after any reboot.

Honest trade-offs to know: you now own a server (updates, the occasional reboot),
Oracle has historically reclaimed *idle* Always-Free instances (this one won't be
idle), and ARM capacity in a given region can be scarce at signup — pick another
availability domain/region if creation fails.

---

## One-time setup

### 1. Create the VM
1. Sign up at cloud.oracle.com and complete the Always Free onboarding.
2. **Compute → Instances → Create instance.**
   - Image: **Ubuntu 22.04/24.04**.
   - Shape: **Ampere (ARM, `VM.Standard.A1.Flex`)** — Always Free allows up to
     4 OCPU / 24 GB across your free ARM allotment. 1 OCPU / 6 GB is plenty here.
     (The images in this stack all have arm64 builds, so ARM is fine.)
   - Add your SSH public key.
3. Note the instance's **public IP**.

### 2. Open the ports
Oracle blocks inbound traffic in two places — open **both**:
1. **VCN security list** (Networking → your VCN → Security Lists → default):
   add ingress rules for TCP **80** and **443** from `0.0.0.0/0`.
2. **On the VM** (Oracle Ubuntu images ship restrictive iptables):
   ```sh
   sudo iptables -I INPUT 5 -p tcp --dport 80  -j ACCEPT
   sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
   sudo netfilter-persistent save
   ```

### 3. Point a domain at the IP
Google OAuth and Let's Encrypt both need a real domain (not a bare IP).
- Free option: **DuckDNS** — create e.g. `nominate.duckdns.org` and set it to the
  VM's public IP. (Any domain/registrar works; just create an `A` record → IP.)

### 4. Install Docker
SSH in (`ssh ubuntu@<public-ip>`), then:
```sh
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # log out/in so `docker` works without sudo
```

### 5. Deploy
```sh
git clone <your-repo-url> NOMinate
cd NOMinate/deploy
cp .env.example .env
nano .env        # fill in domain, DB password, secrets, and API keys
docker compose up -d --build
```
Caddy fetches the HTTPS cert automatically on first boot (this needs port 80
reachable and DNS already pointing at the box). Check it's healthy:
```sh
docker compose ps
docker compose logs -f web api
curl https://<your-domain>/health
```

### 6. Update Google OAuth
In Google Cloud Console → your OAuth client → **Authorized JavaScript origins**,
add `https://<your-domain>`. (Remove the old Render origin if you like.)

---

## Day-to-day

| Task | Command (run in `deploy/`) |
|------|----------------------------|
| Ship new code | `git pull && docker compose up -d --build` |
| View logs | `docker compose logs -f api` |
| Restart one service | `docker compose restart api` |
| Stop everything | `docker compose down` (data survives in volumes) |
| DB shell | `docker compose exec db psql -U nominate nominate` |
| Backup DB | `docker compose exec db pg_dump -U nominate nominate > backup.sql` |

Postgres data lives in the `dbdata` volume and the TLS cert in `caddydata`, so
`down`/`up` and reboots don't lose anything. `docker compose down -v` **deletes**
those volumes — don't use `-v` unless you mean it.

## Retraining the model
Training still uses PyTorch and runs off the server (locally). It writes both
`model.pt` and the NumPy `model_weights.npz` the server actually loads:
```sh
cd backend
pip install -r requirements-train.txt
python -m ml.train
```
Commit the updated `ml/checkpoints/` and redeploy (`docker compose up -d --build`).
