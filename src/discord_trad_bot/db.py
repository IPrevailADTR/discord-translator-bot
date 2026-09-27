import aiosqlite
import os

DB_PATH = os.path.join(
    os.path.dirname(__file__),
    '..',
    'user_prefs.db'
)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user_lang (
                user_id TEXT PRIMARY KEY,
                lang TEXT NOT NULL,
                auto_translate INTEGER NOT NULL DEFAULT 1
            )
        ''')

        # Add the column when upgrading an existing database
        # that was created by the previous version.
        try:
            await db.execute('''
                ALTER TABLE user_lang
                ADD COLUMN auto_translate INTEGER NOT NULL DEFAULT 1
            ''')
        except aiosqlite.OperationalError as e:
            if 'duplicate column name' not in str(e).lower():
                raise

        await db.commit()


async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            INSERT INTO user_lang (user_id, lang)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET lang = excluded.lang
        ''', (str(user_id), lang))

        await db.commit()


async def get_user_lang(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT lang FROM user_lang WHERE user_id = ?',
            (str(user_id),)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_auto_translate(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            '''
            SELECT auto_translate
            FROM user_lang
            WHERE user_id = ?
            ''',
            (str(user_id),)
        ) as cursor:
            row = await cursor.fetchone()

            if not row:
                return False

            return bool(row[0])


async def set_auto_translate(user_id: int, enabled: bool):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            '''
            UPDATE user_lang
            SET auto_translate = ?
            WHERE user_id = ?
            ''',
            (1 if enabled else 0, str(user_id))
        )

        await db.commit()


async def get_all_user_prefs():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            '''
            SELECT user_id, lang, auto_translate
            FROM user_lang
            '''
        ) as cursor:
            rows = await cursor.fetchall()

            return rows
