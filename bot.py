import os
import random
import re
import json
import requests
import urllib.parse
import asyncio
import datetime
import xml.etree.ElementTree as ET
from collections import Counter

import discord
from discord.ext import commands
from discord.ext import tasks
import aiohttp

from numbers_solver import solve_numbers
from parser import parse_numbers_solution, normalize_expression

os.environ["DISCORD_NO_AUDIO"] = "1"

# === Configuration ===
CONUNDRUM_CHANNEL_ID = 1424500871365918761
NUMBERS_CHANNEL_ID = 1431380518179573911
LETTERS_CHANNEL_ID = 1438454341920100423

# ✅ Test channels
TEST_GENERAL_CHANNEL_ID = 1424857126878052413
TEST_CONUNDRUMS_CHANNEL_ID = 1433910612009816356
TEST_NUMBERS_CHANNEL_ID = 1430278725739479153
TEST_LETTERS_CHANNEL_ID = 1436448481182220328

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Custom Emoji Maps (Replace IDs with your actual custom emoji IDs) ---

# 1. Custom Emojis for Letters A-Z
# *** YOU MUST REPLACE THE PLACEHOLDER IDs WITH YOUR ACTUAL CUSTOM EMOJI IDs ***
LETTER_EMOJI_MAP = {
    'A': '<:a_:1443944916039503942>', 'B': '<:b_:1443945023564419123>', 'C': '<:c_:1443945049246138502>',
    'D': '<:d_:1443945068867092561>', 'E': '<:e_:1443945090220298300>', 'F': '<:f_:1443945112693375117>',
    'G': '<:g_:1443945137292967936>', 'H': '<:h_:1443945156960325672>', 'I': '<:i_:1443945180024672377>',
    'J': '<:j_:1443945199784034436>', 'K': '<:k_:1444066307762032772>', 'L': '<:l_:1444066346093772902>',
    'M': '<:m_:1444066371007942777>', 'N': '<:n_:1444066405728256021>', 'O': '<:o_:1444066434777874654>',
    'P': '<:p_:1444066465249497271>', 'Q': '<:q_:1444066490033897524>', 'R': '<:r_:1444066521856081951>',
    'S': '<:s_:1444066546191302708>', 'T': '<:t_:1444066574762770442>', 'U': '<:u_:1444066601656647770>',
    'V': '<:v_:1444066635723051199>', 'W': '<:w_:1444066667930980443>', 'X': '<:x_:1444066897019797646>',
    'Y': '<:y_:1444066919496941689>', 'Z': '<:z_:1444066945358893177>',
}

# 2. Unified Custom Emojis for ALL Numbers (0-10, 25, 50, 75, 100)
# This map is used for selection numbers (by number) AND target digits (by string/key).
# *** YOU MUST REPLACE THE PLACEHOLDER IDs WITH YOUR ACTUAL CUSTOM EMOJI IDs ***
NUMBER_EMOJI_MAP = {
    # Digits 0-9
    "0": '<:n_zero:1444443623201574962>',
    "1": '<:n_one:1444443729091104920>',
    "2": '<:n_two:1444443674963476622>',
    "3": '<:n_three:1444443647331537007>',
    "4": '<:n_four:1444443589957648555>',
    "5": '<:n_five:1444443560471560353>',
    "6": '<:n_six:1444443500081971414>',
    "7": '<:n_seven:1444443532688490556>',
    "8": '<:n_eight:1444443465030303854>',
    "9": '<:n_nine:1444443435422453880>',
    
    # Selection Numbers (Keys are integers)
    1: '<:n_one:1444443729091104920>',
    2: '<:n_two:1444443674963476622>',
    3: '<:n_three:1444443647331537007>',
    4: '<:n_four:1444443589957648555>',
    5: '<:n_five:1444443560471560353>',
    6: '<:n_six:1444443500081971414>',
    7: '<:n_seven:1444443532688490556>',
    8: '<:n_eight:1444443465030303854>',
    9: '<:n_nine:1444443435422453880>',
    10: '<:ten:1444239787782574141>',
    25: "<:twentyfive:1430640762655342602>",
    50: "<:fifty:1430640824244371617>",
    75: "<:seventyfive:1430640855173300325>",
    100: "<:onehundred:1430640895895670901>",
}

