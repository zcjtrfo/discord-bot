import os
import random
import re
import json
import requests
import urllib.parse
import asyncio
import xml.etree.ElementTree as ET

import discord
from discord.ext import commands
import aiohttp

from numbers_solver import solve_numbers
from parser import parse_numbers_solution

os.environ["DISCORD_NO_AUDIO"] = "1"

# === Configuration ===
CONUNDRUM_CHANNEL_ID = 1424500871365918761
NUMBERS_CHANNEL_ID = 1431380518179573911

# ✅ Test channels
TEST_GENERAL_CHANNEL_ID = 1424857126878052413
TEST_CONUNDRUMS_CHANNEL_ID = 1433910612009816356
TEST_NUMBERS_CHANNEL_ID = 1430278725739479153

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# === Word validity check ===
@bot.command(name="check")
async def check_word(ctx, *, term: str):
    """
    Checks whether a word is valid using the FocalTools API.
    Usage: !check <word>
    """
    try:
        # Use the Discord username as the IP value
        user_identifier = ctx.author.name
        url = f"https://focaltools.azurewebsites.net/api/checkword/{term}?ip={user_identifier}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.text.strip().lower()

        # Parse the XML boolean response
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
    """
    Finds the longest possible words from the given selection using the FocalTools API.
    Usage: !maxes <letters> (supports up to two '*' wildcards)
    """

    selection = selection.strip().upper()

    # ✅ Allow A–Z and up to 2 wildcard * characters
    if not re.fullmatch(r"[A-Z\*]+", selection):
        await ctx.send("⚠️ Selection must only contain letters A–Z and up to two '*' wildcards.")
        return

    if selection.count('*') > 2:
        await ctx.send("⚠️ You can use a maximum of two '*' wildcards.")
        return

    # ✅ Enforce total length ≤ 12 (including wildcards)
    if len(selection) > 12:
        await ctx.send("⚠️ Selection must contain 12 characters or fewer (including wildcards).")
        return

    user_identifier = urllib.parse.quote(ctx.author.name)
    url = f"https://focaltools.azurewebsites.net/api/getwords/{selection}?ip={user_identifier}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Parse JSON array
        words = json.loads(response.text)
        if not words:
            await ctx.send(f"⚠️ No words found for *{selection}*.")
            return

        max_len = max(len(w) for w in words)
        max_words = [w for w in words if len(w) == max_len]

        await ctx.send(f":arrow_up: Maxes from *{selection}*: **{', '.join(sorted(max_words))}**")

    except Exception as e:
        await ctx.send(f"⚠️ Could not process request — `{e}`")

# === Word definition lookup ===
@bot.command(name="define")
async def define_word(ctx, *, term: str):
    """
    Retrieves the definition of a word using the FocalTools API.
    Usage: !define <word>
    """
    try:
        # Use the Discord username as the IP value
        user_identifier = ctx.author.name
        url = f"https://focaltools.azurewebsites.net/api/define/{term}?ip={user_identifier}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.text.strip()

        # Extract the definition text from the XML response
        if "<string" in data and "</string>" in data:
            # Remove XML tags
            start = data.find(">") + 1
            end = data.rfind("</string>")
            definition = data[start:end].strip()

            # Send formatted message
            if definition:
                await ctx.send(f"📘 **Definition of {term.upper()}**:\n> {definition}")
            else:
                await ctx.send(f"⚠️ No definition found for **{term.upper()}**.")
        else:
            await ctx.send(f"⚠️ Unexpected response for **{term}**: `{data}`")

    except requests.exceptions.RequestException as e:
        await ctx.send(f"❌ Error calling the API: `{e}`")


