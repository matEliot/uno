import discord
from discord.ext import commands
import random
import asyncio
import time

intents = discord.Intents.default()
intents.message_content = True

prefix = "uno"
bot = commands.Bot(case_insensitive=True, command_prefix=commands.when_mentioned_or(prefix, prefix.upper, prefix.capitalize()), intents=discord.Intents.all())

games = {}
colors = {"red": 0xff0000, "green": 0x00ff00, "blue": 0x0000ff, "yellow": 0xffff00}
extended_colors = {**colors, "wild": 0x000000}
color_translation = {"r": "Red", "g": "Green", "b": "Blue", "y": "Yellow", "w": "Wild"}
values = ["skip", "draw two", "reverse"]
for i in range(10):
    values += [str(i)]

def create_deck():
    deck = []
    for color in colors:
        for value in values:
            amount = 2
            if value != 0:
                amount = 1
            deck += [f"{color.capitalize()} {value}"] * amount
    deck += ["Wild"] * 4
    deck += ["Wild draw four"] * 4
    random.shuffle(deck)
    return deck

async def grab_card(channelId, userId, amount=1):
    global games
    for i in range(amount):
        if len(games[channelId]["deck"]) <= 0:
            games[channelId]["deck"] = games[channelId]["pile"][0:-1]
            games[channelId]["pile"] = games[channelId]["pile"][-1::]
            random.shuffle(games[channelId]["deck"])
            await bot.get_channel(channelId).send("The discard pile has been shuffled and and turned into a draw pile.")
        if len(games[channelId]["deck"]) <= 0:
            game_end(channelId)
            await bot.get_channel(channelId).send("Game ended with no winners.")
            return False
        games[channelId][userId] += [games[channelId]["deck"][0]]
        games[channelId]["deck"].pop(0)

async def put_card(channelId, card):
    global games
    details = card.split(" ")
    color = details[0]
    value = ""
    if len(details) > 1:
        value = " ".join(details[1::])
    pile_color, pile_value = color, value
    if len(games[channelId]["pile"]):
        pile_details = games[channelId]["pile"][-1].split(" ")
        pile_color = pile_details[0]
        if len(pile_details) > 1:
            pile_value = " ".join(pile_details[1::])
    if color.capitalize() != "Wild":
        if pile_color.capitalize() != "Wild":
            if color != pile_color and value != pile_value:
                return False
        else:
            if games[channelId]["wild state"] != color.lower():
                return False
    games[channelId]["pile"] += [card]
    match value:
        case "draw two":
            await grab_card(channelId, games[channelId]["players"][await add_to_turn(channelId)], amount=2)
            games[channelId]["direction"] *= 2
        case "skip":
            games[channelId]["direction"] *= 2
        case "reverse":
            if len(games[channelId]["players"]) > 2:
                games[channelId]["direction"] *= -1
            else:
                games[channelId]["direction"] *= 2
        case "draw four":
            games[channelId]["wild state"] = "-"
            await bot.get_channel(channelId).send(f'Pick a color (uno color <color>).')
            await grab_card(channelId, games[channelId]["players"][await add_to_turn(channelId)], amount=4)
            games[channelId]["direction"] *= 2
        case "":
            games[channelId]["wild state"] = "-"
            await bot.get_channel(channelId).send(f'Pick a color (uno color <color>).')
    return True

def hand_message(channelId, userId):
    return f'Your deck:\n' + " | ".join(games[channelId][userId])
async def dm_deck(channelId, userId, dm=""):
    global games
    try:
        user = await bot.fetch_user(userId)
        if not dm:
            if userId in games[channelId]["channels"]:
                dm = games[channelId]["channels"][userId]
            elif not user.bot:
                dm = await user.create_dm()
            else:
                return
        if userId not in games[channelId]["channels"]:
            games[channelId]["channels"][userId] = dm
        if userId in games[channelId]:
            await dm.send(hand_message(channelId, userId))
    except:
        pass

async def add_user(channelId, authorId, mention=True):
    global games
    channel = bot.get_channel(channelId)
    if len(games[channelId]["players"]) >= 10:
        await channel.send(f"Game is already at full capacity.")
        return
    if games[channelId]["active"]:
        await channel.send(f"Game has already started.")
        return
    if authorId in games[channelId]:
        await channel.send(f"You're already in the game, <@{authorId}>.")
        return
    games[channelId][authorId] = []
    games[channelId]["players"] += [authorId]
    if mention:
        await channel.send(f"<@{authorId}> has joined the game.")

