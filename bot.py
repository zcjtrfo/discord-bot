import os
import discord
from discord.ext import commands

# === Channel IDs ===
CONUNDRUM_CHANNEL_ID = 1424500871365918761
NUMBERS_CHANNEL_ID = 1431380518179573911

# ✅ Test channels
TEST_GENERAL_CHANNEL_ID = 1424857126878052413
TEST_CONUNDRUMS_CHANNEL_ID = 1433910612009816356
TEST_NUMBERS_CHANNEL_ID = 1430278725739479153

# === Scores file ===
SCORES_FILE = "scores.json"

# === Bot setup ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# === Main async entry point ===
async def main():
    # Load extensions (async)
    await bot.load_extension("utils")
    await bot.load_extension("conundrum_bot")
    await bot.load_extension("numbers_bot")

    # Get token from environment
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Environment variable DISCORD_BOT_TOKEN is missing.")

    # Start the bot
    await bot.start(token)

# === Bot events ===
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (id: {bot.user.id})")

# === Run bot ===
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