@bot.command(name="selection")
async def selection(ctx, *, args: str):
    """
    Converts a string of letters (A–Z only) into regional indicator emojis,
    or a list of valid Countdown numbers into emoji formatting.
    Usage:
      • !selection COUNTDOWN
      • !selection 25 50 3 6 7 10 952
    """

    args = args.strip()

    # --- Check if input is letters ---
    if re.fullmatch(r"[A-Za-z]+", args.replace(" ", "")):
        letters = args.replace(" ", "").upper()
        emoji_output = " ".join(f":regional_indicator_{ch.lower()}:" for ch in letters)
        await ctx.send(f">{emoji_output}<")
        return

    # --- Check if input is numbers ---
    try:
        numbers = [int(x) for x in args.split()]
    except ValueError:
        await ctx.send("⚠️ Please provide either letters (A–Z) or numbers separated by spaces.")
        return

    # Must have at least 3 numbers (6 selection + 1 target typically)
    if len(numbers) < 3:
        await ctx.send("⚠️ Please provide at least 3 numbers (e.g. `!selection 25 50 3 6 7 10 952`).")
        return

    # Split into selection and target
    *selection, target = numbers

    # Valid Countdown numbers
    valid_numbers = {1,2,3,4,5,6,7,8,9,10,25,50,75,100}

    if not all(n in valid_numbers for n in selection):
        await ctx.send("⚠️ Only numbers from [1,2,3,4,5,6,7,8,9,10,25,50,75,100] are allowed in the selection.")
        return

    # Emoji maps
    emoji_map = {
        1: ":one:",
        2: ":two:",
        3: ":three:",
        4: ":four:",
        5: ":five:",
        6: ":six:",
        7: ":seven:",
        8: ":eight:",
        9: ":nine:",
        10: ":number_10:",
        25: "<:twentyfive:1430640762655342602>",
        50: "<:fifty:1430640824244371617>",
        75: "<:seventyfive:1430640855173300325>",
        100: "<:onehundred:1430640895895670901>",
    }

    digit_map = {
        "0": ":zero:",
        "1": ":one:",
        "2": ":two:",
        "3": ":three:",
        "4": ":four:",
        "5": ":five:",
        "6": ":six:",
        "7": ":seven:",
        "8": ":eight:",
        "9": ":nine:",
    }

    def to_emoji(num):
        return emoji_map.get(num, str(num))

    def target_to_emojis(target_num):
        return " ".join(digit_map[d] for d in str(target_num))

    # Format output
    selection_emojis = " ".join(to_emoji(n) for n in selection)
    target_emojis = target_to_emojis(target)

    await ctx.send(
        f":dart:--->{target_emojis}<---:dart:\n"
        f"|-{selection_emojis}-|"
    )



# === Load words ===
WORDS = []
with open("conundrums.txt", encoding="utf-8") as f:
    for line in f:
        w = line.strip()
        if w:
            WORDS.append(w)

def scramble(word):
    letters = list(word)
    for _ in range(10):
        random.shuffle(letters)
        s = "".join(letters)
        if s.lower() != word.lower():
            return s
    return "".join(letters)

def regional_indicator(word):
    emoji_letters = []
    for ch in word.lower():
        if 'a' <= ch <= 'z':
            emoji_letters.append(f":regional_indicator_{ch}:")
        else:
            emoji_letters.append(ch)
    return " ".join(emoji_letters)

# === Random message pools ===
CONGRATS_MESSAGES = [
    "🎉 That's correct, {user}!",
    "👏 Nice work, {user}!",
    "🔥 You nailed it, {user}!",
    "🥳 Brilliant, {user}!",
    "✅ Great stuff, {user}!",
    "⚡ Speedy, {user}!",
    "🏆 You got it first, {user}!",
    "🔟 Ten points to {user}!",
    "💡 Quick on the buzzer, {user}!",
    "👀 What a spot, {user}!",
]

SCRAMBLE_MESSAGES = [
    "Next conundrum: **{scrambled}**",
    "Try this one: **{scrambled}**",
    "Let's see if you can get this! **{scrambled}**",
    "Here's your next Countdown Conundrum: **{scrambled}**",
    "A new Countdown Conundrum awaits: **{scrambled}**",
    "Can you solve this conundrum? **{scrambled}**",
    "Here's a tricky one: **{scrambled}**",
    "Please reveal today's Countdown Conundrum: **{scrambled}**",
    "Fingers on buzzers: **{scrambled}**",
    "Quiet please, for the Countdown Conundrum: **{scrambled}**",
]

# === Active puzzles per channel/thread ===
current = {} # conundrums
current_numbers = {}  # for the Numbers game
locks = {}              # for conundrum channels
numbers_locks = {}      # for numbers channels

# === Leaderboard storage ===
SCORES_FILE = "scores.json"
try:
    with open(SCORES_FILE, "r", encoding="utf-8") as f:
        scores = json.load(f)
