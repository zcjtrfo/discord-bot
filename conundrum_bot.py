import random
import asyncio
from discord.ext import commands
import config

def setup(bot: commands.Bot):
    # --- Load word list ---
    WORDS = []
    with open("conundrums.txt", encoding="utf-8") as f:
        for line in f:
            w = line.strip()
            if w:
                WORDS.append(w)

    # --- Active puzzles and locks ---
    if not hasattr(bot, "con_current"):
        bot.con_current = {}
    if not hasattr(bot, "con_locks"):
        bot.con_locks = {}

    # --- Message templates ---
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

    # --- Helper functions ---
    def scramble(word: str) -> str:
        letters = list(word)
        for _ in range(10):
            random.shuffle(letters)
            s = "".join(letters)
            if s.lower() != word.lower():
                return s
        return "".join(letters)

    def regional_indicator(word: str) -> str:
        return " ".join(
            f":regional_indicator_{ch}:" if 'a' <= ch.lower() <= 'z' else ch
            for ch in word.lower()
        )

    # --- Core function to post a new puzzle ---
    async def new_puzzle(channel):
        word = random.choice(WORDS)
        scrambled_word = scramble(word)
        bot.con_current[channel.id] = word

        scramble_emoji = regional_indicator(scrambled_word)
        msg_template = random.choice(SCRAMBLE_MESSAGES)
        formatted_message = msg_template.format(scrambled=f"\n>{scramble_emoji}<")
        await channel.send(formatted_message)

    # --- Expose new_puzzle for other modules ---
    bot.new_puzzle = new_puzzle
    bot.con_grats_messages = CONGRATS_MESSAGES

    # --- Message handler for conundrum channels ---
    @bot.event
    async def on_message(message):
        if message.author.bot:
            return

        if message.channel.id in [config.CONUNDRUM_CHANNEL_ID, config.TEST_CONUNDRUMS_CHANNEL_ID]:
            cid = message.channel.id
            if cid in bot.con_current and not message.content.startswith("!"):
                guess = message.content.strip().replace("?", "").lower()

                if guess in ["give up", "giveup"]:
                    answer = bot.con_current[cid]
                    await message.channel.send(f"💡 The answer is **{answer}**.")
                    await bot.new_puzzle(message.channel)
                    return

                if cid not in bot.con_locks:
                    bot.con_locks[cid] = asyncio.Lock()

                async with bot.con_locks[cid]:
                    if cid not in bot.con_current:
                        return

                    if guess == bot.con_current[cid].lower():
                        user_id = str(message.author.id)
                        existing_data = bot.scores.get(user_id, {})
                        name = message.author.display_name
                        con_score = existing_data.get("con_score", 0) + 1
                        num_score = existing_data.get("num_score", 0)

                        bot.scores[user_id] = {
                            "name": name,
                            "con_score": con_score,
                            "num_score": num_score,
                        }

                        with open(config.SCORES_FILE, "w", encoding="utf-8") as f:
                            json.dump(bot.scores, f, indent=2)

                        congrats = random.choice(bot.con_grats_messages).format(user=message.author.display_name)
                        await message.channel.send(congrats)

                        del bot.con_current[cid]
                        await bot.new_puzzle(message.channel)
                        return

        # Let other extensions process commands
        await bot.process_commands(message)

    print("✅ conundrum_bot.py loaded successfully.")
