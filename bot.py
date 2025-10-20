import os
import random
import discord
import json
import requests
import re
import xml.etree.ElementTree as ET
os.environ["DISCORD_NO_AUDIO"] = "1"
from discord.ext import commands

# === Configuration ===
ALLOWED_CHANNEL_ID = 1424500871365918761
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

# === Maxes from selection ===
@bot.command(name="maxes")
async def maxes(ctx, *, selection: str):
    """
    Finds the longest possible words from the given selection using the FocalTools API.
    Usage: !maxes <letters>
    """
    import requests
    import xml.etree.ElementTree as ET
    import urllib.parse

    selection = selection.strip().upper()
    if not selection.isalpha() or len(selection) > 12:
        await ctx.send("⚠️ Selection must contain 12 letters or fewer (A–Z only).")
        return

    user_identifier = urllib.parse.quote(ctx.author.name)
    url = f"https://focaltools.azurewebsites.net/api/getwords/{selection}?ip={user_identifier}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Clean and check text
        text = response.text.strip()
        if not text.startswith("<"):
            raise ValueError(f"Unexpected response start: {text[:100]}")

        # Parse XML safely
        root = ET.fromstring(text)
        words = [el.text for el in root.findall(".//{http://schemas.microsoft.com/2003/10/Serialization/Arrays}string") if el.text]

        if not words:
            await ctx.send(f"⚠️ No words found for {selection}.")
            return

        max_len = max(len(w) for w in words)
        max_words = [w for w in words if len(w) == max_len]

        await ctx.send(f"Maxes from **{selection}**: *{', '.join(sorted(max_words))}*")

    except Exception as e:
        await ctx.send(f"⚠️ Could not parse API response — `{e}`")

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
    formatted_message = msg_template.format(scrambled=f"\n{scramble_emoji}")
    await channel.send(formatted_message)

# === Commands ===
@bot.command()
async def start(ctx):
    """Start the anagram quiz in this channel."""
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        await ctx.send("⚠️ This bot only runs in the designated channel.")
        return
    await new_puzzle(ctx.channel)
    await ctx.send("Started the quiz here! Reply with your answers.")

@bot.command()
async def stop(ctx):
    """Stop the quiz in this channel."""
    if ctx.channel.id != ALLOWED_CHANNEL_ID:
        await ctx.send("⚠️ This bot only runs in the designated channel.")
        return
    if ctx.channel.id in current:
        del current[ctx.channel.id]
        await ctx.send("Quiz stopped in this channel.")
    else:
        await ctx.send("No active quiz here.")

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

# === Message handling ===
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Only allow conundrum logic in the designated channel
    if message.channel.id == ALLOWED_CHANNEL_ID:
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
                # Update leaderboard
                user_id = str(message.author.id)
                scores[user_id] = {
                    "name": message.author.display_name,  # nickname if set
                    "score": scores.get(user_id, {}).get("score", 0) + 1
                }
                # Save to JSON
                with open(SCORES_FILE, "w", encoding="utf-8") as f:
                    json.dump(scores, f, indent=2)
                
                # Congratulate user
                congrats = random.choice(CONGRATS_MESSAGES).format(user=message.author.mention)
                await message.channel.send(congrats)
                await new_puzzle(message.channel)

    # Always allow command processing
    await bot.process_commands(message)

# === Run bot ===
if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Environment variable DISCORD_BOT_TOKEN is missing.")
    bot.run(token)