except FileNotFoundError:
    scores = {}

# === Bot events ===
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (id: {bot.user.id})")

async def new_puzzle(channel):
    word = random.choice(WORDS)
    scrambled_word = scramble(word)
    current[channel.id] = word
    scramble_emoji = regional_indicator(scrambled_word)
    msg_template = random.choice(SCRAMBLE_MESSAGES)
    formatted_message = msg_template.format(scrambled=f"\n>{scramble_emoji}<")
    await channel.send(formatted_message)

# === Moderator-only Conundrum & Numbers Commands (updated) ===

# === Test-only Commands ===
@bot.command(name="start_tests")
@commands.has_permissions(manage_messages=True)
async def start_tests(ctx):
    """Start both test conundrum and numbers quizzes (usable only in #test_general)."""
    if ctx.channel.id != TEST_GENERAL_CHANNEL_ID:
        await ctx.send("⚠️ This command can't be used in this channel.")
        return

    test_conundrum_channel = bot.get_channel(TEST_CONUNDRUMS_CHANNEL_ID)
    test_numbers_channel = bot.get_channel(TEST_NUMBERS_CHANNEL_ID)

    if test_conundrum_channel:
        await new_puzzle(test_conundrum_channel)
        await test_conundrum_channel.send("🧩 Test Conundrum quiz started! Reply with your answers below.")
    if test_numbers_channel:
        await new_numbers_round(test_numbers_channel)

    await ctx.send("✅ Test quizzes started in #test_conundrums and #test_numbers.")


@bot.command(name="stop_tests")
@commands.has_permissions(manage_messages=True)
async def stop_tests(ctx):
    """Stop both test conundrum and numbers quizzes (usable only in #test_general)."""
    if ctx.channel.id != TEST_GENERAL_CHANNEL_ID:
        await ctx.send("⚠️ This command can't be used in this channel.")
        return

    # Stop test conundrum
    if TEST_CONUNDRUMS_CHANNEL_ID in current:
        del current[TEST_CONUNDRUMS_CHANNEL_ID]
        ch = bot.get_channel(TEST_CONUNDRUMS_CHANNEL_ID)
        if ch:
            await ch.send("🛑 Test Conundrum quiz stopped.")

    # Stop test numbers
    if TEST_NUMBERS_CHANNEL_ID in current_numbers:
        del current_numbers[TEST_NUMBERS_CHANNEL_ID]
        ch = bot.get_channel(TEST_NUMBERS_CHANNEL_ID)
        if ch:
            await ch.send("🛑 Test Numbers quiz stopped.")

    await ctx.send("✅ Test quizzes stopped in #test_conundrums and #test_numbers.")


@bot.command(name="start_bots")
@commands.has_permissions(manage_messages=True)
async def start_bots(ctx):
    """Start all bots (conundrums + numbers) across all channels from test_general."""
    if ctx.channel.id != TEST_GENERAL_CHANNEL_ID:
        await ctx.send("⚠️ This command can't be used in this channel.")
        return

    # All four channels
    all_channels = [
        bot.get_channel(CONUNDRUM_CHANNEL_ID),
        bot.get_channel(TEST_CONUNDRUMS_CHANNEL_ID),
        bot.get_channel(NUMBERS_CHANNEL_ID),
        bot.get_channel(TEST_NUMBERS_CHANNEL_ID),
    ]

    for ch in all_channels:
        if ch:
            if ch.id in [CONUNDRUM_CHANNEL_ID, TEST_CONUNDRUMS_CHANNEL_ID]:
                await new_puzzle(ch)
                await ch.send("🧩 Conundrum quiz started! Reply with your answers below.")
            elif ch.id in [NUMBERS_CHANNEL_ID, TEST_NUMBERS_CHANNEL_ID]:
                await new_numbers_round(ch)
    await ctx.send("✅ All bots started in all quiz channels.")