# === Word validity check with historical info ===
@bot.command(name="check", aliases=["history"])
async def check_word(ctx, *, term: str):
    """
    Checks whether a word is valid using the FocalTools API and reports its historical validity.
    Usage: !check <word>
    """
    try:
        # === Step 1: Prepare word and call API ===
        word = term.strip().upper()
        user_identifier = ctx.author.name
        url = f"https://focaltools.azurewebsites.net/api/checkword/{word}?ip={user_identifier}"

        # --- Use aiohttp for non-blocking requests ---
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                data = (await response.text()).strip().lower()

        # === Step 2: If word is >9 letters, skip history lookup ===
        skip_history = len(word) > 9

        # === Step 3: Lookup helper functions ===
        def lookup_history(filename, word):
            """Look up a word in the specified history file and return its associated date string."""
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split("\t")
                        if len(parts) >= 2 and parts[0].strip().upper() == word:
                            return parts[1].strip()
            except FileNotFoundError:
                return None
            return None

        def format_history_message(date_str, valid=True):
            """Interpret the date string and return a formatted sentence."""
            if not date_str:
                return (
                    "I can't find a record of when this word became valid; it was probably very recently added."
                    if valid
                    else "I can't find a record of this word being removed; it may never have been valid."
                )

            # === Special dictionary events ===
            if not valid:
                if re.search(r"06/2016", date_str):
                    return "This word was removed in the Great OED Variant Cull of June 2016."
                if re.search(r"08/2024", date_str):
                    return "This word was removed in the Great Dictionary Reset of August 2024."

            # === Exact date format: dd/mm/yy or dd/mm/yyyy ===
            m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", date_str)
            if m:
                day, month, year = map(int, m.groups())
                if year < 100:
                    year += 2000
                month_name = datetime.date(year, month, 1).strftime("%B")
                if valid:
                    return f"This word has been valid since {month_name} {year}."
                else:
                    return f"This word was removed in {month_name} {year}."

            # === Between years format: between 2006 - 2012 ===
            m = re.match(r"between\s+(\d{4})\s*[-–]\s*(\d{4})", date_str, re.IGNORECASE)
            if m:
                y1, y2 = m.groups()
                if valid:
                    return f"This word became valid sometime between {y1} and {y2}."
                else:
                    return f"This word was removed sometime between {y1} and {y2}."

            # === Pre-2006 ===
            if re.match(r"pre[-–]?\s*2006", date_str, re.IGNORECASE):
                if valid:
                    return "This word has likely always been valid."
                else:
                    return "This word was removed before 2006."

            # Fallback
            return f"(Unrecognized date format: {date_str})"

        # === Step 4: Send response ===
        if "true" in data:
            msg = f"✅ **{word}** is **VALID**"
            if not skip_history:
                date_info = lookup_history("history_valid.txt", word)
                msg += "\n" + format_history_message(date_info, valid=True)
            await ctx.send(msg)

        elif "false" in data:
            msg = f"❌ **{word}** is **INVALID**"
            if not skip_history:
                date_info = lookup_history("history_invalid.txt", word)
                msg += "\n" + format_history_message(date_info, valid=False)
            await ctx.send(msg)

        else:
            await ctx.send(f"⚠️ Unexpected response for **{word}**: `{data}`")

    except asyncio.TimeoutError:
        await ctx.send("⏳ The FocalTools API took too long to respond. Please try again in a moment.")

    except aiohttp.ClientError as e:
        await ctx.send(f"🌐 Network error contacting FocalTools API: `{e}`")

    except Exception as e:
        await ctx.send(f"❌ Unexpected error: `{e}`")

def fit_words(words: list, budget: int) -> str:
    """
    Join words with ', ' fitting within budget characters.
    Appends ', ...' if truncated. Never cuts a word mid-way.
    """
    result = []
    used = 0
    for i, w in enumerate(words):
        sep = ", " if result else ""
        is_last = (i == len(words) - 1)
        # Reserve room for ', ...' unless this is the last word
        needed = len(sep) + len(w) + (0 if is_last else len(", ..."))
        if used + needed <= budget:
            result.append(w)
            used += len(sep) + len(w)
        else:
            return (", ".join(result) + ", ...") if result else w[:budget]
    return ", ".join(result)


def mark_wildcards(word: str, letters: str) -> str:
    """
    Returns the word with any letters that required a wildcard ('*') wrapped in
    Discord underline markdown (__xy__). Consecutive wildcard letters are merged
    into a single __...__ span to avoid broken markdown.
    """
    num_wildcards = letters.count('*')
    if num_wildcards == 0:
        return word
    pool = Counter(c for c in letters if c != '*')
    wildcards_used = 0
    # Build a list of (char, is_wildcard) tuples
    tagged = []
    for ch in word:
        if pool[ch] > 0:
            pool[ch] -= 1
            tagged.append((ch, False))
        elif wildcards_used < num_wildcards:
            wildcards_used += 1
            tagged.append((ch, True))
        else:
            tagged.append((ch, False))
    # Merge consecutive wildcard spans into a single __...__ block
    result = []
    i = 0
    while i < len(tagged):
        ch, is_wc = tagged[i]
        if is_wc:
            span = []
            while i < len(tagged) and tagged[i][1]:
                span.append(tagged[i][0])
                i += 1
            result.append(f"__{''.join(span)}__")
        else:
            result.append(ch)
            i += 1
    return "".join(result)


