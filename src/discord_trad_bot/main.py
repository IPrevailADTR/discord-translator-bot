import os
import asyncio
import threading
import json

import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
from googletrans import LANGUAGES

from discord_trad_bot import db

from discord_trad_bot.utils import (
    preserve_user_mentions,
    restore_mentions,
    translate_message,
    detect_language,
)

from discord_trad_bot.constants import SUPPORTED_LANGUAGES
from discord_trad_bot.commands import admin_commands

from http.server import HTTPServer, BaseHTTPRequestHandler


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv()

try:
    TRANSLATION_CHANNEL_ID = int(
        os.getenv(
            "TRANSLATION_CHANNEL_ID",
            "0"
        )
    )
except ValueError:
    TRANSLATION_CHANNEL_ID = 0


TRANSLATION_CATEGORY_NAME = "Translations"


# =========================================================
# LANGUAGE NAMES
# =========================================================

LANGUAGE_NAMES = {
    code: LANGUAGES[code]
    for code in SUPPORTED_LANGUAGES
    if code in LANGUAGES
}


LANGUAGE_ALIASES = {
    "english": "en",
    "spanish": "es",
    "dutch": "nl",
    "french": "fr",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "japanese": "ja",
    "korean": "ko",
    "russian": "ru",
    "arabic": "ar",
    "polish": "pl",
    "turkish": "tr",
    "vietnamese": "vi",
    "thai": "th",
    "greek": "el",
    "hebrew": "he",
    "hindi": "hi",
    "ukrainian": "uk",
    "swedish": "sv",
    "norwegian": "no",
    "danish": "da",
    "finnish": "fi",
    "czech": "cs",
    "hungarian": "hu",
    "romanian": "ro",
}


def resolve_language(value: str):
    value = value.strip().lower()

    if value in SUPPORTED_LANGUAGES:
        return value

    if value in LANGUAGE_ALIASES:
        return LANGUAGE_ALIASES[value]

    for code, name in LANGUAGE_NAMES.items():
        if value == name.lower():
            return code

    return None


def language_display_name(code: str):
    return LANGUAGE_NAMES.get(
        code,
        code
    ).title()


# =========================================================
# DISCORD INTENTS
# =========================================================

intents = discord.Intents.default()

intents.message_content = True
intents.members = True


# =========================================================
# RENDER HEALTH CHECK
# =========================================================

class HealthCheckHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        if self.path == "/health":

            self.send_response(200)

            self.send_header(
                "Content-type",
                "application/json"
            )

            self.end_headers()

            response = {
                "status": "healthy",
                "bot_status":
                    "online"
                    if bot.is_ready()
                    else "offline"
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
            "0.0.0.0",
            int(
                os.getenv(
                    "PORT",
                    "8080"
                )
            )
        ),
        HealthCheckHandler
    )

    print(
        "Health check server running on port "
        f"{os.getenv('PORT', '8080')}"
    )

    server.serve_forever()


# =========================================================
# TRANSLATION CATEGORY
# =========================================================

async def get_or_create_translation_category(
    guild: discord.Guild
):

    category = discord.utils.find(
        lambda c:
            c.name == TRANSLATION_CATEGORY_NAME,
        guild.categories
    )

    if category:
        return category

    category = await guild.create_category(
        TRANSLATION_CATEGORY_NAME,
        reason="Create translation category"
    )

    print(
        f"Created category: {category.name}"
    )

    return category


# =========================================================
# LANGUAGE CHANNEL
# =========================================================

async def get_or_create_language_channel(
    guild: discord.Guild,
    language: str
):

    category = (
        await get_or_create_translation_category(
            guild
        )
    )

    channel_name = (
        f"translate-{language}"
    )

    existing = discord.utils.find(
        lambda channel:
            channel.name == channel_name
        and channel.category_id == category.id,
        guild.text_channels
    )

    if existing:
        return existing

    channel = await guild.create_text_channel(
        channel_name,
        category=category,
        reason=(
            "Create translation channel for "
            f"{language_display_name(language)}"
        )
    )

    await channel.send(
        embed=discord.Embed(
            title=(
                f"{language_display_name(language)} "
                f"Translations"
            ),
            description=(
                "Messages from the main chat are "
                "automatically translated into "
                f"{language_display_name(language)} "
                "in this channel."
            ),
            color=discord.Color.blue()
        )
    )

    print(
        f"Created translation channel: "
        f"#{channel_name}"
    )

    return channel


