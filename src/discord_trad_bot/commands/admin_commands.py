from discord_trad_bot import db
import aiosqlite
from discord.ext.commands import has_permissions, CheckFailure


def setup(bot):
    @bot.command(name='debugdb')
    @has_permissions(administrator=True)
    async def debugdb(ctx):
        """Debug command to check database schema and content"""
        try:
            # Get some user preferences (limit to 5 for readability)
            async with aiosqlite.connect(db.DB_PATH) as conn:
                async with conn.execute('SELECT user_id, lang FROM user_lang LIMIT 5') as cursor:
                    users = await cursor.fetchall()
            users_info = "\n".join([f"User ID: {u[0]}, Lang: {u[1]}" for u in users])
            # Get table info
            async with aiosqlite.connect(db.DB_PATH) as conn:
                async with conn.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
                    tables = await cursor.fetchall()
            tables_info = "\n".join([f"Table: {t[0]}" for t in tables])
            # Format the response
            response = f"""**Database Debug Info:**\n\n**Tables:**\n{tables_info}\n\n**Sample User Preferences (up to 5):**\n{users_info}"""
            await ctx.send(response)
        except Exception as e:
            await ctx.send(f"Error checking database: {str(e)}")

    @debugdb.error
    async def debugdb_error(ctx, error):
        if isinstance(error, CheckFailure):
            await ctx.send('You need to be an administrator to use this command.') 