@bot.command(name="maxes", aliases=["max"])
async def maxes(ctx, *, selection: str):
    """
    Case A: !maxes <letters> <n>  -> getwords, parse JSON or XML, filter by length n.
    Case B: !maxes <letters>      -> getmaxes, JSON only (original behaviour).
    """

    # 1) Character limit raised to 1800
    async def send_limited(message: str):
        if len(message) > 1800:
            message = message[:1797] + "**..."
        await ctx.send(message)

    parts = selection.strip().upper().split()

    # -----------------------
    # CASE A detection
    # -----------------------
    if len(parts) == 2 and parts[1].isdigit():
        letters = parts[0]
        n = int(parts[1])

        if not (1 <= n <= 12):
            await send_limited("⚠️ The length number must be between 1 and 12.")
            return

        if not re.fullmatch(r"[A-Z\*]+", letters):
            await send_limited("⚠️ Letter selection must only contain A–Z and up to two '*' wildcards.")
            return

        if letters.count('*') > 2:
            await send_limited("⚠️ You can use a maximum of two '*' wildcards.")
            return

        if len(letters) > 12:
            await send_limited("⚠️ Selection must contain 12 characters or fewer (including wildcards).")
            return

        url = f"https://focaltools.azurewebsites.net/api/getwords/{letters}?ip=c4c"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response.raise_for_status()
                    text = await response.text()

            words = None
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    words = [w.upper() for w in parsed if isinstance(w, str)]
            except json.JSONDecodeError:
                pass

            if words is None:
                words = re.findall(r"<string>(.*?)</string>", text)
                words = [w.upper() for w in words]

            words = [w for w in words if len(w) == n]
            display_letters = letters.replace('*', '?')

            if not words:
                await send_limited(f"⚠️ No words of length **{n}** found for *{display_letters}*.")
                return

            # Sort and join words; mark wildcard letters with underline if wildcards present
            sorted_words = sorted(words)
            marked = [mark_wildcards(w, letters) for w in sorted_words]
            prefix = f":arrow_up: Words of length **{n}** from *{display_letters}*: **"
            suffix = "**"
            formatted_words = fit_words(marked, 1800 - len(prefix) - len(suffix))
            await send_limited(f"{prefix}{formatted_words}{suffix}")
            return

        except asyncio.TimeoutError:
            await send_limited(f"⏳ Timeout fetching words for *{letters.replace('*', '?')}*. Please try again.")
            return
        except Exception as e:
            await send_limited(f"⚠️ Could not process request — `{e}`")
            return

    # -----------------------
    # CASE B (original)
    # -----------------------
    selection = selection.strip().upper()

    if not re.fullmatch(r"[A-Z\*]+", selection):
        await send_limited("⚠️ Selection must only contain letters A–Z and up to two '*' wildcards.")
        return

    if selection.count('*') > 2:
        await send_limited("⚠️ You can use a maximum of two '*' wildcards.")
        return

    if len(selection) > 12:
        await send_limited("⚠️ Selection must contain 12 characters or fewer (including wildcards).")
        return

    user_identifier = urllib.parse.quote(ctx.author.name)
    url = f"https://focaltools.azurewebsites.net/api/getmaxes/{selection}?ip={user_identifier}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                text = await response.text()

        words = json.loads(text)
        display_selection = selection.replace('*', '?')

        if not words:
            await send_limited(f"⚠️ No words found for *{display_selection}*.")
            return

        # Sort and join words; mark wildcard letters with underline if wildcards present
        sorted_words = sorted([w.upper() for w in words])
        marked = [mark_wildcards(w, selection) for w in sorted_words]
        prefix = f":arrow_up: Maxes from *{display_selection}*: **"
        suffix = "**"
        formatted_words = fit_words(marked, 1800 - len(prefix) - len(suffix))
        await send_limited(f"{prefix}{formatted_words}{suffix}")

    except json.JSONDecodeError:
        await send_limited(f"⚠️ Unexpected response format from API for *{selection.replace('*', '?')}*.")
    except Exception as e:
        await send_limited(f"⚠️ Could not process request — `{e}`")





# === Word definition lookup (with input validation) ===
@bot.command(name="define", aliases=["definition", "meaning"])
async def define_word(ctx, *, term: str):
    """
    Retrieves the definition of a word using the FocalTools API.
    Usage: !define <word>
    Only accepts single alphabetic words (A–Z).
    """
    term = term.strip()

    # ✅ Validate input (only A–Z, one word)
    if not re.fullmatch(r"[A-Za-z]+", term):
        await ctx.send(
            "⚠️ Please provide a **single word** containing only letters A–Z.\n"
            "Example: `!define apple`"
        )
        return

    user_identifier = ctx.author.name
    url = f"https://focaltools.azurewebsites.net/api/define/{term}?ip={user_identifier}"

    try:
        # --- Async HTTP request using aiohttp ---
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                data = (await response.text()).strip()

        # --- Extract text whether XML or plain ---
        if "<string" in data and "</string>" in data:
            start = data.find(">") + 1
            end = data.rfind("</string>")
            definition = data[start:end].strip()
        else:
            definition = data

        # --- Clean up formatting ---
        definition = definition.strip('"').strip("'").strip()
        normalized = definition.upper()

        # --- Handle known response cases ---
        if normalized == "DEFINITION NOT FOUND":
            await ctx.send(f"ℹ️ No definition found for **{term.upper()}**.")
            return
        elif normalized == "INVALID":
            await ctx.send(f"❌ **{term.upper()}** is not a valid word.")
            return
        elif not definition:
            await ctx.send(f"⚠️ No definition found for **{term.upper()}**.")
            return

        # --- Send valid definition ---
        await ctx.send(f"📘 **Definition of {term.upper()}**:\n> {definition}")

    except asyncio.TimeoutError:
        await ctx.send("⏳ The dictionary service took too long to respond. Please try again later.")

    except aiohttp.ClientError as e:
        await ctx.send(f"🌐 Network error contacting dictionary API: `{e}`")

    except Exception as e:
        await ctx.send(f"❌ Unexpected error while fetching definition: `{e}`")