# =========================================================
# MANUAL TRANSLATE CONTEXT MENU
# =========================================================

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
                "Use `/mylang` to choose your "
                "translation language first.",
                ephemeral=True
            )

            return

        try:

            detected_lang = await asyncio.to_thread(
                detect_language,
                message.content
            )

            if not detected_lang:

                await interaction.response.send_message(
                    "Could not detect the message language.",
                    ephemeral=True
                )

                return

            content_preserved, mention_map = (
                preserve_user_mentions(
                    message.content
                )
            )

            if detected_lang == user_lang:

                translated_text = content_preserved

            else:

                translated_text = (
                    await asyncio.to_thread(
                        translate_message,
                        content_preserved,
                        user_lang
                    )
                )

            translated_text = restore_mentions(
                translated_text,
                mention_map
            )

            embed = discord.Embed(
                description=translated_text,
                color=discord.Color.blue()
            )

            embed.set_author(
                name=(
                    f"Translation for "
                    f"{interaction.user.display_name}"
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
                "There was an error translating "
                "this message.",
                ephemeral=True
            )

    bot.tree.add_command(
        translate_message_context
    )


# =========================================================
# AUTOMATIC TRANSLATION
# =========================================================

async def automatic_translate_message(
    message: discord.Message
):

    # Only messages from a Discord server.
    if message.guild is None:
        return

    # Never translate bot messages.
    if message.author.bot:
        return

    # Only monitor our designated #chat channel.
    if (
        TRANSLATION_CHANNEL_ID
        and message.channel.id
        != TRANSLATION_CHANNEL_ID
    ):
        return

    content = message.content.strip()

    if not content:
        return

    # Don't translate bot commands.
    if content.startswith("!"):
        return

    # Get all selected languages.
    user_languages = (
        await db.get_all_user_langs()
    )

    if not user_languages:
        return

    active_languages = set(
        user_languages.values()
    )

    if not active_languages:
        return

    # Detect the original language once.
    try:

        detected_lang = await asyncio.to_thread(
            detect_language,
            content
        )

    except Exception as e:

        print(
            f"Language detection error: {e}"
        )

        return

    if not detected_lang:
        return

    content_preserved, mention_map = (
        preserve_user_mentions(
            content
        )
    )

    # Translate once for each active language.
    for target_language in active_languages:

        try:

            if target_language == detected_lang:

                translated_text = (
                    content_preserved
                )

            else:

                translated_text = (
                    await asyncio.to_thread(
                        translate_message,
                        content_preserved,
                        target_language
                    )
                )

            translated_text = restore_mentions(
                translated_text,
                mention_map
            )

        except Exception as e:

            print(
                f"Translation failed for "
                f"{target_language}: {e}"
            )

            continue

        try:

            channel = (
                await get_or_create_language_channel(
                    message.guild,
                    target_language
                )
            )

            embed = discord.Embed(
                description=translated_text,
                color=discord.Color.blue(),
                url=message.jump_url
            )

            embed.set_author(
                name=(
                    f"{message.author.display_name}"
                ),
                icon_url=(
                    message.author.display_avatar.url
                )
            )

            embed.set_footer(
                text=(
                    f"Original language: "
                    f"{language_display_name(detected_lang)}"
                )
            )

            await channel.send(
                embed=embed,
                allowed_mentions=(
                    discord.AllowedMentions.none()
                )
            )

        except discord.Forbidden:

            print(
                "Discord denied permission to "
                f"create/write #translate-{target_language}. "
                "Make sure the bot has Manage Channels."
            )

        except Exception as e:

            print(
                f"Could not send "
                f"{target_language} translation: {e}"
            )


# =========================================================
# BOT
# =========================================================

class TranslationBot(
    commands.Bot
):

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):

        # -------------------------------------------------
        # /mylang
        # -------------------------------------------------

        @self.tree.command(
            name="mylang",
            description=(
                "Choose your personal translation language"
            )
        )
        @app_commands.describe(
            language=(
                "Example: English, Spanish, "
                "Dutch, French, or a language code"
            )
        )
        async def mylang(
            interaction: discord.Interaction,
            language: str
        ):

            if interaction.guild is None:

                await interaction.response.send_message(
                    "Use `/mylang` inside the server.",
                    ephemeral=True
                )

                return

            value = language.strip().lower()

            # Turn personal translation preference off.
            if value in {
                "off",
                "disable",
                "none"
            }:

                await db.clear_user_lang(
                    interaction.user.id
                )

                await interaction.response.send_message(
                    "Your translation language has "
                    "been turned off.",
                    ephemeral=True
                )

                return

            language_code = resolve_language(
                value
            )

            if not language_code:

                await interaction.response.send_message(
                    "I don't recognize that language.\n\n"
                    "Try a language such as "
                    "`english`, `spanish`, `dutch`, "
                    "`french`, `german`, `italian`, "
                    "`japanese`, or a supported code.",
                    ephemeral=True
                )

                return

            try:

                # Save personal preference.
                await db.set_user_lang(
                    interaction.user.id,
                    language_code
                )

                # Create the shared language channel.
                channel = (
                    await get_or_create_language_channel(
                        interaction.guild,
                        language_code
                    )
                )

                await interaction.response.send_message(
                    f"Your personal language is now "
                    f"**{language_display_name(language_code)}**.\n\n"
                    f"Your language channel is "
                    f"{channel.mention}.",
                    ephemeral=True
                )

            except discord.Forbidden:

                await interaction.response.send_message(
                    "I couldn't create the language channel. "
                    "Give TB Server Translator the "
                    "**Manage Channels** permission.",
                    ephemeral=True
                )

            except Exception as e:

                print(
                    f"/mylang error: {e}"
                )

                await interaction.response.send_message(
                    "I couldn't configure that language.",
                    ephemeral=True
                )

        print(
            "Registered /mylang command"
        )

        # -------------------------------------------------
        # /ping
        # -------------------------------------------------

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

        # -------------------------------------------------
        # /languages
        # -------------------------------------------------

        @self.tree.command(
            name="languages",
            description=(
                "List supported Google Translate languages"
            )
        )
        async def languages_slash(
            interaction: discord.Interaction
        ):

            codes = sorted(
                SUPPORTED_LANGUAGES
            )

            text = " ".join(
                f"`{code}`"
                for code in codes
            )

            await interaction.response.send_message(
                text[:1900],
                ephemeral=True
            )

        print(
            "Registered /languages command"
        )

        # -------------------------------------------------
        # /help-translate
        # -------------------------------------------------

        @self.tree.command(
            name="help-translate",
            description="Show translation bot help"
        )
        async def help_translate(
            interaction: discord.Interaction
        ):

            embed = discord.Embed(
                title="TB Server Translator",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="/mylang",
                value=(
                    "Choose the language you want "
                    "the server conversation translated into.\n\n"
                    "Examples:\n"
                    "`/mylang english`\n"
                    "`/mylang spanish`\n"
                    "`/mylang dutch`\n"
                    "`/mylang french`"
                ),
                inline=False
            )

            embed.add_field(
                name="How it works",
                value=(
                    "Messages in #chat are translated into "
                    "each language currently selected by "
                    "members."
                ),
                inline=False
            )

            embed.add_field(
                name="Channels",
                value=(
                    "Each language has one shared channel:\n"
                    "`#translate-english`\n"
                    "`#translate-spanish`\n"
                    "`#translate-dutch`\n"
                    "`#translate-french`"
                ),
                inline=False
            )

            embed.add_field(
                name="Turn it off",
                value=(
                    "`/mylang off`"
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

        # -------------------------------------------------
        # AUTOCOMPLETE
        # -------------------------------------------------

        @mylang.autocomplete("language")
        async def mylang_autocomplete(
            interaction: discord.Interaction,
            current: str
        ):

            current = current.lower().strip()

            choices = []

            for code, name in sorted(
                LANGUAGE_NAMES.items(),
                key=lambda item: item[1]
            ):

                if (
                    not current
                    or current in code.lower()
                    or current in name.lower()
                ):

                    choices.append(
                        app_commands.Choice(
                            name=(
                                f"{name.title()} ({code})"
                            )[:100],
                            value=code
                        )
                    )

                if len(choices) >= 25:
                    break

            return choices

        # -------------------------------------------------
        # CONTEXT MENU
        # -------------------------------------------------

        add_translate_context_menu(
            self
        )

        print(
            "Registered Translate context menu"
        )

        print(
            "Registered app commands:",
            [
                cmd.name
                for cmd in self.tree.get_commands()
            ]
        )


# =========================================================
# CREATE BOT
# =========================================================

bot = TranslationBot()


# =========================================================
# ADMIN COMMANDS
# =========================================================

admin_commands.setup(
    bot
)


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    await db.init_db()

    print(
        f"{bot.user} has connected to Discord!"
    )

    print(
        "Translation source channel:",
        TRANSLATION_CHANNEL_ID
    )


# =========================================================
# MESSAGE HANDLER
# =========================================================

@bot.event
async def on_message(
    message: discord.Message
):

    if message.author.bot:
        return

    # Keep !sync working.
    await bot.process_commands(
        message
    )

    # Automatic translation.
    try:

        await automatic_translate_message(
            message
        )

    except Exception as e:

        print(
            f"Automatic translation error: {e}"
        )


# =========================================================
# SERVER COMMAND SYNC
# =========================================================

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


# =========================================================
# START BOT
# =========================================================

def run_bot():

    health_thread = threading.Thread(
        target=run_health_server,
        daemon=True
    )

    health_thread.start()

    bot.run(
        os.getenv(
            "DISCORD_TOKEN"
        )
    )


if __name__ == "__main__":
    run_bot()
