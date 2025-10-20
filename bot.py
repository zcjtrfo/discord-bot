import os
import random
import discord
import requests  # 👈 new import
os.environ["DISCORD_NO_AUDIO"] = "1"
from discord.ext import commands

# === Configuration ===
ALLOWED_CHANNEL_ID = 1424500871365918761
intents = discord.Intents.default()
intents.message_content = True  # make sure it's enabled in the Developer Portal
bot = commands.Bot(command_prefix="!", intents=intents)

# === Load words ===
WORDS = []
with open("conundrums.txt", encoding="utf-8") as f:
    for line in f:
        w = line.strip()
        if w:
            WORDS.append(w)

def scramble(word):
    letters = list(word)
    for _ in range(10):  # try to ensure shuffle differs from original
        random.shuffle(letters)
        s = "".join(letters)
        if s.lower() != word.lower():
            return s
    return "".join(letters)

def regional_indicator(word):
    """Convert letters in word to Discord regional_indicator emojis"""
    emoji_letters = []
    for ch in word.lower():
        if 'a' <= ch <= 'z':
            emoji_letters.append(f":regional_indicator_{ch}:")
        else:
            emoji_letters.append(ch)  # leave punctuation/numbers as-is
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

# active puzzles per channel/thread
current = {}

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (id: {bot.user.id})")

async def new_puzzle(channel):
    word = random.choice(WORDS)
    scrambled_word = scramble(word)
    current[channel.id] = word
    scramble_emoji = regional_indicator(scrambled_word)
    msg_template = random.choice(SCRAMBLE_MESSAGES)
    await channel.send(msg_template.format(scrambled=scramble_emoji))

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

# === Word validity check ===
@bot.command(name="check")
async def check_word(ctx, *, term: str):
    """
    Checks whether a word is valid using the FocalTools API.
    Usage: !check <word>
    """
    try:
        url = f"https://focaltools.azurewebsites.net/api/checkword/{term}?ip=c4c"
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

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Only allow the conundrum bot logic in the designated channel
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
                congrats = random.choice(CONGRATS_MESSAGES).format(user=message.author.mention)
                await message.channel.send(congrats)
                await new_puzzle(message.channel)

    # Let command processing continue (for !check etc.)
    await bot.process_commands(message)


if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Environment variable DISCORD_BOT_TOKEN is missing.")
    bot.run(token)

