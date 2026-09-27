import re
from googletrans import Translator
import aiosqlite
import os

translator = Translator()

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'user_prefs.db')

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_lang (
                user_id TEXT PRIMARY KEY,
                lang TEXT NOT NULL
            )
        ''')
        await db.commit()

async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO user_lang (user_id, lang) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET lang=excluded.lang
        ''', (str(user_id), lang))
        await db.commit()

async def get_user_lang(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute('SELECT lang FROM user_lang WHERE user_id = ?', (str(user_id),)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

def preserve_user_mentions(text):
    """Replace user mentions with robust placeholders and return (text_with_placeholders, mention_map)."""
    mention_map = {}
    def mention_replacer(match):
        user_id = match.group(1)
        placeholder = f"[[[MENTION{len(mention_map)+1}]]]"
        mention_map[placeholder] = f"<@{user_id}>"
        return placeholder
    text_with_placeholders = re.sub(r'<@!?([0-9]+)>', mention_replacer, text)
    return text_with_placeholders, mention_map

def restore_mentions(text, mention_map):
    """Restore mentions in text using the mention_map (case-insensitive)."""
    for placeholder, mention in mention_map.items():
        text = re.sub(re.escape(placeholder), mention, text, flags=re.IGNORECASE)
    return text

def translate_message(content, dest_lang):
    """Translate content to dest_lang using googletrans."""
    return translator.translate(content, dest=dest_lang).text

def detect_language(content):
    """Detect the language of the content using googletrans."""
    try:
        detected = translator.detect(content)
        return detected.lang
    except Exception:
        return None 