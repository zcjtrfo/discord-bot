import json
import random
import re
import requests
import urllib.parse
import discord
from discord.ext import commands

# Import shared bot instance and constants from bot.py
from bot import (
    bot,
    CONUNDRUM_CHANNEL_ID,
    NUMBERS_CHANNEL_ID,
    TEST_GENERAL_CHANNEL_ID,
    TEST_CONUNDRUMS_CHANNEL_ID,
    TEST_NUMBERS_CHANNEL_ID,
    SCORES_FILE,
)

# === Global scores storage ===
try:
    with open(SCORES_FILE, "r", encoding="utf-8") as f:
        scores = json.load(f)
except FileNotFoundError:
    scores = {}


# === Helper: Save scores to file ===
def save_scores():
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2)


# === WORD VALIDATION COMMANDS ===
@bot.command(name="check")
async def check_word(ctx, *, term: str):
    """Check whether a word is valid using the FocalTools API."""
    try:
        user_identifier = ctx.author.name
        url = f"https://focaltools.azurewebsites.net/api/checkword/{term}?ip={user_identifier}"

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.text.strip().lower()

        if "true" in data:
            await ctx.send(f"✅ **{term.upper()}** is **VALID**")
        elif "false" in data:
            await ctx.send(f"❌ **{term.upper()}** is **INVALID**")
        else:
            await ctx.send(f"⚠️ Unexpected response for **{term}**: `{data}`")
    except requests.exceptions.RequestException as e:
        await ctx.send(f"❌ Error calling the API: `{e}`")


@bot.command(name="maxes")
async def maxes(ctx, *, selection: str):
    """Find the longest possible words from the given selection using FocalTools."""
    selection = selection.strip().upper()

    if not re.fullmatch(r"[A-Z\*]+", selection):
        await ctx.send("⚠️ Selection must only contain letters A–Z and up to two '*' wildcards.")
        return
    if selection.count("*") > 2:
        await ctx.send("⚠️ You can use a maximum of two '*' wildcards.")
        return
    if len(selection) > 12:
        await ctx.send("⚠️ Selection must contain 12 characters or fewer (including wildcards).")
        return

    user_identifier = urllib.parse.quote(ctx.author.name)
    url = f"https://focaltools.azurewebsites.net/api/getwords/{selection}?ip={user_identifier}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        words = json.loads(response.text)
        if not words:
            await ctx.send(f"⚠️ No words found for *{selection}*.")
            return

        max_len = max(len(w) for w in words)
        max_words = [w for w in words if len(w) == max_len]
        await ctx.send(f":arrow_up: Maxes from *{selection}*: **{', '.join(sorted(max_words))}**")

    except Exception as e:
        await ctx.send(f"⚠️ Could not process request — `{e}`")


# === SELECTION FORMATTER ===
@bot.command(name="selection")
async def selection(ctx, *, args: str):
    """Convert letters or numbers into emoji selection format."""
    args = args.strip()

    # Letters
    if re.fullmatch(r"[A-Za-z]+", args.replace(" ", "")):
        letters = args.replace(" ", "").upper()
        emoji_output = " ".join(f":regional_indicator_{ch.lower()}:" for ch in letters)
        await ctx.send(f">{emoji_output}<")
        return

    # Numbers
    try:
        numbers = [int(x) for x in args.split()]
    except ValueError:
        await ctx.send("⚠️ Please provide either letters (A–Z) or numbers separated by spaces.")
        return

    if len(numbers) < 3:
        await ctx.send("⚠️ Please provide at least 3 numbers (e.g. `!selection 25 50 3 6 7 10 952`).")
        return

    *selection_nums, target = numbers
    valid_numbers = {1,2,3,4,5,6,7,8,9,10,25,50,75,100}

    if not all(n in valid_numbers for n in selection_nums):
        await ctx.send("⚠️ Only numbers from [1–10, 25, 50, 75, 100] are allowed.")
        return

    emoji_map = {
        1: ":one:", 2: ":two:", 3: ":three:", 4: ":four:", 5: ":five:",
        6: ":six:", 7: ":seven:", 8: ":eight:", 9: ":nine:", 10: ":number_10:",
        25: "<:twentyfive:1430640762655342602>",
        50: "<:fifty:1430640824244371617>",
        75: "<:seventyfive:1430640855173300325>",
        100: "<:onehundred:1430640895895670901>",
    }
    digit_map = {
        "0": ":zero:", "1": ":one:", "2": ":two:", "3": ":three:",
        "4": ":four:", "5": ":five:", "6": ":six:", "7": ":seven:",
        "8": ":eight:", "9": ":nine:",
    }

    def to_emoji(num): return emoji_map.get(num, str(num))
    def target_to_emojis(t): return " ".join(digit_map[d] for d in str(t))

    selection_emojis = " ".join(to_emoji(n) for n in selection_nums)
    target_emojis = target_to_emojis(target)

    await ctx.send(f":dart:--->{target_emojis}<---:dart:\n|-{selection_emojis}-|" )


