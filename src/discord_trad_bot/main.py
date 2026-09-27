import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from googletrans import LANGUAGES

from discord_trad_bot import db
from discord_trad_bot.constants import SUPPORTED_LANGUAGES
from discord_trad_bot.utils import (
    detect_language,
    preserve_user_mentions,
    restore_mentions,
    translate_message,
)


load_dotenv()


# =========================================================
# SERVER CONFIGURATION
# =========================================================

GUILD_ID = 1551762166246408222

# Your #chat channel from the Discord URL you gave me.
CHAT_CHANNEL_ID = 1551762166892200007

TRANSLATION_CATEGORY_NAME = "Translations"

GUILD_OBJECT = discord.Object(id=GUILD_ID)


# =========================================================
# DISCORD INTENTS
# =========================================================

intents = discord.Intents.default()

intents.message_content = True
intents.members = True


# =========================================================
# LANGUAGE HELPERS
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
    "brazilian portuguese": "pt",
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
    return LANGUAGE_NAMES.get(code, code).title()


# =========================================================
# RENDER HEALTH CHECK
# =========================================================

class HealthCheckHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        if self.path == "/health":

            self.send_response(200)

            self.send_header(
                "Content-Type",
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

            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        return


def run_health_server():

    port = int(
        os.getenv(
            "PORT",
            "8080"
        )
    )

    server = HTTPServer(
        (
            "0.0.0.0",
            port
        ),
        HealthCheckHandler
    )

    print(
        f"Health server listening on port {port}"
    )

    server.serve_forever()


# =========================================================
# TRANSLATION CATEGORY
# =========================================================

async def get_or_create_translation_category(
    guild: discord.Guild
):

    category = discord.utils.find(
        lambda item:
            item.name == TRANSLATION_CATEGORY_NAME,
        guild.categories
    )

    if category:
        return category

    category = await guild.create_category(
        TRANSLATION_CATEGORY_NAME,
        reason="Create translation category"
    )

    print(
        f"Created category #{TRANSLATION_CATEGORY_NAME}"
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

    channel_name = f"translate-{language}"

    existing = discord.utils.find(
        lambda channel:
            (
                channel.name == channel_name
                and channel.category_id == category.id
            ),
        guild.text_channels
    )

    if existing:
        return existing

    overwrites = {}

    overwrites[guild.default_role] = (
        discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            read_message_history=True
        )
    )

    if guild.me:

        overwrites[guild.me] = (
            discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                embed_links=True,
                read_message_history=True
            )
        )

    channel = await guild.create_text_channel(
        channel_name,
        category=category,
        overwrites=overwrites,
        reason=(
            "Create shared "
            f"{language_display_name(language)} "
            "translation channel"
        )
    )

    await channel.send(
        embed=discord.Embed(
            title=(
                f"{language_display_name(language)} "
                "Translations"
            ),
            description=(
                "Messages from #chat will be "
                "automatically translated into "
                f"{language_display_name(language)} here."
            ),
            color=discord.Color.blue()
        )
    )

    print(
        f"Created #{channel_name}"
    )

    return channel


# =========================================================
# AUTOMATIC TRANSLATION
# =========================================================

async def automatic_translate_message(
    message: discord.Message
):

    if message.guild is None:
        return

    if message.guild.id != GUILD_ID:
        return

    if message.channel.id != CHAT_CHANNEL_ID:
        return

    if message.author.bot:
        return

    content = message.content.strip()

    if not content:
        return

    user_languages = (
        await db.get_all_user_langs()
    )

    active_languages = sorted(
        set(
            user_languages.values()
        )
    )

    if not active_languages:
        return

    detected_lang = await asyncio.to_thread(
        detect_language,
        content
    )

    if not detected_lang:

        print(
            "Could not detect message language"
        )

        return

    content_preserved, mention_map = (
        preserve_user_mentions(
            content
        )
    )

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

            translated_text = (
                restore_mentions(
                    translated_text,
                    mention_map
                )
            )

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
                name=message.author.display_name,
                icon_url=(
                    message.author
                    .display_avatar
                    .url
                )
            )

            embed.set_footer(
                text=(
                    "Original language: "
                    f"{language_display_name(detected_lang)}"
                )
            )

            await channel.send(
                embed=embed,
                allowed_mentions=(
                    discord.AllowedMentions.none()
                )
            )

        except discord.Forbidden as exc:

            print(
                f"Discord permission error "
                f"for {target_language}: {exc}"
            )

        except Exception as exc:

            print(
                f"Translation failed for "
                f"{target_language}: {exc}"
            )


# =========================================================
# BOT
# =========================================================