# === Quantum Tombola solver link (no preview) + solution info ===
@bot.command(name="solve")
async def solve(ctx, *, input_text: str):
    """
    Generates a link to Quantum Tombola solutions and shows one example if possible.
    Usage: !solve <num1> <num2> ... <num6> <target>
    """

    # Split input by spaces
    parts = input_text.strip().split()

    # Validate: at least 3 numbers (2–6 selections + 1 target)
    if len(parts) < 3 or len(parts) > 7:
        await ctx.send(
            "⚠️ Invalid input. Please provide **between 2 and 6 selection numbers** followed by **1 target number**.\n"
            "Example: `!solve 100 75 50 25 6 3 952`"
        )
        return

    # Ensure all parts are digits only
    if not all(part.isdigit() for part in parts):
        await ctx.send("⚠️ All inputs must be numbers only (no letters or symbols).")
        return

    # Split selection and target
    *selection_numbers, target = parts
    target = int(target)
    selection = [int(n) for n in selection_numbers]

    try:
        # Try to find one example solution first
        solutions = solve_numbers(target, selection)
        message_lines = []

        if solutions and solutions.get("results"):
            sol = solutions["results"][0][1]
            diff = solutions.get("difference", None)

            if diff == 0:
                message_lines.append(f"💡 A possible solution is: `{sol}`")
            else:
                message_lines.append(f"💡 The closest is **{diff}** away. A possible solution is: `{sol}`")
        else:
            message_lines.append("⚠️ No solutions found.")

    except Exception as e:
        await ctx.send(f"⚠️ Could not generate example solution — `{e}`")
        return

    # Construct URL + link text
    selection_param = "-".join(selection_numbers)
    url = f"https://greem.co.uk/quantumtombola/?sel={urllib.parse.quote(selection_param)}&target={urllib.parse.quote(str(target))}"
    message_lines.append(f"See all solutions in Quantum Tombola:\n<{url}>")

    # Send both messages together, in the correct order
    await ctx.send("\n".join(message_lines))


@bot.command(name="selection")
async def selection(ctx, *, args: str):
    """
    Converts letters/numbers to emojis. After 40 seconds, 
    automatically posts the solution using !maxes or !solve.
    """
    args_clean = args.strip()
    is_letters = False
    is_numbers = False

    # --- 1. Check if input is letters ---
    if re.fullmatch(r"[A-Za-z]+", args_clean.replace(" ", "")):
        is_letters = True
        letters_only = args_clean.replace(" ", "").upper()
        emoji_output = " ".join(LETTER_EMOJI_MAP.get(ch, f"**{ch}**") for ch in letters_only)
        await ctx.send(f">{emoji_output}<")

    # --- 2. Check if input is numbers ---
    else:
        try:
            num_list = [int(x) for x in args_clean.split()]
            if len(num_list) >= 3:
                is_numbers = True
                *selection_nums, target = num_list
                
                valid_set = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 25, 50, 75, 100}
                if not all(n in valid_set for n in selection_nums):
                    await ctx.send("⚠️ Only valid Countdown numbers allowed in selection.")
                    return

                # Display logic (reversing for visual style as per your snippet)
                disp_selection = list(reversed(selection_nums))
                selection_emojis = " ".join(NUMBER_EMOJI_MAP.get(n, str(n)) for n in disp_selection)
                target_emojis = encode_target_digits(target)

                await ctx.send(
                    f":dart:--->{target_emojis}<---:dart:\n"
                    f"|-{selection_emojis}-|"
                )
            else:
                await ctx.send("⚠️ Please provide at least 3 numbers (selection + target).")
                return
        except ValueError:
            await ctx.send("⚠️ Please provide either letters (A–Z) or numbers separated by spaces.")
            return

    # --- 3. The 40-Second Delay ---
    await asyncio.sleep(40)

    # --- 4. Auto-invoke the solvers ---
    if is_letters:
        # We pass the cleaned letters to the existing maxes command
        # bot.get_command('maxes') finds your @bot.command(name="maxes")
        await ctx.invoke(bot.get_command('maxes'), selection=args_clean.replace(" ", ""))
    
    elif is_numbers:
        # We pass the original number string to the existing solve command
        await ctx.invoke(bot.get_command('solve'), input_text=args_clean)


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

# def regional_indicator(word):
#     emoji_letters = []
#     for ch in word.lower():
#         if 'a' <= ch <= 'z':
#             emoji_letters.append(f":regional_indicator_{ch}:")
#         else:
#             emoji_letters.append(ch)
#     return " ".join(emoji_letters)

def encode_letters(text):
    out = []
    for ch in text.upper():
        out.append(LETTER_EMOJI_MAP.get(ch, ch))
    return " ".join(out)

def encode_number_selection(n):
    return NUMBER_EMOJI_MAP.get(n, str(n))

def encode_target_digits(n):
    return " ".join(NUMBER_EMOJI_MAP[d] for d in str(n))

# === Random message pools ===
CONGRATS_MESSAGES = [
    "🎉 That's correct, {user}!",
    "👏 Nice work, {user}!",
    "🔥 You nailed it, {user}!",
    "🥳 Brilliant, {user}!",
    "✅ Great stuff, {user}!",
    "⚡ Speedy, {user}!",
    "🏆 You got it first, {user}!",
    "🧮 Racking up the points, {user}!",
    "💡 Quick thinking, {user}!",
    "👀 What a spot, {user}!",
]

SCRAMBLE_MESSAGES = [
    "Next conundrum: **{scrambled}**",
    "Try this one: **{scrambled}**",
    "Let's see if you can get this! **{scrambled}**",
    "Here's your next conundrum: **{scrambled}**",
    "A new conundrum awaits: **{scrambled}**",
    "Can you solve this conundrum? **{scrambled}**",
    "Here's a tricky one: **{scrambled}**",
    "Please reveal today's conundrum: **{scrambled}**",
    "Fingers on buzzers: **{scrambled}**",
    "Quiet please, for the conundrum: **{scrambled}**",
]

