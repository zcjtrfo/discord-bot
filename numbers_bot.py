import random
import asyncio
from discord.ext import commands
import config
from numbers_solver import solve_numbers

def setup(bot: commands.Bot):
    # --- Active puzzles and locks ---
    if not hasattr(bot, "num_current"):
        bot.num_current = {}
    if not hasattr(bot, "num_locks"):
        bot.num_locks = {}

    # --- Emoji maps ---
    NUMBER_EMOJIS = {
        1: ":one:", 2: ":two:", 3: ":three:", 4: ":four:", 5: ":five:",
        6: ":six:", 7: ":seven:", 8: ":eight:", 9: ":nine:", 10: ":number_10:",
        25: "<:twentyfive:1430640762655342602>",
        50: "<:fifty:1430640824244371617>",
        75: "<:seventyfive:1430640855173300325>",
        100: "<:onehundred:1430640895895670901>",
    }

    DIGIT_EMOJIS = {str(i): f":{['zero','one','two','three','four','five','six','seven','eight','nine'][i]}:" for i in range(10)}

    # --- Helpers ---
    def to_emoji(num: int) -> str:
        return NUMBER_EMOJIS.get(num, str(num))

    def target_to_emojis(target: int) -> str:
        return " ".join(DIGIT_EMOJIS[d] for d in str(target))

    # --- Core function to generate a numbers puzzle ---
    async def new_numbers_round(channel):
        while True:
            L = random.randint(0, 4)
            larges = random.sample([25,50,75,100], L)
            smalls = random.sample(
                [1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10],
                6-L
            )
            selection = larges + smalls
            target = random.randint(101, 999)

            solutions = solve_numbers(target, selection)
            if solutions and solutions.get("difference")==0 and solutions.get("results"):
                bot.num_current[channel.id] = {
                    "selection": selection,
                    "target": target,
                    "solution": solutions["results"][0][1],
                }

                selection_emojis = " ".join(to_emoji(n) for n in selection)
                target_emojis = target_to_emojis(target)
                intro_text = f"Your {L} large selection is:" if L>0 else "Your 6 small selection is:"
                await channel.send(
                    f"{intro_text}\n"
                    f":dart:--->{target_emojis}<---:dart:\n"
                    f"|-{selection_emojis}-|"
                )
                break

    # --- Expose function for utils.py or commands ---
    bot.new_numbers_round = new_numbers_round

    print("✅ numbers_bot.py loaded successfully.")
