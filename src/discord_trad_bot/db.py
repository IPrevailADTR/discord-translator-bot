import aiosqlite
import os

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