async def add_to_turn(channelId, change=False):
    global games
    result = games[channelId]["turn"] + games[channelId]["direction"]
    if result <= -1:
        result = len(games[channelId]["players"]) + result
    elif result >= len(games[channelId]["players"]):
        result = result - len(games[channelId]["players"])
    if change:
        if abs(games[channelId]["direction"]) == 2:
            games[channelId]["direction"] = int(games[channelId]["direction"] / 2)
        games[channelId]["turn"] = result
        userId = games[channelId]["players"][result]
        await dm_deck(channelId, userId, dm=games[channelId]["channels"][userId])
    return result

class Hand(discord.ui.View):
    def __init__(self):
        super().__init__()
    @discord.ui.button(label="Hand", style=discord.ButtonStyle.primary)
    async def button_callback(self, interaction, button):
        channelId = interaction.channel.id
        authorId = interaction.user.id
        if channelId not in games:
            await interaction.response.defer()
            return
        if authorId not in games[channelId]:
            await interaction.response.defer()
            return
        await interaction.response.send_message(hand_message(channelId, authorId), ephemeral=True)

async def display_pile(channelId, title=""):
    global games
    if channelId not in games:
        return
    next_ = games[channelId]["players"][games[channelId]["turn"]]
    color = extended_colors[games[channelId]["pile"][-1].lower().split(" ")[0]]
    extra = ""
    if color == 0x000000:
        if games[channelId]["wild state"] in colors:
            color = colors[games[channelId]["wild state"]]
            extra = f' ({games[channelId]["wild state"]})'
    embed = discord.Embed(title=title, description=f'Card on top of the pile:\n**{games[channelId]["pile"][-1]}{extra}**\n\nNext to play: <@{next_}>', color=color)
    view = Hand()
    await bot.get_channel(channelId).send("", embed=embed, view=view)

async def end_game(channelId):
    global games
    for user_id, channel in games[channelId]["channels"].items():
        if channel and not isinstance(channel, discord.DMChannel):
            try:
                await channel.delete()
            except Exception as e:
                print(f"Can't delete <#{channel.id}> bruh")
    games.pop(channelId)

async def remove_player(channelId, authorId, left=True):
    global games
    channel = bot.get_channel(channelId)
    games[channelId]["deck"] += games[channelId][authorId]
    random.shuffle(games[channelId]["deck"])
    games[channelId].pop(authorId)
    removeId = games[channelId]["players"].index(authorId)
    await add_to_turn(channelId, change=True)
    games[channelId]["players"].remove(authorId)
    if games[channelId]["turn"] > removeId:
        games[channelId]["turn"] -= 1
    if left:
        await channel.send(f'<@{authorId}> quit the game.')
    if len(games[channelId]["players"]) <= 0:
        await channel.send(f'Game aborted.')
        return
    elif len(games[channelId]["players"]) == 1 and games[channelId]["active"]:
        await channel.send(f'<@{games[channelId]["players"][0]}> automatically wins.')
        await end_game(channelId)
        return
    elif games[channelId]["active"]:
        await display_pile(channelId, title="Previous move")
    if games[channelId]["leader"] == authorId and not games[channelId]["active"]:
        games[channelId]["leader"] = games[channelId]["players"][0]
        await channel.send(f'<@{games[channelId]["leader"]}> has become the new leader.')

async def expire_check():
    global games
    while True:
        try:
            await asyncio.sleep(2)
            for channelId in games.copy():
                if time.time() - games[channelId]["time"] >= 180:
                    channel = bot.get_channel(channelId)
                    if not games[channelId]["active"]:
                        await channel.send("Game took too long to start.")
                        await end_game(channelId)
                        continue
                    player = games[channelId]["players"][games[channelId]["turn"]]
                    await channel.send(f"<@{player}> removed for inactivity.")
                    games[channelId]["time"] = time.time()
                    await remove_player(channelId, player, left=False)
        except Exception as e:
            pass

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    asyncio.run_coroutine_threadsafe(expire_check(), bot.loop)

