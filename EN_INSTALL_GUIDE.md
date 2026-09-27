# Discord Translation Bot Installation Guide (Render Version)

This guide explains how to install the Discord translation bot on Render using the package version. It's much simpler than the old way!

---

## 1. Prerequisites
- A Discord account with admin rights on your server
- A GitHub account ([https://github.com/](https://github.com/))
- A Render account ([https://render.com/](https://render.com/))
- A web browser (Chrome, Firefox, Safari, etc.)

> 💡 **Important Note:** You don't need to install Python or any other tools on your computer. Everything happens directly on Render (but you do need GitHub for your project files).

---

## 2. Create a Discord Application and Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application"
3. Give your application a name (e.g., "Trad-Bot")
4. In the left menu, click "Bot" then "Add Bot"
5. Click "Reset Token" and copy the token (keep it secret!)
6. Enable the following permissions:
   - PRESENCE INTENT
   - SERVER MEMBERS INTENT
   - MESSAGE CONTENT INTENT

---

## 3. Invite the Bot to Your Discord Server

1. In the left menu, click "OAuth2" > "URL Generator"
2. Check the boxes:
   - bot
   - applications.commands
3. Under "Bot Permissions", check:
   - VIEW CHANNELS
   - SEND MESSAGES
   - READ MESSAGE HISTORY
   - USE SLASH COMMANDS
4. Copy the generated link at the bottom, open it in your browser, and invite the bot to your server.

---

## 4. Prepare the GitHub Repository

1. Create a new GitHub repository (or use an existing one)
2. Add a `requirements.txt` file with:
   ```
   discord-trad-bot==X.Y.Z
   ```
   (replace X.Y.Z with the latest package version)
3. Add a `main.py` file with:
   ```python
   from discord_trad_bot import run_bot

   if __name__ == "__main__":
       run_bot()
   ```
4. Push these files to GitHub (commit + push)

---

## 5. Create a Render Web Service

1. Go to [https://dashboard.render.com/](https://dashboard.render.com/)
2. Click "New +" > "Web Service"
3. Connect your GitHub account if you haven't already
4. Select your repo and branch

---

## 6. Configure the Service
- **Environment**: Python 3 (Render auto-detects from `requirements.txt`)
- **Build Command**: (leave blank, Render will use `pip install -r requirements.txt` by default)
- **Start Command**: `python main.py`

---

## 7. Set Environment Variables
1. In the Render dashboard, go to the "Environment" tab for your service
2. Add:
   - DISCORD_TOKEN (your Discord bot token)
   - GOOGLE_TRANSLATE_API_KEY (leave blank or use a dummy value if not needed)

---

## 8. Deploy and Launch the Bot

1. Click "Create Web Service"
2. Wait for the build and deploy to finish
3. Check the logs for any errors
4. If all goes well, your bot will be online and connected to your Discord server!

---

## 9. Update the Bot

When a new version is available:
1. Simply change the version number in `requirements.txt` on GitHub
2. Push the change (commit + push)
3. Render will automatically update the bot

---

## 10. Using the Bot

The commands remain the same:
- `!setlang fr` : Set your language
- `!mylang` : See your current language
- `!languages` : See supported languages
- `!settranschannel` : Set the translation channel

---

## Need Help?

- Ask Pierre or send a screenshot of your problem!

---

**Happy gaming and happy translating!** 🎮🌍 