import random
import asyncio
from bot import bot  # shared bot instance

# === Conundrum word list ===
WORDS = []
with open("conundrums.txt", encoding="utf-8") as f:
    for line in f:
        w = line.strip()
        if w:
            WORDS.append(w)

# === Active puzzles per channel ===
current = {}   # {channel_id: current_word}
locks = {}     # asyncio locks per channel

# === Message templates ===
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


# === Helper Functions ===
def scramble(word: str) -> str:
    """Randomly scramble a word, ensuring it's not identical to the original."""
    letters = list(word)
    for _ in range(10):
        random.shuffle(letters)
        s = "".join(letters)
        if s.lower() != word.lower():
            return s
    return "".join(letters)


def regional_indicator(word: str) -> str:
    """Convert a word into Discord regional indicator emojis."""
    return " ".join(
        f":regional_indicator_{ch}:" if 'a' <= ch.lower() <= 'z' else ch
        for ch in word.lower()
    )


# === Core Functionality ===
async def new_puzzle(channel):
    """Select a random word, scramble it, and post to the channel."""
    word = random.choice(WORDS)
    scrambled_word = scramble(word)
    current[channel.id] = word

    scramble_emoji = regional_indicator(scrambled_word)
    msg_template = random.choice(SCRAMBLE_MESSAGES)
    formatted_message = msg_template.format(scrambled=f"\n>{scramble_emoji}<")
    await channel.send(formatted_message)


# === Extension Setup ===
async def setup(bot):
    print("✅ conundrum_bot.py loaded successfully.")