# === Active puzzles per channel/thread ===
current = {} # conundrums
current_numbers = {}  # for the Numbers game
current_letters = {}  # for the Letters game
locks = {}              # for conundrum channels
numbers_locks = {}      # for numbers channels
letters_locks = {}      # for letters channels

# === Leaderboard storage ===
SCORES_FILE = "scores.json"
try:
    with open(SCORES_FILE, "r", encoding="utf-8") as f:
        scores = json.load(f)
except FileNotFoundError:
    scores = {}

# === Bot events ===
async def new_puzzle(channel):
    word = random.choice(WORDS)
    scrambled_word = scramble(word)
    current[channel.id] = word
    scramble_emoji = encode_letters(scrambled_word)
    msg_template = random.choice(SCRAMBLE_MESSAGES)
    formatted_message = msg_template.format(scrambled=f"\n>{scramble_emoji}<")
    await channel.send(formatted_message)

async def safe_react(message, emoji):
    try:
        await message.add_reaction(emoji)
    except Exception:
        pass

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
    test_letters_channel = bot.get_channel(TEST_LETTERS_CHANNEL_ID)

    if test_conundrum_channel:
        await new_puzzle(test_conundrum_channel)
    if test_numbers_channel:
        await new_numbers_round(test_numbers_channel)
    if test_letters_channel:
        await new_letters_round(test_letters_channel)

    await ctx.send("✅ Test quizzes started in #test_conundrums and #test_numbers and #test_letters.")


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

    # Stop test letters
    if TEST_LETTERS_CHANNEL_ID in current_letters:
        del current_letters[TEST_LETTERS_CHANNEL_ID]
        ch = bot.get_channel(TEST_LETTERS_CHANNEL_ID)
        if ch:
            await ch.send("🛑 Test Letters quiz stopped.")

    await ctx.send("✅ Test quizzes stopped in #test_conundrums and #test_numbers and #test_letters.")


@bot.command(name="start_bots")
@commands.has_permissions(manage_messages=True)
async def start_bots(ctx):
    """Start all bots (conundrums + numbers + letters) across all channels from #test_general."""
    if ctx.channel.id != TEST_GENERAL_CHANNEL_ID:
        await ctx.send("⚠️ This command can't be used in this channel.")
        return

    # All quiz channels (main + test)
    all_channels = [
        bot.get_channel(CONUNDRUM_CHANNEL_ID),
        bot.get_channel(TEST_CONUNDRUMS_CHANNEL_ID),
        bot.get_channel(NUMBERS_CHANNEL_ID),
        bot.get_channel(TEST_NUMBERS_CHANNEL_ID),
        bot.get_channel(LETTERS_CHANNEL_ID),
        bot.get_channel(TEST_LETTERS_CHANNEL_ID),
    ]

    for ch in all_channels:
        if not ch:
            continue

        # 🧩 Conundrum Channels
        if ch.id in [CONUNDRUM_CHANNEL_ID, TEST_CONUNDRUMS_CHANNEL_ID]:
            await new_puzzle(ch)
            await ch.send("🧩 Conundrum quiz started! Reply with your answers below.")

        # 🔢 Numbers Channels
        elif ch.id in [NUMBERS_CHANNEL_ID, TEST_NUMBERS_CHANNEL_ID]:
            await new_numbers_round(ch)
            await ch.send("🔢 Numbers quiz started! Solve the target!")

        # 🔤 Letters Channels
        elif ch.id in [LETTERS_CHANNEL_ID, TEST_LETTERS_CHANNEL_ID]:
            await new_letters_round(ch)
            await ch.send("🔤 Letters quiz started! Type the longest word!")

    await ctx.send("✅ All bots (Conundrum, Numbers, Letters) started in all quiz channels.")

@bot.command(name="stop_bots")
@commands.has_permissions(manage_messages=True)
async def stop_bots(ctx):
    """Stop all bots (conundrums + numbers + letters) across all channels from #test_general."""
    if ctx.channel.id != TEST_GENERAL_CHANNEL_ID:
        await ctx.send("⚠️ This command can't be used in this channel.")
        return

    # Stop all active rounds
    for cid in list(current.keys()):
        del current[cid]
    for cid in list(current_numbers.keys()):
        del current_numbers[cid]
    for cid in list(current_letters.keys()):
        del current_letters[cid]

    # Notify all channels
    for ch_id in [
        CONUNDRUM_CHANNEL_ID, TEST_CONUNDRUMS_CHANNEL_ID,
        NUMBERS_CHANNEL_ID, TEST_NUMBERS_CHANNEL_ID,
        LETTERS_CHANNEL_ID, TEST_LETTERS_CHANNEL_ID,
    ]:
        ch = bot.get_channel(ch_id)
        if ch:
            await ch.send("🛑 Quiz has been temporarily stopped.")

    await ctx.send("✅ All bots (Conundrum, Numbers, Letters) stopped across all quiz channels.")


