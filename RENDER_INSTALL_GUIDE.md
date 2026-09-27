# Deploying Discord Translation Bot on Render (The No-Drama Guide)

This guide will get your packaged Discord bot running on Render for free, with minimal fuss and zero code refactor.

---

## 1. Prerequisites
- A GitHub account ([https://github.com/](https://github.com/))
- A Render account ([https://render.com/](https://render.com/))
- Your Discord bot token (from the Discord Developer Portal)
- Your code pushed to a GitHub repo (with `requirements.txt` and `main.py` at the root)

---

## 2. Prepare Your GitHub Repo
1. Make sure your repo contains:
   - `requirements.txt` with:
     ```
     discord-trad-bot==X.Y.Z
     ```
     (replace X.Y.Z with the latest version)
   - `main.py` with:
     ```python
     from discord_trad_bot import run_bot

     if __name__ == "__main__":
         run_bot()
     ```
2. Push your changes to GitHub.

---

## 3. Create a New Web Service on Render
1. Go to [https://dashboard.render.com/](https://dashboard.render.com/)
2. Click **"New +"** > **"Web Service"**
3. Connect your GitHub account if you haven't already
4. Select your repo and branch

---

## 4. Configure the Service
- **Environment**: Python 3 (Render auto-detects from `requirements.txt`)
- **Build Command**: (leave blank, Render will use `pip install -r requirements.txt` by default)
- **Start Command**: `python main.py`

---

## 5. Set Environment Variables
1. In the Render dashboard, go to the **Environment** tab for your service
2. Add:
   - `DISCORD_TOKEN` (your Discord bot token)
   - `GOOGLE_TRANSLATE_API_KEY` (leave blank or use a dummy value if not needed)

---

## 6. Deploy
1. Click **"Create Web Service"**
2. Wait for the build and deploy to finish
3. Check the logs for any errors
4. If all goes well, your bot will be online and connected to your Discord server!

---

## 7. Updating Your Bot
- Push changes to your GitHub repo
- Render will auto-deploy on every push
- To update the bot version, just change the version in `requirements.txt` and push

---

## 8. Notes & Tips
- The free tier will auto-sleep after 15 minutes of inactivity. For most bots, this is fine.
- If you need persistent uptime, consider a paid plan.
- You can monitor logs and redeploy manually from the Render dashboard.

---

## 9. Need Help?
- Check [Render's Python docs](https://render.com/docs/deploy-python)
- Ask Pierre or open an issue in the repo

---

**Enjoy your zero-drama, always-up-to-date Discord bot!** 