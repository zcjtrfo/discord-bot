import os
import discord
from discord.ext import commands

# === Configuration ===
CONUNDRUM_CHANNEL_ID = 1424500871365918761
NUMBERS_CHANNEL_ID = 1431380518179573911

TEST_GENERAL_CHANNEL_ID = 1424857126878052413
TEST_CONUNDRUMS_CHANNEL_ID = 1433910612009816356
TEST_NUMBERS_CHANNEL_ID = 1430278725739479153

SCORES_FILE = "scores.json"

# === Shared State ===
current = {}           # Active conundrums per channel
locks = {}             # Async locks per conundrum channel
current_numbers = {}   # Active numbers puzzles per channel
numbers_locks = {}     # Async locks per numbers channel

try:
    import json
    with open(SCORES_FILE, "r", encoding="utf-8") as f:
        scores = json.load(f)
except FileNotFoundError:
    scores = {}

# === Discord Bot Setup ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# === On Ready Event ===
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (id: {bot.user.id})")

# === Load Extensions ===
async def load_extensions():
    await bot.load_extension("utils")
    await bot.load_extension("conundrum_bot")
    await bot.load_extension("numbers_bot")
    print("✅ All extensions loaded.")

# === Run Bot ===
if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Environment variable DISCORD_BOT_TOKEN is missing.")

    async def main():
        async with bot:
            await load_extensions()
            await bot.start(token)

    import asyncio
    asyncio.run(main())
