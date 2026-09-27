# Discord Translation Bot

A Discord bot that automatically translates messages in a designated channel to each user's preferred language while maintaining Discord's rich formatting.

---

## 📦 Deployment & Installation Guide
- [Install on Render (English)](RENDER_INSTALL_GUIDE.md)

---

## Features

- Automatic translation of messages in a designated channel
- User language preferences
- Preserves Discord formatting (emojis, mentions, etc.)
- Free to use (uses Google Translate API free tier)

## Setup (Local Development)

1. **Clone this repository**
2. **Create a virtual environment:**
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Upgrade pip (required for editable installs with modern packaging):**
   ```
   python -m pip install --upgrade pip
   ```
4. **Install the package in editable/development mode from the project root:**
   ```
   pip install -e .
   ```
   This makes the `discord_trad_bot` package available for import and development, and any code changes are picked up instantly.

5. **Create a `.env` file in the project root with your Discord bot token and Google Translate API key:**
   ```
   DISCORD_TOKEN=your_discord_bot_token
   GOOGLE_TRANSLATE_API_KEY=your_google_translate_api_key
   ```

## Running the Bot Locally

You have several options:

- **Recommended:**  
  If you have a `__main__.py` in `src/discord_trad_bot/` (recommended for package-style projects), run:
  ```
  python -m discord_trad_bot
  ```

- **Directly:**  
  Or, run the main file directly:
  ```
  python src/discord_trad_bot/main.py
  ```

- **Via entry point (if set up in pyproject.toml):**  
  If you have a script entry point defined, you can also run:
  ```
  discord-trad-bot
  ```

- **Using the Makefile (shortcut for dev):**
  If you prefer, you can use the provided Makefile command to run the bot in development mode:
  ```
  make dev
  ```
  This is equivalent to running `python src/discord_trad_bot/main.py` and is handy for quick local testing.

## Configuration

Create a `.env` file with the following variables:
```
DISCORD_TOKEN=your_discord_bot_token
GOOGLE_TRANSLATE_API_KEY=your_google_translate_api_key
```

## Commands

### User Commands
- `!setlang <language_code>` — Set your preferred language
- `!mylang` — Show your current language setting
- `!languages` — List available languages
- `!ping` — Test if the bot is working

### Admin Commands
- `!settranschannel <#channel>` — Set the translation channel
- `!addtranschannel <#channel>` — Add a new translation channel
- `!removetranschannel <#channel>` — Remove a translation channel
- `!listtranschannels` — List all translation channels
- `!setchannellang <#channel> <language_code>` — Set the default language for a translation channel
- `!debugdb` — Debug command to check database schema and content
- `!transstatus` — Show bot status and usage

---

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

---

## License

MIT
