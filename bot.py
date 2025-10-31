import os
import discord
from discord.ext import commands

# Load config
import config

# Set env to avoid audio issues
os.environ["DISCORD_NO_AUDIO"] = "1"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Shared data ---
bot.scores = {}
bot.con_current = {}        # conundrum current puzzles
bot.con_locks = {}
bot.num_current = {}        # numbers current puzzles
bot.num_locks = {}

# Load scores file if exists
import json
try:
    with open(config.SCORES_FILE, "r", encoding="utf-8") as f:
        bot.scores = json.load(f)
except FileNotFoundError:
    bot.scores = {}

# --- Load extensions ---
bot.load_extension("utils")
bot.load_extension("conundrum_bot")
bot.load_extension("numbers_bot")

# --- Run bot ---
if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Environment variable DISCORD_BOT_TOKEN is missing.")
    bot.run(token)
