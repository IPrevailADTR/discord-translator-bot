import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from discord_trad_bot import db
from discord import app_commands
from discord_trad_bot.utils import (
    preserve_user_mentions,
    restore_mentions,
    translate_message,
    detect_language,
)
from discord_trad_bot.constants import SUPPORTED_LANGUAGES
from discord_trad_bot.commands import admin_commands
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json


# Load environment variables
load_dotenv()


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

# Put the Discord channel ID here through Render environment
# variables using:
#
# TRANSLATION_CHANNEL_ID = your_channel_id
#
# If left blank/0, automatic translation will run in all
# server text channels.
TRANSLATION_CHANNEL_ID = int(
    os.getenv('TRANSLATION_CHANNEL_ID', '0') or '0'
)


# ---------------------------------------------------------
# Bot setup
# ---------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# ---------------------------------------------------------
# Render health check
# ---------------------------------------------------------

class HealthCheckHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header(
                'Content-type',
                'application/json'
            )
            self.end_headers()

            response = {
                'status': 'healthy',
                'bot_status':
                    'online' if bot.is_ready() else 'offline'
            }

            self.wfile.write(
                json.dumps(response).encode()
            )

        else:
            self.send_response(404)
            self.end_headers()


def run_health_server():
    server = HTTPServer(
        (
            '0.0.0.0',
            int(os.getenv('PORT', '8080'))
        ),
        HealthCheckHandler
    )

    print(
        f"Health check server running on port "
        f"{os.getenv('PORT', '8080')}"
    )

    server.serve_forever()


# ---------------------------------------------------------
# Manual Translate context menu
# ---------------------------------------------------------

