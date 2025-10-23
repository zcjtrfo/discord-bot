import os
import random
import discord
import json
import requests
import re
import xml.etree.ElementTree as ET
os.environ["DISCORD_NO_AUDIO"] = "1"
from discord.ext import commands
from numbers_solver import solve_numbers
from parser import parse_numbers_solution

# === Configuration ===
ALLOWED_CHANNEL_ID = 1424500871365918761
NUMBERS_CHANNEL_ID = 1430278725739479153
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
    import requests
    import urllib.parse
    import json
    import re

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
current = {}
current_numbers = {}  # for the Numbers game

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

# === Moderator-only Conundrum Commands ===
@bot.command(name="start_conundrums")
@commands.has_permissions(manage_messages=True)
async def start_conundrums(ctx):
    """Start the anagram quiz in this channel (moderators only)."""
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        await ctx.send("⚠️ This bot only runs in the designated conundrum channel.")
        return

    await new_puzzle(ctx.channel)
    await ctx.send("🧩 Conundrum quiz started! Reply with your answers below.")

@bot.command(name="stop_conundrums")
@commands.has_permissions(manage_messages=True)
async def stop_conundrums(ctx):
    """Stop the anagram quiz in this channel (moderators only)."""
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        await ctx.send("⚠️ This bot only runs in the designated conundrum channel.")
        return

    if ctx.channel.id in current:
        del current[ctx.channel.id]
        await ctx.send("🛑 Conundrum quiz stopped.")
    else:
        await ctx.send("ℹ️ No active quiz is currently running here.")

@bot.command(name="points")
async def leaderboard(ctx):
    """Show top solvers."""
    if not scores:
        await ctx.send("No scores yet!")
        return

    # Sort top 25 by score
    top = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)[:25]

    msg = "**🏆 Countdown Conundrum Leaderboard**\n"
    for idx, (user_id, info) in enumerate(top, 1):
        name = info["name"]
        score = info["score"]
        msg += f"{idx}. {name}: {score}\n"

    await ctx.send(msg)

@bot.command(name="dump_scores")
async def dump_scores(ctx):
    with open(SCORES_FILE, "r") as f:
        data = f.read()
    await ctx.send(f"```json\n{data}\n```")

# === Numbers Game (numbers-bot channel only) ===
@bot.command(name="start_numbers")
@commands.has_permissions(manage_messages=True)
async def start_numbers(ctx):
    """Start a Countdown Numbers round (moderators only)."""
    if ctx.channel.id != NUMBERS_CHANNEL_ID:
        await ctx.send("⚠️ This command can only be used in the Numbers channel.")
        return

    await new_numbers_round(ctx.channel)


async def new_numbers_round(channel):
    """Generate and post a random solvable numbers puzzle with emoji formatting."""
    import random

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
        if solutions and solutions["results"]:
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

    # === Handle Numbers Channel ===
    if message.channel.id == NUMBERS_CHANNEL_ID:
        cid = message.channel.id
        if cid in current_numbers:
            guess = message.content.strip()

            # User gives up
            if guess.lower() in ["give up", "giveup"]:
                sol = current_numbers[cid]["solution"]
                await message.channel.send(f"💡 A possible solution was: `{sol}`")
                await new_numbers_round(message.channel)
                return

            # User attempts a guess
            selection = current_numbers[cid]["selection"]
            target = current_numbers[cid]["target"]

            result = parse_numbers_solution(guess, selection)
            if result is False:
                # silently ignore invalid attempts
                return

            if result == target:
                await message.channel.send(
                    f"🎉 {message.author.mention} solved it correctly!\n> `{guess}` = **{target}**"
                )
                await new_numbers_round(message.channel)
                return

    # === Handle Conundrum Channel ===
    elif message.channel.id == ALLOWED_CHANNEL_ID:
        cid = message.channel.id
        if cid in current:
            guess = message.content.strip().lower()

            # User gives up
            if guess in ["give up", "giveup"]:
                answer = current[cid]
                await message.channel.send(f"💡 The answer is **{answer}**.")
                await new_puzzle(message.channel)
                return

            # User guesses correctly
            if guess == current[cid].lower():
                user_id = str(message.author.id)
                scores[user_id] = {
                    "name": message.author.display_name,
                    "score": scores.get(user_id, {}).get("score", 0) + 1,
                }
                with open(SCORES_FILE, "w", encoding="utf-8") as f:
                    json.dump(scores, f, indent=2)

                congrats = random.choice(CONGRATS_MESSAGES).format(
                    user=message.author.mention
                )
                await message.channel.send(congrats)
                await new_puzzle(message.channel)

    # Always allow other commands to process
    await bot.process_commands(message)


# === Run bot ===
if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Environment variable DISCORD_BOT_TOKEN is missing.")
    bot.run(token)

