@bot.command(name="stop_bots")
@commands.has_permissions(manage_messages=True)
async def stop_bots(ctx):
    """Stop all bots (conundrums + numbers) across all channels from test_general."""
    if ctx.channel.id != TEST_GENERAL_CHANNEL_ID:
        await ctx.send("⚠️ This command can't be used in this channel.")
        return

    # Stop all current quizzes
    for cid in list(current.keys()):
        del current[cid]
    for cid in list(current_numbers.keys()):
        del current_numbers[cid]

    # Inform the channels
    for ch_id in [
        CONUNDRUM_CHANNEL_ID, TEST_CONUNDRUMS_CHANNEL_ID,
        NUMBERS_CHANNEL_ID, TEST_NUMBERS_CHANNEL_ID
    ]:
        ch = bot.get_channel(ch_id)
        if ch:
            await ch.send("🛑 Quiz has been temporarily stopped.")

    await ctx.send("✅ All bots stopped across all quiz channels.")

@bot.command(name="points")
async def leaderboard(ctx):
    """Show top solvers for either Conundrum or Numbers rounds (works in test & main channels)."""
    if not scores:
        await ctx.send("No scores yet!")
        return

    channel_id = ctx.channel.id

    # Determine which leaderboard to show
    if channel_id in [CONUNDRUM_CHANNEL_ID, TEST_CONUNDRUMS_CHANNEL_ID]:
        key = "con_score"
        title = "🏆 Countdown Conundrum Leaderboard"
    elif channel_id in [NUMBERS_CHANNEL_ID, TEST_NUMBERS_CHANNEL_ID]:
        key = "num_score"
        title = "🔢 Countdown Numbers Leaderboard"
    else:
        await ctx.send("⚠️ This command can only be used in the Conundrum or Numbers channels.")
        return

    # Filter out users with 0 in this category
    valid_scores = {uid: info for uid, info in scores.items() if info.get(key, 0) > 0}

    if not valid_scores:
        await ctx.send("No scores yet for this category!")
        return

    # Sort all users by score descending
    sorted_scores = sorted(valid_scores.items(), key=lambda x: x[1][key], reverse=True)

    msg = f"**{title}**\n"
    user_id_str = str(ctx.author.id)
    user_rank_info = None

    for idx, (uid, info) in enumerate(sorted_scores, 1):
        name = info.get("name", "Unknown User")
        score_value = info.get(key, 0)

        # Build top 15 leaderboard
        if idx <= 15:
            msg += f"{idx}. {name}: {score_value}\n"

        # Check if this is the command user
        if str(uid) == user_id_str:
            user_rank_info = (idx, score_value)

    # If user is not in top 15, append their rank
    if user_rank_info and user_rank_info[0] > 15:
        msg += f"\n{user_rank_info[0]}. {ctx.author.display_name}: {user_rank_info[1]}"

    await ctx.send(msg)



@bot.command(name="dump_scores")
@commands.has_permissions(manage_messages=True)
async def dump_scores_file(ctx):
    """Send the current scores.json file (only usable from #test_general)."""
    if ctx.channel.id != TEST_GENERAL_CHANNEL_ID:
        await ctx.send("⚠️ This command can't be used in this channel.")
        return

    try:
        await ctx.send(file=discord.File("scores.json"))
        await ctx.send("✅ Scores file dumped successfully.")
    except FileNotFoundError:
        await ctx.send("⚠️ No scores file found.")