def add_translate_context_menu(bot):

    @app_commands.context_menu(
        name="Translate"
    )
    async def translate_message_context(
        interaction: discord.Interaction,
        message: discord.Message
    ):
        user_lang = await db.get_user_lang(
            interaction.user.id
        )

        if not user_lang:
            await interaction.response.send_message(
                "You haven't set a language preference yet. "
                "Use `/setlang` first.",
                ephemeral=True
            )
            return

        detected_lang = await asyncio.to_thread(
            detect_language,
            message.content
        )

        if not detected_lang:
            await interaction.response.send_message(
                "Could not detect the language of the message.",
                ephemeral=True
            )
            return

        if detected_lang == user_lang:
            await interaction.response.send_message(
                f"This message is already in "
                f"your preferred language ({user_lang}).",
                ephemeral=True
            )
            return

        try:
            content_preserved, mention_map = (
                preserve_user_mentions(
                    message.content
                )
            )

            translated_text = await asyncio.to_thread(
                translate_message,
                content_preserved,
                user_lang
            )

            translated_text = restore_mentions(
                translated_text,
                mention_map
            )

            embed = discord.Embed(
                color=discord.Color.blue(),
                description=translated_text
            )

            embed.set_author(
                name=(
                    f"Translation for "
                    f"{interaction.user.display_name}"
                ),
                icon_url=(
                    interaction.user.display_avatar.url
                )
            )

            embed.set_footer(
                text=(
                    f"Original message by "
                    f"{message.author.display_name}"
                )
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        except Exception as e:
            print(
                f"Manual translation error: {e}"
            )

            await interaction.response.send_message(
                "Sorry, there was an error translating "
                "this message.",
                ephemeral=True
            )

    bot.tree.add_command(
        translate_message_context
    )


# ---------------------------------------------------------
# Automatic translation
# ---------------------------------------------------------

async def automatic_translate_message(
    message: discord.Message
):

    # Only translate messages in guild channels.
    if message.guild is None:
        return

    # Ignore bots.
    if message.author.bot:
        return

    # If a translation channel has been configured,
    # only translate messages from that channel.
    if (
        TRANSLATION_CHANNEL_ID
        and message.channel.id != TRANSLATION_CHANNEL_ID
    ):
        return

    content = message.content.strip()

    if not content:
        return

    # Don't translate bot-style commands.
    if content.startswith('!'):
        return

    # Detect source language.
    detected_lang = await asyncio.to_thread(
        detect_language,
        content
    )

    if not detected_lang:
        print(
            "Could not detect language for message."
        )
        return

    # Get everyone who has selected a language.
    preferences = await db.get_all_user_prefs()

    # Group recipients by destination language.
    recipients_by_language = {}

    for user_id, user_lang, auto_translate in preferences:

        if not auto_translate:
            continue

        try:
            target_user_id = int(user_id)
        except (TypeError, ValueError):
            continue

        # Don't DM the person who sent the message.
        if target_user_id == message.author.id:
            continue

        # No translation needed when the user's language
        # is already the language of the message.
        if user_lang == detected_lang:
            continue

        # Only send to members of this server.
        member = message.guild.get_member(
            target_user_id
        )

        if member is None:
            continue

        recipients_by_language.setdefault(
            user_lang,
            []
        ).append(member)

    if not recipients_by_language:
        return

    # Preserve mentions while translating.
    content_preserved, mention_map = (
        preserve_user_mentions(
            content
        )
    )

    # Translate once per destination language.
    for destination_lang, members in (
        recipients_by_language.items()
    ):

        try:
            translated_text = await asyncio.to_thread(
                translate_message,
                content_preserved,
                destination_lang
            )

            translated_text = restore_mentions(
                translated_text,
                mention_map
            )

        except Exception as e:
            print(
                f"Translation error for "
                f"{destination_lang}: {e}"
            )
            continue

        # Build the DM embed.
        embed = discord.Embed(
            title="Automatic Translation",
            description=translated_text,
            color=discord.Color.blue(),
            url=message.jump_url
        )

        embed.set_author(
            name=(
                f"{message.author.display_name} "
                f"in #{message.channel.name}"
            ),
            icon_url=(
                message.author.display_avatar.url
            )
        )

        embed.set_footer(
            text=(
                f"Original language: {detected_lang} "
                f"• Your language: {destination_lang}"
            )
        )

        # Send to every opted-in member using that language.
        for member in members:

            try:
                await member.send(
                    embed=embed,
                    allowed_mentions=discord.AllowedMentions.none()
                )

                print(
                    f"Sent {destination_lang} translation "
                    f"to {member} for message "
                    f"{message.id}"
                )

            except discord.Forbidden:
                print(
                    f"Cannot DM {member}; "
                    f"their DMs may be disabled."
                )

            except discord.HTTPException as e:
                print(
                    f"Discord DM error for {member}: {e}"
                )

            # Small delay to avoid hammering Discord.
            await asyncio.sleep(0.2)


# ---------------------------------------------------------
# Bot class
# ---------------------------------------------------------

class TranslationBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):

        # ---------------------------------------------
        # /setlang
        # ---------------------------------------------

        @self.tree.command(
            name="setlang",
            description="Set your preferred language"
        )
        @app_commands.describe(
            language="Your preferred language code"
        )
        async def setlang(
            interaction: discord.Interaction,
            language: str
        ):

            if language not in SUPPORTED_LANGUAGES:
                await interaction.response.send_message(
                    f'`{language}` is not a supported '
                    f'language code.',
                    ephemeral=True
                )
                return

            await db.set_user_lang(
                interaction.user.id,
                language
            )

            await interaction.response.send_message(
                f'Your preferred language has been set '
                f'to `{language}`.\n\n'
                f'Automatic translations are now enabled '
                f'for you. Use `/autotranslate false` '
                f'to turn them off.',
                ephemeral=True
            )

        print(
            "Registered /setlang command"
        )

        # ---------------------------------------------
        # /autotranslate
        # ---------------------------------------------

        @self.tree.command(
            name="autotranslate",
            description="Turn automatic translation DMs on or off"
        )
        @app_commands.describe(
            enabled="Enable or disable automatic translations"
        )
        async def autotranslate(
            interaction: discord.Interaction,
            enabled: bool
        ):

            user_lang = await db.get_user_lang(
                interaction.user.id
            )

            if not user_lang:
                await interaction.response.send_message(
                    "Set your language first with `/setlang`.",
                    ephemeral=True
                )
                return

            await db.set_auto_translate(
                interaction.user.id,
                enabled
            )

            if enabled:
                response = (
                    "Automatic translations are now **ON**."
                )
            else:
                response = (
                    "Automatic translations are now **OFF**."
                )

            await interaction.response.send_message(
                response,
                ephemeral=True
            )

        print(
            "Registered /autotranslate command"
        )

        # ---------------------------------------------
        # /ping
        # ---------------------------------------------

        @self.tree.command(
            name="ping",
            description="Test if the bot is working"
        )
        async def ping_slash(
            interaction: discord.Interaction
        ):
            await interaction.response.send_message(
                "Pong!",
                ephemeral=True
            )

        print(
            "Registered /ping command"
        )

        # ---------------------------------------------
        # /languages
        # ---------------------------------------------

        @self.tree.command(
            name="languages",
            description="List available languages"
        )
        async def languages_slash(
            interaction: discord.Interaction
        ):

            codes = sorted(
                SUPPORTED_LANGUAGES
            )

            # Discord allows 2000 characters per normal
            # response, so split into manageable chunks.
            chunks = []

            current = ""

            for code in codes:

                if len(current) + len(code) + 1 > 1900:
                    chunks.append(current)
                    current = code
                else:
                    if current:
                        current += " "

                    current += code

            if current:
                chunks.append(current)

            await interaction.response.send_message(
                chunks[0],
                ephemeral=True
            )

            for chunk in chunks[1:]:
                await interaction.followup.send(
                    chunk,
                    ephemeral=True
                )

        print(
            "Registered /languages command"
        )

        # ---------------------------------------------
        # /mylang
        # ---------------------------------------------

        @self.tree.command(
            name="mylang",
            description="Show your current language setting"
        )
        async def mylang_slash(
            interaction: discord.Interaction
        ):

            user_lang = await db.get_user_lang(
                interaction.user.id
            )

            if not user_lang:
                await interaction.response.send_message(
                    "You have not set a language yet. "
                    "Use `/setlang`.",
                    ephemeral=True
                )
                return

            auto_enabled = await db.get_auto_translate(
                interaction.user.id
            )

            await interaction.response.send_message(
                f"Your language: `{user_lang}`\n"
                f"Automatic translations: "
                f"`{'ON' if auto_enabled else 'OFF'}`",
                ephemeral=True
            )

        print(
            "Registered /mylang command"
        )

        # ---------------------------------------------
        # /help-translate
        # ---------------------------------------------

        @self.tree.command(
            name="help-translate",
            description="Show help for the translation bot"
        )
        async def help_slash(
            interaction: discord.Interaction
        ):

            embed = discord.Embed(
                title="Translation Bot Help",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="Language",
                value=(
                    "`/setlang <language>` — "
                    "Choose your language\n"
                    "`/mylang` — View your settings\n"
                    "`/languages` — List language codes"
                ),
                inline=False
            )

            embed.add_field(
                name="Automatic Translation",
                value=(
                    "`/autotranslate true` — Turn it on\n"
                    "`/autotranslate false` — Turn it off\n\n"
                    "Messages from the configured translation "
                    "channel are automatically translated and "
                    "sent to your Discord DMs."
                ),
                inline=False
            )

            embed.add_field(
                name="Manual Translation",
                value=(
                    "You can also right-click a message and "
                    "use **Apps → Translate**."
                ),
                inline=False
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        print(
            "Registered /help-translate command"
        )

        # ---------------------------------------------
        # Language autocomplete
        # ---------------------------------------------

        @setlang.autocomplete('language')
        async def language_autocomplete(
            interaction: discord.Interaction,
            current: str
        ) -> list[app_commands.Choice[str]]:

            return [
                app_commands.Choice(
                    name=lang,
                    value=lang
                )
                for lang in sorted(
                    SUPPORTED_LANGUAGES
                )
                if current.lower() in lang.lower()
            ][:25]

        # ---------------------------------------------
        # Manual context menu
        # ---------------------------------------------

        add_translate_context_menu(
            self
        )

        print(
            "Registered context menu command (Translate)"
        )

        # Debug output.
        print(
            "App commands after setup_hook:",
            [
                cmd.name
                for cmd in self.tree.get_commands()
            ]
        )


# ---------------------------------------------------------
# Create bot
# ---------------------------------------------------------

bot = TranslationBot()


# Register admin commands
admin_commands.setup(
    bot
)


# ---------------------------------------------------------
# Ready event
# ---------------------------------------------------------

@bot.event
async def on_ready():

    await db.init_db()

    print(
        f'{bot.user} has connected to Discord!'
    )

    print(
        "App commands after on_ready:",
        [
            cmd.name
            for cmd in bot.tree.get_commands()
        ]
    )

    if TRANSLATION_CHANNEL_ID:
        print(
            "Automatic translation channel ID: "
            f"{TRANSLATION_CHANNEL_ID}"
        )
    else:
        print(
            "Automatic translation is currently enabled "
            "for all server channels."
        )


# ---------------------------------------------------------
# Message event
# ---------------------------------------------------------

@bot.event
async def on_message(
    message: discord.Message
):

    # Keep prefix commands such as !sync working.
    if not message.author.bot:
        await bot.process_commands(
            message
        )

    # Ignore bots and DMs after processing commands.
    if message.author.bot:
        return

    if message.guild is None:
        return

    # Run automatic translation.
    try:
        await automatic_translate_message(
            message
        )
    except Exception as e:
        print(
            f"Automatic translation handler error: {e}"
        )


# ---------------------------------------------------------
# Server-specific command synchronization
# ---------------------------------------------------------

@bot.command()
async def sync(ctx):

    if ctx.guild is None:
        await ctx.send(
            "This command must be used in a server."
        )
        return

    bot.tree.copy_global_to(
        guild=ctx.guild
    )

    await bot.tree.sync(
        guild=ctx.guild
    )

    await ctx.send(
        "Synced commands to this server."
    )


# ---------------------------------------------------------
# Bot entry point
# ---------------------------------------------------------

def run_bot():
    """Entry point for the bot."""

    health_thread = threading.Thread(
        target=run_health_server,
        daemon=True
    )

    health_thread.start()

    bot.run(
        os.getenv('DISCORD_TOKEN')
    )


# ---------------------------------------------------------
# Run directly
# ---------------------------------------------------------

if __name__ == '__main__':
    run_bot()