@bot.command(name="points", aliases=["leaderboard", "score", "scores"])
async def leaderboard(ctx):
    """Show top solvers for either Conundrum or Numbers rounds (works in test & main channels)."""
    if not scores:
        await ctx.send("No scores yet!")
        return

    channel_id = ctx.channel.id

    # Determine which leaderboard to show
    if channel_id in [CONUNDRUM_CHANNEL_ID, TEST_CONUNDRUMS_CHANNEL_ID]:
        key = "con_score"
        title = "🏆 Conundrum Leaderboard"
    elif channel_id in [NUMBERS_CHANNEL_ID, TEST_NUMBERS_CHANNEL_ID]:
        key = "num_score"
        title = "🔢 Numbers Leaderboard"
    elif channel_id in [LETTERS_CHANNEL_ID, TEST_LETTERS_CHANNEL_ID]:
        key = "let_score"
        title = "🔤 Countdown Letters Leaderboard"
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
        return NUMBER_EMOJI_MAP.get(num, str(num))

    def encode_target_digits(n):
        return " ".join(NUMBER_EMOJI_MAP[d] for d in str(n))

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

            selection_emojis = " ".join(encode_number_selection(n) for n in selection)
            target_emojis = encode_target_digits(target)

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

# === Letters Game (letters-bot channel only) ===
cons = {
    'B':2,'C':3,'D':6,'F':2,'G':4,'H':2,'J':1,'K':1,'L':5,'M':4,'N':8,
    'P':4,'Q':1,'R':9,'S':9,'T':9,'V':2,'W':2,'X':1,'Y':1,'Z':1
}
vows = {'A':15,'E':20,'I':13,'O':13,'U':7}

def draw_letters():
    n_vowels = random.choice([3, 4, 5])
    n_cons = 9 - n_vowels

    def make_pool(deck):
        # Expand frequency map into a list of individual cards
        return [ltr for ltr, freq in deck.items() for _ in range(freq)]

    def draw_from_deck(pool, count):
        chosen = []
        prev = None

        for _ in range(count):
            if not pool:
                break  # safety guard (shouldn't happen with normal frequencies)

            # Shuffle and take the top card
            random.shuffle(pool)
            pick = pool.pop(0)

            # If it's the same as previous, put it back and reshuffle, then draw again
            if pick == prev:
                pool.append(pick)   # put it back
                random.shuffle(pool)
                # draw again (this will remove whatever we draw)
                pick = pool.pop(0)
                # If this second draw is still equal to prev, we accept it (it is removed already).
                # If it's different, we accept the different one (also removed).
                # Either way, the chosen card has been removed from the pool.
            # Otherwise (pick != prev) we already removed it so accept it.

            chosen.append(pick)
            prev = pick

        return chosen

    vowel_pool = make_pool(vows)
    cons_pool = make_pool(cons)

    vowels = draw_from_deck(vowel_pool, n_vowels)
    consonants = draw_from_deck(cons_pool, n_cons)

    selection = vowels + consonants
    random.shuffle(selection)
    return selection

