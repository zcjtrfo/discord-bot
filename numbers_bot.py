=import random
import asyncio
from bot import bot, current_numbers, numbers_locks  # import shared state
from numbers_solver import solve_numbers

# === Emoji maps ===
NUMBER_EMOJIS = {
    1: ":one:", 2: ":two:", 3: ":three:", 4: ":four:", 5: ":five:",
    6: ":six:", 7: ":seven:", 8: ":eight:", 9: ":nine:", 10: ":number_10:",
    25: "<:twentyfive:1430640762655342602>",
    50: "<:fifty:1430640824244371617>",
    75: "<:seventyfive:1430640855173300325>",
    100: "<:onehundred:1430640895895670901>",
}

DIGIT_EMOJIS = {
    "0": ":zero:", "1": ":one:", "2": ":two:", "3": ":three:", "4": ":four:",
    "5": ":five:", "6": ":six:", "7": ":seven:", "8": ":eight:", "9": ":nine:",
}


# === Helper Functions ===
def to_emoji(num: int) -> str:
    """Convert a number to its emoji representation."""
    return NUMBER_EMOJIS.get(num, str(num))


def target_to_emojis(target: int) -> str:
    """Convert each digit of the target number into emoji numbers."""
    return " ".join(DIGIT_EMOJIS[d] for d in str(target))


# === Core Functionality ===
async def new_numbers_round(channel):
    """
    Generate a random solvable Countdown Numbers puzzle and post it in the channel.
    Stores the solution in current_numbers[channel.id].
    """
    while True:
        L = random.randint(0, 4)
        larges = random.sample([25, 50, 75, 100], L)
        smalls = random.sample(
            [1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10],
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

            intro_text = f"Your {L} large selection is:" if L > 0 else "Your 6 small selection is:"

            await channel.send(
                f"{intro_text}\n"
                f":dart:--->{target_emojis}<---:dart:\n"
                f"|-{selection_emojis}-|"
            )
            break


# === Extension Setup ===
async def setup(bot):
    print("✅ numbers_bot.py loaded successfully.")