# === TEST CONTROL COMMANDS ===
@bot.command(name="start_tests")
@commands.has_permissions(manage_messages=True)
async def start_tests(ctx):
    """Start both test conundrum and numbers quizzes (usable only in #test_general)."""
    if ctx.channel.id != TEST_GENERAL_CHANNEL_ID:
        await ctx.send("⚠️ This command can't be used in this channel.")
        return

    from conundrum_bot import new_puzzle
    from numbers_bot import new_numbers_round

    con_channel = bot.get_channel(TEST_CONUNDRUMS_CHANNEL_ID)
    num_channel = bot.get_channel(TEST_NUMBERS_CHANNEL_ID)

    if con_channel:
        await new_puzzle(con_channel)
        await con_channel.send("🧩 Test Conundrum quiz started! Reply with your answers below.")
    if num_channel:
        await new_numbers_round(num_channel)

    await ctx.send("✅ Test quizzes started in #test_conundrums and #test_numbers.")


@bot.command(name="stop_tests")
@commands.has_permissions(manage_messages=True)
async def stop_tests(ctx):
    """Stop both test conundrum and numbers quizzes (usable only in #test_general)."""
    if ctx.channel.id != TEST_GENERAL_CHANNEL_ID:
        await ctx.send("⚠️ This command can't be used in this channel.")
        return

    from conundrum_bot import current as con_current
    from numbers_bot import current_numbers

    if TEST_CONUNDRUMS_CHANNEL_ID in con_current:
        del con_current[TEST_CONUNDRUMS_CHANNEL_ID]
        ch = bot.get_channel(TEST_CONUNDRUMS_CHANNEL_ID)
        if ch:
            await ch.send("🛑 Test Conundrum quiz stopped.")

    if TEST_NUMBERS_CHANNEL_ID in current_numbers:
        del current_numbers[TEST_NUMBERS_CHANNEL_ID]
        ch = bot.get_channel(TEST_NUMBERS_CHANNEL_ID)
        if ch:
            await ch.send("🛑 Test Numbers quiz stopped.")

    await ctx.send("✅ Test quizzes stopped in #test_conundrums and #test_numbers.")


# === LEADERBOARD & SCORES ===
@bot.command(name="points")
async def leaderboard(ctx):
    """Show top solvers for the current channel (Conundrum or Numbers)."""
    if not scores:
        await ctx.send("No scores yet!")
        return

    channel_id = ctx.channel.id
    if channel_id in [CONUNDRUM_CHANNEL_ID, TEST_CONUNDRUMS_CHANNEL_ID]:
        key, title = "con_score", "🏆 Countdown Conundrum Leaderboard"
    elif channel_id in [NUMBERS_CHANNEL_ID, TEST_NUMBERS_CHANNEL_ID]:
        key, title = "num_score", "🔢 Countdown Numbers Leaderboard"
    else:
        await ctx.send("⚠️ This command can only be used in the Conundrum or Numbers channels.")
        return

    valid = {uid: info for uid, info in scores.items() if info.get(key, 0) > 0}
    if not valid:
        await ctx.send("No scores yet for this category!")
        return

    top = sorted(valid.items(), key=lambda x: x[1][key], reverse=True)[:15]
    msg = f"**{title}**\n"
    for i, (uid, info) in enumerate(top, 1):
        msg += f"{i}. {info.get('name', 'Unknown')}: {info.get(key, 0)}\n"

    await ctx.send(msg)


@bot.command(name="dump_scores")
@commands.has_permissions(manage_messages=True)
async def dump_scores_file(ctx):
    """Send the current scores.json file (only usable from #test_general)."""
    if ctx.channel.id != TEST_GENERAL_CHANNEL_ID:
        await ctx.send("⚠️ This command can't be used in this channel.")
        return

    try:
        await ctx.send(file=discord.File(SCORES_FILE))
        await ctx.send("✅ Scores file dumped successfully.")
    except FileNotFoundError:
        await ctx.send("⚠️ No scores file found.")


# === Extension Setup ===
async def setup(bot):
    """Allow this module to be loaded as an extension."""
    print("✅ utils.py loaded successfully.")