@bot.event
async def on_message(message):
    global games
    authorId = message.author.id
    if message.author == bot.user:
        return
    if 'uno' in message.content.lower()[0:3]:
        msg = message.content.lower().split(" ")
        channelId = message.channel.id
        server = message.guild
        channel = bot.get_channel(channelId)
        if msg[0] == "uno!":
            if channelId not in games:
                return
            if authorId not in games[channelId]:
                return
            deckLen = len(games[channelId][authorId])
            if deckLen == 1:
                if games[channelId]["uno state"] == ["-", authorId]:
                    games[channelId]["uno state"] = ["", 0]
                    await channel.send(f"Phew! <@{authorId}> has cleared their name after forgetting to the move prior.")
            elif deckLen == 2:
                if authorId != games[channelId]["players"][games[channelId]["turn"]]:
                    return
                if games[channelId]["uno state"] != ["+", authorId]:
                    games[channelId]["uno state"] = ["+", authorId]
                    await channel.send(f"<@{authorId}> now has clearance to put their second to last card down.")
        if len(msg) == 1:
            return
        match msg[1]:
            case "help":
                await channel.send('UNO JOIN - Join / Create a game in this channel.' +
                                                               '\nUNO START - Start the game once everyone is present.' +
                                                               '\nUNO QUIT - Quit the game.' +
                                                               '\nUNO TABLE - Show everyone playing.' +
                                                               '\nUNO PLAY <color> <value> - Play a card.' +
                                                               '\nUNO COLOR <color> - Pick a color after using a wild card.' +
                                                               '\nUNO PICKUP - Pick up a card.' +
                                                               "\nUNO SKIP - Pass after picking up a card." +
                                                               '\nUNO CALLOUT - Call out a player for not saying Uno!' +
                                                               '\nUNO LAST - Replay the last move.' +
                                                               "\nUNO! - Use when you're putting down your second to last card.")
            case "join" | "j":
                if channelId not in games:
                    games[channelId] = {"deck": create_deck(), "pile": [], "active": False, "leader": authorId, "players": [], "turn": -1,
                                        "direction": 1, "time": time.time(), "channels": {}, "wild state": "", "pick state": "",
                                        "uno state": ["", 0], "penalty state": False}
                    await add_user(channelId, authorId, mention=False)
                    await channel.send(f'<@{authorId}> has created a game in this channel.')
                else:
                    await add_user(channelId, authorId)
            case "start" | "st":
                if channelId not in games:
                    await channel.send(f'There is no game in this channel.')
                    return
                if games[channelId]["leader"] != authorId:
                    await channel.send(f"You're not the leader of this game, <@{authorId}>.")
                    return
                if games[channelId]["active"]:
                    await channel.send(f'This game is already active.')
                    return
                if len(games[channelId]["players"]) < 2:
                    await channel.send(f'Not enough players present.')
                    return
                games[channelId]["active"] = True
                for player in games[channelId]["players"]:
                    player_ = await server.fetch_member(player)
                    await grab_card(channelId, player, amount=7)
                    if player_.bot:
                        overwrites = {
                            server.default_role: discord.PermissionOverwrite(read_messages=False),
                            server.me: discord.PermissionOverwrite(read_messages=True),
                            player_: discord.PermissionOverwrite(read_messages=True)
                            }
                        channel_name = f"{player}s deck"
                        channel = discord.utils.get(server.channels, name=channel_name)
                        if not channel:
                            channel = await server.create_text_channel(channel_name, overwrites=overwrites)
                        await dm_deck(channelId, player, dm=channel)
                        continue
                    await dm_deck(channelId, player)
                while True:
                    if games[channelId]["deck"][0] == "Wild draw four":
                        random.shuffle(games[channelId]["deck"])
                    else:
                        await put_card(channelId, games[channelId]["deck"][0])
                        if abs(games[channelId]["direction"]) == 1:
                            games[channelId]["turn"] = 0
                        else:
                            games[channelId]["direction"] = int(games[channelId]["direction"] / 2)
                            games[channelId]["turn"] = 1
                        games[channelId]["deck"].pop(0)
                        break
                await display_pile(channelId)
            case "quit" | "q":
                if channelId not in games:
                    return
                if authorId in games[channelId]:
                    await remove_player(channelId, authorId)
                else:
                    return
            case "table" | "t":
                if channelId not in games:
                    await channel.send(f"There is no game in this channel.")
                    return
                table = "Players present:"
                for player in games[channelId]["players"]:
                    table += f"\n<@{player}> | {len(games[channelId][player])} Card(s)"
                await channel.send(table)
            case "play" | "p":
                if channelId not in games:
                    return
                if authorId not in games[channelId]:
                    return
                if games[channelId]["wild state"] == "-":
                    return
                if authorId != games[channelId]["players"][games[channelId]["turn"]]:
                    return
                if len(msg) >= 3:
                    if msg[2] in color_translation:
                        msg[2] = color_translation[msg[2]]
                    action_translation = {"s": "skip", "r" : "reverse", "+2": "draw two", "+4": "draw four"}
                    if len(msg) > 3:
                        if msg[3] in action_translation:
                            msg[3] = action_translation[msg[3]]
                    card = " ".join(msg[2::]).capitalize()
                    if card in games[channelId][authorId]:
                        if games[channelId]["pick state"]:
                            if games[channelId]["pick state"] != card:
                                return
                        if await put_card(channelId, card):
                            if games[channelId]["wild state"] in colors:
                                games[channelId]["wild state"] = ""
                            games[channelId]["pick state"] = ""
                            games[channelId]["penalty state"] = ""
                            games[channelId][authorId].remove(card)
                            if games[channelId]["wild state"] != "-":
                                await add_to_turn(channelId, change=True)
                            await display_pile(channelId)
                            games[channelId]["time"] = time.time()
                            deckLen = len(games[channelId][authorId])
                            if games[channelId]["uno state"] == ["-", authorId]:
                                games[channelId]["uno state"] = ["", 0]
                            if deckLen == 1:
                                if games[channelId]["uno state"] != ["+", authorId]:
                                    games[channelId]["uno state"] = ["-", authorId]
                                else:
                                    games[channelId]["uno state"] = ["", 0]
                            elif deckLen == 0:
                                await end_game(channelId)
                                await channel.send(f"<@{authorId}> has won by placing their last card.")
                                return
            case "color" | "c":
                if channelId not in games:
                    return
                if authorId not in games[channelId]:
                    return
                if games[channelId]["wild state"] != "-":
                    return
                if authorId != games[channelId]["players"][games[channelId]["turn"]]:
                    return
                if len(msg) >= 3:
                    color = msg[2].lower()
                    if color in color_translation:
                        color = color_translation[color].lower()
                    if color in colors:
                        games[channelId]["wild state"] = color
                        await add_to_turn(channelId, change=True)
                        await display_pile(channelId)
            case "pickup" | "pu":
                if channelId not in games:
                    return
                if authorId not in games[channelId]:
                    return
                if games[channelId]["wild state"] == "-":
                    return
                if authorId != games[channelId]["players"][games[channelId]["turn"]]:
                    return
                if games[channelId]["pick state"]:
                    return
                await grab_card(channelId, authorId)
                games[channelId]["pick state"] = games[channelId][authorId][-1]
                await dm_deck(channelId, authorId)
                await channel.send(f"<@{authorId}> picked up a card from the draw pile.\nYou must now play the card or use 'uno skip'.")
            case "skip" | "s":
                if channelId not in games:
                    return
                if authorId not in games[channelId]:
                    return
                if not games[channelId]["pick state"]:
                    return
                if authorId != games[channelId]["players"][games[channelId]["turn"]]:
                    return
                await add_to_turn(channelId, change=True)
                games[channelId]["time"] = time.time()
                games[channelId]["pick state"] = ""
                await channel.send(f"<@{authorId}> skipped their turn.")
                await display_pile(channelId)
            case "callout" | "co":
                if channelId not in games:
                    return
                if authorId not in games[channelId]:
                    return
                state, userId = games[channelId]["uno state"]
                if state != "-":
                    await channel.send(f"<@{authorId}> tried to call someone out for forgetting to say Uno, but there was no one.")
                    return
                await grab_card(channelId, userId, amount=2)
                await channel.send(f"<@{authorId}> called <@{userId}> out for forgetting to say Uno.\n<@{userId}> has received the penalty of two cards.")
                games[channelId]["uno state"] = ["", 0]
            case "last" | "l":
                await display_pile(channelId, title="Previous move")

bot.run("<MIDDLEGROUND BOT TOKEN HERE>")