async def new_letters_round(channel, max_retries=3):
    """Generate and post a random letters puzzle asynchronously."""
    for attempt in range(1, max_retries + 1):
        selection = draw_letters()
        selection_str = "".join(selection)
        user_identifier = urllib.parse.quote("lettersbot")
        url = f"https://focaltools.azurewebsites.net/api/getmaxes/{selection_str}?ip={user_identifier}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response.raise_for_status()
                    text = await response.text()
                    words = json.loads(text)

            if not words:
                await channel.send(f"⚠️ No valid words found for `{selection_str}` (attempt {attempt}/{max_retries})")
                continue  # try again

            current_letters[channel.id] = {
                "selection": selection_str,
                "maxes": [w.upper() for w in words],
            }

            emoji_output = encode_letters(selection_str)
            await channel.send(f"Find the longest word from this letters selection:\n>{emoji_output}<")
            return  # success, stop retrying

        except asyncio.TimeoutError:
            await channel.send(f"⏳ Timeout fetching maxes for `{selection_str}` (attempt {attempt}/{max_retries})")

        except aiohttp.ClientError as e:
            await channel.send(f"🌐 Network error fetching maxes: `{e}` (attempt {attempt}/{max_retries})")

        except Exception as e:
            await channel.send(f"❌ Unexpected error fetching maxes: `{e}` (attempt {attempt}/{max_retries})")

        await asyncio.sleep(2)  # small delay before retry

    await channel.send("❌ Could not generate a valid letters round after several attempts.")
    
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
            if guess.lower() in ["give up", "giveup", "skip", "next"]:
                sol = current_numbers[cid]["solution"]
                sel = current_numbers[cid]["selection"]
                tgt = current_numbers[cid]["target"]
                selection_param = "-".join(str(n) for n in sel)
                url = f"https://greem.co.uk/quantumtombola/?sel={urllib.parse.quote(selection_param)}&target={urllib.parse.quote(str(tgt))}"
                await message.channel.send(
                    f"💡 A possible solution is: `{sol}`\nSee all solutions in Quantum Tombola:\n<{url}>"
                )
                await new_numbers_round(message.channel)
                return

            selection = current_numbers[cid]["selection"]
            target = current_numbers[cid]["target"]

            # 🟡 "Add" shorthand — e.g. "add them up"
            if guess.lower().startswith("add"):
                guess = "+".join(str(n) for n in selection)

            # 🟡 "Multiply"/"Times" shorthand — e.g. "multiply them" or "times them together"
            elif guess.lower().startswith(("multiply", "times")):
                guess = "x".join(str(n) for n in selection)

            # Otherwise, replace shorthand letters everywhere
            else:
                shorthand_map = {"h": "100", "s": "75", "f": "50", "t": "25"}
                for key, val in shorthand_map.items():
                    guess = re.sub(key, val, guess, flags=re.IGNORECASE)

            # ✅ Normalize before evaluation and for display
            normalized_guess = normalize_expression(guess)
            # Evaluate the user’s attempt
            result = parse_numbers_solution(normalized_guess, selection)
            if result is False:
                return  # ignore invalid attempts

            # Ensure per-channel lock exists
            numbers_locks.setdefault(cid, asyncio.Lock())


            # Capture data for use outside the lock

            is_correct = False
            winner_name = None
            winner_id = None
            chosen_congrats = None
            chosen_guess = None

            async with numbers_locks[cid]:
                if cid not in current_numbers:
                    return  # already solved

                if result == target:

                    is_correct = True
                    winner_id = str(message.author.id)
                    winner_name = message.author.display_name

                    existing_data = scores.get(winner_id, {})
                    con_score = existing_data.get("con_score", 0)
                    num_score = existing_data.get("num_score", 0)
                    let_score = existing_data.get("let_score", 0)

                    # 🧮 Check for "no large numbers used" condition
                    large_numbers = {25, 50, 75, 100}
                    selection_has_large = any(n in large_numbers for n in selection)

                    # Normalize expression before checking which numbers were used
                    used_large = any(str(n) in normalized_guess for n in large_numbers)

                    # 🐱 LNAFP bonus if selection had large numbers but user didn’t use any
                    cat_bonus = selection_has_large and not used_large

                    if cat_bonus:
                        num_score += 2
                        await safe_react(message, "<:LNAFP:1437476304990638162>")
                        await message.channel.send("<:LNAFP:1437476304990638162> Double points!")
                    else:
                        num_score += 1

                    # Save updated score
                    scores[winner_id] = {
                        "name": winner_name,
                        "con_score": con_score,
                        "num_score": num_score,
                        "let_score": let_score,
                    }

                    chosen_congrats = random.choice(CONGRATS_MESSAGES).format(user=winner_name)
                    chosen_guess = normalized_guess  # display normalized version
                    del current_numbers[cid]

            # Outside the lock: save file, announce winner, start new round
            if is_correct:
                with open(SCORES_FILE, "w", encoding="utf-8") as f:
                    json.dump(scores, f, indent=2)

                await message.channel.send(f"{chosen_congrats}\n> `{chosen_guess}` = **{target}**")
                await new_numbers_round(message.channel)
                return

    # --- CONUNDRUM CHANNELS (main + test) ---
    elif message.channel.id in [CONUNDRUM_CHANNEL_ID, TEST_CONUNDRUMS_CHANNEL_ID]:
        cid = message.channel.id
        if cid in current and not message.content.startswith("!"):
            guess = message.content.strip().replace("?", "").lower()
    
            if guess.lower() == "hint":
                answer = current[cid]
                scrambled_view = encode_letters(scramble(answer))
            
                first, last = answer[0], answer[-1]
                middle_len = len(answer) - 2
                blanks = " ".join("⏹️" for _ in range(middle_len))
            
                hint_display = f"{encode_letters(first)} {blanks} {encode_letters(last)}"
            
                await message.channel.send(f"💡 Here's a hint:\n>{scrambled_view}<\n>{hint_display}<")
                return
    
            # 🧩 Handle "give up" or similar
            if guess in ["give up", "giveup", "skip", "next"]:
                answer = current[cid]
                await message.channel.send(f"💡 The answer is **{answer}**.")
                await new_puzzle(message.channel)
                return
    
            # ensure lock exists
            locks.setdefault(cid, asyncio.Lock())
    
            # captureables for after-lock actions
            is_correct = False
            winner_id = None
            winner_name = None
            chosen_congrats = None
            answer_text = None
    
            async with locks[cid]:
                if cid not in current:
                    return  # already solved
    
                if guess == current[cid].lower():
                    is_correct = True
                    winner_id = str(message.author.id)
                    winner_name = message.author.display_name
    
                    existing_data = scores.get(winner_id, {})
                    con_score = existing_data.get("con_score", 0) + 1
                    num_score = existing_data.get("num_score", 0)
                    let_score = existing_data.get("let_score", 0)
    
                    scores[winner_id] = {
                        "name": winner_name,
                        "con_score": con_score,
                        "num_score": num_score,
                        "let_score": let_score,
                    }
    
                    chosen_congrats = random.choice(CONGRATS_MESSAGES).format(user=winner_name)
                    answer_text = current[cid]
                    del current[cid]
    
            # outside lock: persist + notify + new puzzle
            if is_correct:
                with open(SCORES_FILE, "w", encoding="utf-8") as f:
                    json.dump(scores, f, indent=2)
    
                await message.channel.send(f"{chosen_congrats} The answer is **{answer_text}**")
                await new_puzzle(message.channel)
                return

    # --- LETTERS CHANNELS (main + test) ---
    elif message.channel.id in [LETTERS_CHANNEL_ID, TEST_LETTERS_CHANNEL_ID]:
        cid = message.channel.id
    
        # Do not consume commands
        if message.content.startswith("!"):
            await bot.process_commands(message)
            return
    
        # If no active round, ignore but still allow commands in channel
        if cid not in current_letters:
            await bot.process_commands(message)
            return
    
        letters_locks.setdefault(cid, asyncio.Lock())
    
        async with letters_locks[cid]:
    
            # Round may have ended while waiting for lock
            if cid not in current_letters:
                await bot.process_commands(message)
                return
    
            round_data = current_letters[cid]
            selection = round_data["selection"]
            maxes = round_data["maxes"]
    
            guess = message.content.strip().upper()
    
            # give up
            if guess.lower() in ["give up", "giveup", "skip", "next"]:
                formatted = ", ".join(f"**{w}**" for w in sorted(maxes))
                del current_letters[cid]
                post_action = ("giveup", formatted)
    
            # hint
            elif guess.lower() == "hint":
                if not maxes:
                    post_action = ("nomaxes", None)
                else:
                    word = random.choice(maxes)
                    first, last = word[0], word[-1]
                    blanks = " ".join("⏹️" for _ in range(len(word) - 2))
                    sel_display = encode_letters(selection)
                    hint_display = f"{encode_letters(first)} {blanks} {encode_letters(last)}"
                    post_action = ("hint", (sel_display, hint_display))

            # shuffle
            elif guess.lower() in ["shuffle", "swap"]:
                # Convert string to list, shuffle, and join back
                s_list = list(selection)
                random.shuffle(s_list)
                new_selection = "".join(s_list)
                
                # Update the state so the shuffle persists for future prints
                current_letters[cid]["selection"] = new_selection
                
                # Reuse the print format
                sel_display = encode_letters(new_selection)
                post_action = ("print", sel_display)

            # print current puzzle
            elif guess.lower() == "print":
                sel_display = encode_letters(selection)
                post_action = ("print", sel_display)
    
            # correct
            elif guess in maxes:
                winner_id = str(message.author.id)
                winner_name = message.author.display_name
                existing = scores.get(winner_id, {})
                scores[winner_id] = {
                    "name": winner_name,
                    "con_score": existing.get("con_score", 0),
                    "num_score": existing.get("num_score", 0),
                    "let_score": existing.get("let_score", 0) + 1,
                }
                congrats = random.choice(CONGRATS_MESSAGES).format(user=winner_name)
                formatted = ", ".join(f"**{w}**" for w in sorted(maxes))
                del current_letters[cid]
                post_action = ("correct", (congrats, formatted))
    
            # incorrect
            else:
                if " " in guess:
                    post_action = ("ignore", None)
                elif not all(guess.count(ch) <= selection.count(ch) for ch in guess):
                    post_action = ("react", "❓")
                elif guess in history_invalid:
                    post_action = ("react", "🪦")
                else:
                    post_action = ("checkword", guess)
    
        # ----- post-lock actions -----
        action, data = post_action
    
        if action == "giveup":
            await message.channel.send(f"💡 Max words were: {data}")
            await new_letters_round(message.channel)
            await bot.process_commands(message)
            return
    
        if action == "nomaxes":
            await message.channel.send("⚠️ No max words available yet.")
            await bot.process_commands(message)
            return
    
        if action == "hint":
            sel_display, hint_display = data
            await message.channel.send(f"💡 Here's a hint:\n>{sel_display}<\n>{hint_display}<")
            await bot.process_commands(message)
            return

        if action == "shuffle":
            await message.channel.send(f">{data}<")
            await bot.process_commands(message)
            return

        if action == "print":
            await message.channel.send(f">{data}<")
            await bot.process_commands(message)
            return
    
        if action == "correct":
            congrats, formatted = data
            await message.add_reaction("✅")
            with open(SCORES_FILE, "w", encoding="utf-8") as f:
                json.dump(scores, f, indent=2)
            await message.channel.send(f"{congrats} 💡 The maxes were: {formatted}")
            await new_letters_round(message.channel)
            await bot.process_commands(message)
            return
    
        if action == "ignore":
            await bot.process_commands(message)
            return
    
        if action == "react":
            await message.add_reaction(data)
            await bot.process_commands(message)
            return
    
        if action == "checkword":
            guess = data
            user_identifier = urllib.parse.quote("lettersbot")
            url = f"https://focaltools.azurewebsites.net/api/checkword/{guess}?ip={user_identifier}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=10) as resp:
                        result = (await resp.text()).strip().lower()
            except Exception:
                result = "error"
    
            if "true" in result:
                await message.add_reaction("⬆️")
            elif "false" in result:
                await message.add_reaction("❌")
            else:
                await message.add_reaction("⚠️")
    
            await bot.process_commands(message)
            return


    # Always allow commands to process
    await bot.process_commands(message)

