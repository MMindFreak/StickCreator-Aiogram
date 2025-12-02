import aiosqlite
from config import DB_NAME

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS packs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                title TEXT,
                pack_type TEXT DEFAULT 'regular',
                UNIQUE(name)
            )
            """
        )
        
        try:
            await db.execute("SELECT pack_type FROM packs LIMIT 1")
        except Exception:
            print("Migrating database: adding pack_type column...")
            await db.execute("ALTER TABLE packs ADD COLUMN pack_type TEXT DEFAULT 'regular'")
            await db.commit()
            
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                current_pack_id INTEGER
            )
            """
        )
        await db.commit()

async def get_user_packs(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM packs WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchall()

async def get_user_current_pack_id(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT current_pack_id FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
            setting = await cursor.fetchone()
            return setting[0] if setting else None

async def set_user_current_pack_id(user_id: int, pack_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR REPLACE INTO user_settings (user_id, current_pack_id) VALUES (?, ?)",
            (user_id, pack_id),
        )
        await db.commit()

async def create_pack(user_id: int, name: str, title: str, pack_type: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO packs (user_id, name, title, pack_type) VALUES (?, ?, ?, ?)",
            (user_id, name, title, pack_type)
        )
        await db.commit()
        
        async with db.execute("SELECT id FROM packs WHERE name = ?", (name,)) as cursor:
            new_pack = await cursor.fetchone()
            return new_pack[0]

async def delete_pack_from_db(pack_id: int, user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM packs WHERE id = ?", (pack_id,))
        async with db.execute("SELECT current_pack_id FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
             setting = await cursor.fetchone()
             if setting and setting[0] == pack_id:
                 await db.execute("DELETE FROM user_settings WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_pack_by_id(pack_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT name, title, pack_type FROM packs WHERE id = ?", (pack_id,)) as cursor:
            return await cursor.fetchone()

async def get_user_stats(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM packs WHERE user_id = ?", (user_id,)) as cursor:
            count = await cursor.fetchone()
            return count[0] if count else 0
