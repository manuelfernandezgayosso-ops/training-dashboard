# 🌐 Deploy Your Training Dashboard Online

Access your dashboard from anywhere:
`https://YOUR-NAME.onrender.com`

---

## What you need (already done)
- ✅ GitHub account
- ✅ Render account (linked to GitHub)
- ✅ Strava API credentials

---

## Step 1 — Get your Strava Refresh Token

You need a one-time token that lets the server pull your Strava data.

On your Mac, run:
```bash
cd ~/Downloads/training_v2
python3 -c "
import json
from pathlib import Path
t = json.load(open(Path('~/Documents/training_data/.strava_token.json').expanduser()))
print('REFRESH TOKEN:', t['refresh_token'])
"
```
Copy the long string it prints. You'll need it in Step 4.

---

## Step 2 — Put this folder on GitHub

On your Mac, open Terminal:

```bash
cd ~/Downloads/training_web

# Initialize git
git init
git add .
git commit -m "Initial training dashboard"

# Push to GitHub (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/training-dashboard.git
git branch -M main
git push -u origin main
```

If GitHub asks for a password, use a Personal Access Token:
- Go to github.com → Settings → Developer Settings → Personal Access Tokens → Generate New Token
- Give it "repo" permissions
- Use it as your password

---

## Step 3 — Create the repo on GitHub first

Before pushing, create the repo:
1. Go to github.com
2. Click the green **New** button
3. Name it `training-dashboard`
4. Set to **Private**
5. Click **Create repository**
6. Then run the Terminal commands from Step 2

---

## Step 4 — Deploy on Render

1. Go to **render.com** and log in
2. Click **New → Web Service**
3. Connect your GitHub repo (`training-dashboard`)
4. Render auto-detects the settings from `render.yaml`
5. Click **Advanced** and add these Environment Variables:

| Key | Value |
|-----|-------|
| `STRAVA_CLIENT_ID` | `216131` |
| `STRAVA_CLIENT_SECRET` | your Strava secret |
| `STRAVA_REFRESH_TOKEN` | the token from Step 1 |
| `ATHLETE_NAME` | `Anton` |
| `VOLUME_PROFILE` | `high` |

6. Click **Create Web Service**

Render builds and deploys in ~3 minutes.

---

## Step 5 — Your URL

Once deployed, your dashboard is live at:
```
https://ironman-training-dashboard.onrender.com
```
(or whatever name Render assigns — you'll see it in the dashboard)

Bookmark it on your phone. Done.

---

## Adding a custom domain (optional, ~$12/year)

1. Buy a domain at **namecheap.com** (e.g. `manuel-training.com`)
2. In Render: Settings → Custom Domains → Add Domain
3. Follow the DNS instructions Render provides
4. Takes ~10 minutes to go live

---

## Updating the app

Any time you want to change something (add a race, tweak the plan):
1. Edit the file on your Mac
2. Run:
```bash
cd ~/Downloads/training_web
git add .
git commit -m "Update"
git push
```
Render automatically redeploys in ~2 minutes.

---

## Troubleshooting

**Dashboard shows no data**
Check that your `STRAVA_REFRESH_TOKEN` is correct in Render environment variables.

**"Application error" on Render**
Go to Render → your service → Logs to see what went wrong.

**Token expired**
Re-run Step 1 on your Mac to get a fresh refresh token, update it in Render.