@tasks.loop(hours=24)
async def dump_scores_daily():
    """Automatically dump scores every 24 hours."""
    await bot.wait_until_ready()  # ensure bot is logged in
    channel = bot.get_channel(TEST_GENERAL_CHANNEL_ID)
    if channel is None:
        print("⚠️ Test channel not found! Check the ID.")
        return

    # Simulate the command call by finding the command and invoking it
    ctx = await bot.get_context(await channel.send("Auto dumping scores..."))
    command = bot.get_command("dump_scores")
    if command:
        await ctx.invoke(command)
    else:
        await channel.send("⚠️ `!dump_scores` command not found.")

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (id: {bot.user.id})")

    # --- Load invalid history once on startup ---
    global history_invalid
    history_invalid = set()
    try:
        with open("history_invalid.txt", "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if parts:
                    history_invalid.add(parts[0].strip().upper())
        print(f"📜 Loaded {len(history_invalid)} invalid words from history_invalid.txt")
    except FileNotFoundError:
        print("⚠️ history_invalid.txt not found; continuing without it.")

    # --- Start background tasks ---
    if not dump_scores_daily.is_running():
        dump_scores_daily.start()
        print("⏰ Started daily score dump task.")

# === Run bot ===
if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Environment variable DISCORD_BOT_TOKEN is missing.")
    bot.run(token)