class TranslationBot(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):

        await db.init_db()

        # -------------------------------------------------
        # REMOVE OLD GLOBAL COMMANDS
        # -------------------------------------------------

        self.tree.clear_commands(
            guild=None
        )

        await self.tree.sync()

        # -------------------------------------------------
        # REMOVE OLD SERVER COMMANDS
        # -------------------------------------------------

        self.tree.clear_commands(
            guild=GUILD_OBJECT
        )

        await self.tree.sync(
            guild=GUILD_OBJECT
        )

        # -------------------------------------------------
        # /mylang
        # -------------------------------------------------

        @self.tree.command(
            name="mylang",
            description=(
                "Choose your personal "
                "translation language"
            ),
            guild=GUILD_OBJECT
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

            await interaction.response.defer(
                ephemeral=True
            )

            value = (
                language
                .strip()
                .lower()
            )

            # Turn translation off.

            if value in {
                "off",
                "disable",
                "none"
            }:

                await db.clear_user_lang(
                    interaction.user.id
                )

                await interaction.followup.send(
                    "Your translation language "
                    "has been turned off.",
                    ephemeral=True
                )

                return

            language_code = (
                resolve_language(
                    value
                )
            )

            if not language_code:

                await interaction.followup.send(
                    "I don't recognize that language. "
                    "Try English, Spanish, Dutch, French, "
                    "German, or a supported language code.",
                    ephemeral=True
                )

                return

            try:

                await db.set_user_lang(
                    interaction.user.id,
                    language_code
                )

                channel = (
                    await get_or_create_language_channel(
                        interaction.guild,
                        language_code
                    )
                )

                await interaction.followup.send(
                    (
                        "Your translation language is now "
                        f"**{language_display_name(language_code)}**.\n\n"
                        f"Your server translations will appear in "
                        f"{channel.mention}."
                    ),
                    ephemeral=True
                )

            except discord.Forbidden:

                await interaction.followup.send(
                    (
                        "I could not create the language channel. "
                        "TB Server Translator needs "
                        "**Manage Channels** and permission "
                        "to send messages."
                    ),
                    ephemeral=True
                )

            except Exception as exc:

                print(
                    f"/mylang error: {exc}"
                )

                await interaction.followup.send(
                    (
                        "I could not configure that language. "
                        "Check the Render logs for the exact error."
                    ),
                    ephemeral=True
                )

        # -------------------------------------------------
        # /mylang AUTOCOMPLETE
        # -------------------------------------------------

        @mylang.autocomplete(
            "language"
        )
        async def mylang_autocomplete(
            interaction: discord.Interaction,
            current: str
        ):

            current = (
                current
                .lower()
                .strip()
            )

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
                                f"{name.title()} "
                                f"({code})"
                            )[:100],
                            value=code
                        )
                    )

                if len(choices) == 25:
                    break

            return choices

        # -------------------------------------------------
        # /ping
        # -------------------------------------------------

        @self.tree.command(
            name="ping",
            description="Test if the bot is working",
            guild=GUILD_OBJECT
        )
        async def ping(
            interaction: discord.Interaction
        ):

            await interaction.response.send_message(
                "Pong!",
                ephemeral=True
            )

        # -------------------------------------------------
        # /languages
        # -------------------------------------------------

        @self.tree.command(
            name="languages",
            description=(
                "List supported translation languages"
            ),
            guild=GUILD_OBJECT
        )
        async def languages(
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
                text[:1900]
                if text
                else "No languages found.",
                ephemeral=True
            )

        # -------------------------------------------------
        # /help-translate
        # -------------------------------------------------

        @self.tree.command(
            name="help-translate",
            description=(
                "Show translation bot help"
            ),
            guild=GUILD_OBJECT
        )
        async def help_translate(
            interaction: discord.Interaction
        ):

            embed = discord.Embed(
                title="TB Server Translator",
                description=(
                    "Use `/mylang <language>` "
                    "to choose the language you want "
                    "the server chat translated into."
                ),
                color=discord.Color.blue()
            )

            embed.add_field(
                name="Examples",
                value=(
                    "`/mylang english`\n"
                    "`/mylang spanish`\n"
                    "`/mylang dutch`\n"
                    "`/mylang french`"
                ),
                inline=False
            )

            embed.add_field(
                name="Chat channel",
                value="#chat",
                inline=False
            )

            embed.add_field(
                name="Translation channels",
                value=(
                    "The bot creates "
                    "`#translate-xx` when a "
                    "language is selected."
                ),
                inline=False
            )

            embed.add_field(
                name="Turn it off",
                value="`/mylang off`",
                inline=False
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        # -------------------------------------------------
        # REGISTER COMMANDS
        # -------------------------------------------------

        await self.tree.sync(
            guild=GUILD_OBJECT
        )

        print(
            "Guild slash commands synced."
        )

        print(
            "Registered commands:",
            [
                command.name
                for command in self.tree.get_commands(
                    guild=GUILD_OBJECT
                )
            ]
        )


# =========================================================
# CREATE BOT
# =========================================================

bot = TranslationBot()


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    print(
        f"{bot.user} has connected to Discord!"
    )

    print(
        "Watching #chat channel ID:",
        CHAT_CHANNEL_ID
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

    await bot.process_commands(
        message
    )

    try:

        await automatic_translate_message(
            message
        )

    except Exception as exc:

        print(
            f"Automatic translation error: {exc}"
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

    token = os.getenv(
        "DISCORD_TOKEN"
    )

    if not token:

        raise RuntimeError(
            "DISCORD_TOKEN is not configured."
        )

    bot.run(
        token
    )


if __name__ == "__main__":
    run_bot()
