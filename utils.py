import json
import random
import re
import requests
import urllib.parse
from discord.ext import commands
import discord
import config

def setup(bot: commands.Bot):
    # --- Load scores from bot ---
    if not hasattr(bot, "scores"):
        bot.scores = {}

    SCORES_FILE = config.SCORES_FILE

    # === Save scores helper ===
    def save_scores():
        with open(SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(bot.scores, f, indent=2)

    # --- Word check command ---
    @bot.command(name="check")
    async def check_word(ctx, *, term: str):
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
                await ctx.send(f"⚠️ Unexpected response: `{data}`")
        except requests.exceptions.RequestException as e:
            await ctx.send(f"❌ Error calling API: `{e}`")

    # --- Maxes command ---
    @bot.command(name="maxes")
    async def maxes(ctx, *, selection: str):
        selection = selection.strip().upper()
        if not re.fullmatch(r"[A-Z\*]+", selection):
            await ctx.send("⚠️ Only letters A–Z and up to two '*' wildcards.")
            return
        if selection.count("*") > 2:
            await ctx.send("⚠️ Maximum of two '*' wildcards allowed.")
            return
        if len(selection) > 12:
            await ctx.send("⚠️ Max length 12 characters including wildcards.")
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

    # --- Selection command ---
    @bot.command(name="selection")
    async def selection(ctx, *, args: str):
        args = args.strip()
        # letters
        import re
        if re.fullmatch(r"[A-Za-z]+", args.replace(" ", "")):
            letters = args.replace(" ", "").upper()
            emoji_output = " ".join(f":regional_indicator_{ch.lower()}:" for ch in letters)
            await ctx.send(f">{emoji_output}<")
            return
        # numbers
        try:
            numbers = [int(x) for x in args.split()]
        except ValueError:
            await ctx.send("⚠️ Provide letters A–Z or numbers separated by spaces.")
            return
        if len(numbers) < 3:
            await ctx.send("⚠️ Provide at least 3 numbers.")
            return
        *selection_nums, target = numbers
        valid_numbers = {1,2,3,4,5,6,7,8,9,10,25,50,75,100}
        if not all(n in valid_numbers for n in selection_nums):
            await ctx.send("⚠️ Only numbers [1–10,25,50,75,100] allowed.")
            return
        emoji_map = {
            1: ":one:", 2: ":two:", 3: ":three:", 4: ":four:", 5: ":five:",
            6: ":six:", 7: ":seven:", 8: ":eight:", 9: ":nine:", 10: ":number_10:",
            25: "<:twentyfive:1430640762655342602>",
            50: "<:fifty:1430640824244371617>",
            75: "<:seventyfive:1430640855173300325>",
            100: "<:onehundred:1430640895895670901>",
        }
        digit_map = {str(i): f":{['zero','one','two','three','four','five','six','seven','eight','nine'][i]}:" for i in range(10)}
        selection_emojis = " ".join(emoji_map.get(n,str(n)) for n in selection_nums)
        target_emojis = " ".join(digit_map[d] for d in str(target))
        await ctx.send(f":dart:--->{target_emojis}<---:dart:\n|-{selection_emojis}-|")

    # --- Test commands ---
    @bot.command(name="start_tests")
    @commands.has_permissions(manage_messages=True)
    async def start_tests(ctx):
        if ctx.channel.id != config.TEST_GENERAL_CHANNEL_ID:
            await ctx.send("⚠️ Cannot use this command here.")
            return
        from conundrum_bot import new_puzzle
        from numbers_bot import new_numbers_round
        con_channel = bot.get_channel(config.TEST_CONUNDRUMS_CHANNEL_ID)
        num_channel = bot.get_channel(config.TEST_NUMBERS_CHANNEL_ID)
        if con_channel:
            await new_puzzle(con_channel)
            await con_channel.send("🧩 Test Conundrum started!")
        if num_channel:
            await new_numbers_round(num_channel)
        await ctx.send("✅ Test quizzes started.")

    @bot.command(name="stop_tests")
    @commands.has_permissions(manage_messages=True)
    async def stop_tests(ctx):
        if ctx.channel.id != config.TEST_GENERAL_CHANNEL_ID:
            await ctx.send("⚠️ Cannot use this command here.")
            return
        from conundrum_bot import current as con_current
        from numbers_bot import current_numbers
        if config.TEST_CONUNDRUMS_CHANNEL_ID in con_current:
            del con_current[config.TEST_CONUNDRUMS_CHANNEL_ID]
            ch = bot.get_channel(config.TEST_CONUNDRUMS_CHANNEL_ID)
            if ch:
                await ch.send("🛑 Test Conundrum stopped.")
        if config.TEST_NUMBERS_CHANNEL_ID in current_numbers:
            del current_numbers[config.TEST_NUMBERS_CHANNEL_ID]
            ch = bot.get_channel(config.TEST_NUMBERS_CHANNEL_ID)
            if ch:
                await ch.send("🛑 Test Numbers stopped.")
        await ctx.send("✅ Test quizzes stopped.")

    # --- Leaderboard ---
    @bot.command(name="points")
    async def leaderboard(ctx):
        if not bot.scores:
            await ctx.send("No scores yet!")
            return
        cid = ctx.channel.id
        if cid in [config.CONUNDRUM_CHANNEL_ID, config.TEST_CONUNDRUMS_CHANNEL_ID]:
            key, title = "con_score", "🏆 Countdown Conundrum Leaderboard"
        elif cid in [config.NUMBERS_CHANNEL_ID, config.TEST_NUMBERS_CHANNEL_ID]:
            key, title = "num_score", "🔢 Countdown Numbers Leaderboard"
        else:
            await ctx.send("⚠️ Only Conundrum/Numbers channels.")
            return
        valid = {uid:info for uid,info in bot.scores.items() if info.get(key,0)>0}
        if not valid:
            await ctx.send("No scores yet for this category!")
            return
        top = sorted(valid.items(), key=lambda x: x[1][key], reverse=True)[:15]
        msg = f"**{title}**\n" + "\n".join(f"{i+1}. {info.get('name','Unknown')}: {info.get(key,0)}" for i,(uid,info) in enumerate(top))
        await ctx.send(msg)

    @bot.command(name="dump_scores")
    @commands.has_permissions(manage_messages=True)
    async def dump_scores_file(ctx):
        if ctx.channel.id != config.TEST_GENERAL_CHANNEL_ID:
            await ctx.send("⚠️ Cannot use this command here.")
            return
        try:
            await ctx.send(file=discord.File(SCORES_FILE))
            await ctx.send("✅ Scores dumped successfully.")
        except FileNotFoundError:
            await ctx.send("⚠️ No scores file found.")
