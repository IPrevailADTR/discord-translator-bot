import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from discord_trad_bot import db
from discord import app_commands
from discord_trad_bot.utils import preserve_user_mentions, restore_mentions, translate_message, detect_language
from discord_trad_bot.constants import SUPPORTED_LANGUAGES
# Import command modules
from discord_trad_bot.commands import admin_commands
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json


# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'status': 'healthy',
                'bot_status': 'online' if bot.is_ready() else 'offline'
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_health_server():
    server = HTTPServer(('0.0.0.0', int(os.getenv('PORT', '8080'))), HealthCheckHandler)
    print(f"Health check server running on port {os.getenv('PORT', '8080')}")
    server.serve_forever()

# Add context menu command for translation
def add_translate_context_menu(bot):
    @app_commands.context_menu(name="Translate")
    async def translate_message_context(interaction: discord.Interaction, message: discord.Message):
        user_lang = await db.get_user_lang(interaction.user.id)
        if not user_lang:
            await interaction.response.send_message(
                "⚠️ You haven't set a language preference yet!\n"
                "Please use `/setlang <language_code>` (or `!setlang <language_code>`) to set your preferred language before using Translate.",
                ephemeral=True
            )
            return

        detected_lang = detect_language(message.content)
        if not detected_lang:
            await interaction.response.send_message(
                "Could not detect the language of the message.", ephemeral=True
            )
            return

        if detected_lang == user_lang:
            await interaction.response.send_message(
                f"This message is already in your preferred language ({user_lang}).", ephemeral=True
            )
            return

        try:
            content_preserved, mention_map = preserve_user_mentions(message.content)
            translated_text = translate_message(content_preserved, user_lang)
            translated_text = restore_mentions(translated_text, mention_map)

            embed = discord.Embed(
                color=discord.Color.blue(),
                description=translated_text
            )
            embed.set_author(
                name=f"Translation for {interaction.user.display_name}",
                icon_url=interaction.user.display_avatar.url
            )
            embed.set_footer(text=f"Original message by {message.author.display_name}")

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print(f"Error processing translation for user {interaction.user.id}: {str(e)}")
            await interaction.response.send_message(
                "Sorry, there was an error translating this message.", ephemeral=True
            )

    bot.tree.add_command(translate_message_context)

class TranslationBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        
    async def setup_hook(self):
        # Add autocomplete for language codes
        @self.tree.command(name="setlang", description="Set your preferred language")
        @app_commands.describe(language="Your preferred language")
        async def setlang(interaction: discord.Interaction, language: str):
            if language not in SUPPORTED_LANGUAGES:
                await interaction.response.send_message(f'`{language}` is not a supported language code. Use `!languages` to see the list of supported codes.', ephemeral=True)
                return
            await db.set_user_lang(interaction.user.id, language)
            await interaction.response.send_message(f'Your preferred language has been set to `{language}`', ephemeral=True)
        print("Registered /setlang command")

        @self.tree.command(name="ping", description="Test if the bot is working")
        async def ping_slash(interaction: discord.Interaction):
            await interaction.response.send_message("Pong!", ephemeral=True)
        print("Registered /ping command")

        @self.tree.command(name="languages", description="List available languages")
        async def languages_slash(interaction: discord.Interaction):
            codes = sorted(SUPPORTED_LANGUAGES)
            chunk_size = 50
            for i in range(0, len(codes), chunk_size):
                await interaction.response.send_message(' '.join(codes[i:i+chunk_size]), ephemeral=True)
        print("Registered /languages command")

        @self.tree.command(name="mylang", description="Show your current language setting")
        async def mylang_slash(interaction: discord.Interaction):
            user_lang = await db.get_user_lang(interaction.user.id)
            if user_lang:
                await interaction.response.send_message(f'Your preferred language is `{user_lang}`.', ephemeral=True)
            else:
                await interaction.response.send_message('You have not set a preferred language yet. Use `/setlang <language_code>`.', ephemeral=True)
        print("Registered /mylang command")

        @self.tree.command(name="help-translate", description="Show help for the translation bot")
        async def help_slash(interaction: discord.Interaction):
            embed = discord.Embed(title="Translation Bot Help", color=discord.Color.blue())
            embed.add_field(
                name="User Commands",
                value=(
                    "`/setlang <language_code>` — Set your preferred language\n"
                    "`/languages` — List available languages\n"
                    "`/mylang` — Show your current language setting\n"
                    "`/ping` — Test if the bot is working"
                ),
                inline=False
            )
            embed.add_field(
                name="How to Translate Messages",
                value=(
                    "• Set your preferred language with `/setlang <language_code>`\n"
                    "• Right-click any message, go to **Apps > Translate** to get a private translation in your language\n"
                    "• All translation features are available in every channel."
                ),
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        print("Registered /help-translate command")
        
        @setlang.autocomplete('language')
        async def language_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
            return [
                app_commands.Choice(name=lang, value=lang)
                for lang in sorted(SUPPORTED_LANGUAGES)
                if current.lower() in lang.lower()
            ][:25]  # Discord limits to 25 choices

        add_translate_context_menu(self)
        print("Registered context menu command (Translate)")

        # Print all registered app commands for debugging
        print("App commands after setup_hook:", [cmd.name for cmd in self.tree.get_commands()])

bot = TranslationBot()

# Register commands
admin_commands.setup(bot)

# --- Bot Events ---
@bot.event
async def on_ready():
    await db.init_db()
    print(f'{bot.user} has connected to Discord!')
    # Print all registered app commands after bot is ready
    print("App commands after on_ready:", [cmd.name for cmd in bot.tree.get_commands()])

@bot.command()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send("Synced commands globally.")

def run_bot():
    """Entry point for the bot when used as a package."""
    # Start the health check server in a separate thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Run the bot
    bot.run(os.getenv('DISCORD_TOKEN'))

# Run the bot if this file is executed directly
if __name__ == '__main__':
    run_bot() 