# === Numbers Game (numbers-bot channel only) ===
async def new_numbers_round(channel):
    """Generate and post a random solvable numbers puzzle with emoji formatting."""

    # Emoji map for all valid Countdown numbers
    emoji_map = {
        1: ":one:",
        2: ":two:",
        3: ":three:",
        4: ":four:",
        5: ":five:",
        6: ":six:",
        7: ":seven:",
        8: ":eight:",
        9: ":nine:",
        10: ":number_10:",
        25: "<:twentyfive:1430640762655342602>",
        50: "<:fifty:1430640824244371617>",
        75: "<:seventyfive:1430640855173300325>",
        100: "<:onehundred:1430640895895670901>",
    }

    def to_emoji(num):
        """Convert a number to its corresponding emoji string."""
        return emoji_map.get(num, str(num))

    def target_to_emojis(target):
        """Convert each digit of the target into emoji numbers (e.g. 527 → :five: :two: :seven:)."""
        digit_map = {
            "0": ":zero:",
            "1": ":one:",
            "2": ":two:",
            "3": ":three:",
            "4": ":four:",
            "5": ":five:",
            "6": ":six:",
            "7": ":seven:",
            "8": ":eight:",
            "9": ":nine:",
        }
        return " ".join(digit_map[d] for d in str(target))

    while True:
        L = random.randint(0, 4)
        larges = random.sample([25, 50, 75, 100], L)
        smalls = random.sample(
            [1, 1, 2, 2, 3, 3, 4, 4, 5, 5,
             6, 6, 7, 7, 8, 8, 9, 9, 10, 10],
            6 - L
        )
        selection = larges + smalls
        target = random.randint(101, 999)

        solutions = solve_numbers(target, selection)
        if solutions and solutions.get("difference") == 0 and solutions.get("results"):
            current_numbers[channel.id] = {
                "selection": selection,
                "target": target,
                "solution": solutions["results"][0][1],
            }

            selection_emojis = " ".join(to_emoji(n) for n in selection)
            target_emojis = target_to_emojis(target)

            # Dynamic intro text
            if L == 0:
                intro_text = "Your 6 small selection is:"
            else:
                intro_text = f"Your {L} large selection is:"

            await channel.send(
                f"{intro_text}\n"
                f":dart:--->{target_emojis}<---:dart:\n"
                f"|-{selection_emojis}-|"

            )
            break


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # --- NUMBERS CHANNELS (main + test) ---
    if message.channel.id in [NUMBERS_CHANNEL_ID, TEST_NUMBERS_CHANNEL_ID]:
        cid = message.channel.id
        if cid in current_numbers and not message.content.startswith("!"):
            guess = message.content.strip()

            # User gives up
            if guess.lower() in ["give up", "giveup"]:
                sol = current_numbers[cid]["solution"]
                await message.channel.send(f"💡 A possible solution was: `{sol}`")
                await new_numbers_round(message.channel)
                return

            selection = current_numbers[cid]["selection"]
            target = current_numbers[cid]["target"]

            result = parse_numbers_solution(guess, selection)
            if result is False:
                return  # ignore invalid attempts

            if cid not in numbers_locks:
                numbers_locks[cid] = asyncio.Lock()

            async with numbers_locks[cid]:
                if cid not in current_numbers:
                    return  # already solved

                if result == target:
                    user_id = str(message.author.id)
                    existing_data = scores.get(user_id, {})
                    name = message.author.display_name
                    con_score = existing_data.get("con_score", 0)
                    num_score = existing_data.get("num_score", 0) + 1

                    scores[user_id] = {
                        "name": name,
                        "con_score": con_score,
                        "num_score": num_score,
                    }

                    with open(SCORES_FILE, "w", encoding="utf-8") as f:
                        json.dump(scores, f, indent=2)

                    congrats = random.choice(CONGRATS_MESSAGES).format(user=message.author.display_name)
                    await message.channel.send(f"{congrats}\n> `{guess}` = **{target}**")

                    del current_numbers[cid]
                    await new_numbers_round(message.channel)
                    return

    # --- CONUNDRUM CHANNELS (main + test) ---
    elif message.channel.id in [CONUNDRUM_CHANNEL_ID, TEST_CONUNDRUMS_CHANNEL_ID]:
        cid = message.channel.id
        if cid in current and not message.content.startswith("!"):
            guess = message.content.strip().replace("?", "").lower()

            if guess in ["give up", "giveup"]:
                answer = current[cid]
                await message.channel.send(f"💡 The answer is **{answer}**.")
                await new_puzzle(message.channel)
                return

            if cid not in locks:
                locks[cid] = asyncio.Lock()

            async with locks[cid]:
                if cid not in current:
                    return  # already solved

                if guess == current[cid].lower():
                    user_id = str(message.author.id)
                    existing_data = scores.get(user_id, {})
                    name = message.author.display_name
                    con_score = existing_data.get("con_score", 0) + 1
                    num_score = existing_data.get("num_score", 0)

                    scores[user_id] = {
                        "name": name,
                        "con_score": con_score,
                        "num_score": num_score,
                    }

                    with open(SCORES_FILE, "w", encoding="utf-8") as f:
                        json.dump(scores, f, indent=2)

                    congrats = random.choice(CONGRATS_MESSAGES).format(user=message.author.display_name)
                    await message.channel.send(congrats)

                    del current[cid]
                    await new_puzzle(message.channel)
                    return

    # Always allow commands to process
    await bot.process_commands(message)



# === Run bot ===
if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Environment variable DISCORD_BOT_TOKEN is missing.")
    bot.run(token)









