import discord
from discord.ext import commands
import asyncio
import random
import time
from extra import *

intents = discord.Intents.default()
intents.message_content = True

prefix = "u"
symbol = "!"
bot = commands.Bot(case_insensitive=True, command_prefix=commands.when_mentioned_or(f'{prefix}{symbol}', f'{prefix.upper()}{symbol}', prefix, prefix.upper()), intents=discord.Intents.all())
color_list = ["red", "green", "blue", "yellow", "wild"]
action_list = ["reverse", "skip", "draw two", "draw four", ""]

joined = False
uno_id = 1183193664839749732
hand = []
players = {}
players_ = []
direction = 1
prev = 0
table_call = False
act = False

remember_card = ""
remember_length = 0

def reset():
    global joined, hand, players, direction, prev, players_, table_call
    joined = False
    table_call = False
    hand = []
    players = {}
    players_ = []
    direction = 1
    prev = 0

def p_id(content, loc=0):
    return int(content.split(" ")[loc].replace("<@", "").replace(">", ""))

def prev_player(turn, multiplier=1):
    direction_ = direction * multiplier
    turn = players_.index(turn) - direction_
    while turn >= len(players_):
        turn -= len(players_)
    while turn < 0:
        turn += len(players_)
    return players_[turn]

def values(card):
    color = card.split(" ")[0]
    value = " ".join(card.split(" ")[1::])
    return color.lower(), value.lower()

def can_play(card):
    color, value = values(card)
    playables = []
    for c in hand:
        c_color, c_value = values(c)
        if c_color == color or c_value == value or c_color == "wild":
            playables += [c]
    return c

def playable(top, cards=[], exclude=[], fill=True):
    if not cards and fill:
        cards = hand.copy()
    top = top.lower()
    playable = []
    cards_ = cards.copy()
    for card in range(len(cards)):
        cards_[card] = values(cards[card])
    for card in range(len(cards_)):
        if cards_[card][0] not in exclude and cards_[card][1] not in exclude:
            if cards_[card][0] in top or cards_[card][1] in top or cards_[card][0] == "wild" or "wild" in top and "(" not in top:
                playable += [cards[card]]
    return playable

async def play_card(message, card):
    if len(hand) == 2:
        await message.channel.send("uno!")
        await asyncio.sleep(1)
    await message.channel.send(f"uno play {card}")

def colors(cards=[], exclude=[], numbers=False):
    if not cards:
        cards = hand.copy()
    c = {}
    for color in color_list:
        c[color] = 0
    for color in exclude:
        c.pop(color)
    for card in cards:
        color = values(card)[0]
        if color not in exclude:
            c[color] += 1
    highest = sorted(c, key=lambda k: c[k], reverse=True)
    if numbers:
        numbers = []
        for color in highest:
            numbers += [c[color]]
        return highest, numbers
    return highest

def find_color(color, cards=[], exclude=[], fill=True):
    color = color.lower()
    if not cards and fill:
        cards = hand.copy()
    for card in cards:
        color_, value_ = values(card)
        if color_ == color and color_ not in exclude and value_ not in exclude:
            return card
    return False

def locate_cards(cards=[], color_wl=[], value_wl=[], color_bl=[], value_bl=[]):
    if not cards:
        cards = hand.copy()
    if not color_wl:
        for color in color_list:
            color_wl += [color]
    if not value_wl:
        for value in range(10):
            value_wl += [value]
        for value in action_list:
            value_wl += [value]
    located = []
    for card in cards:
        color, value = values(card)
        if color in color_wl and value in value_wl and color not in color_bl and value not in value_bl:
            located += [card]
    return located

def combos(top, cards=[]):
    if not cards:
        cards = hand.copy()
    value_wl = action_list.copy()
    value_wl.remove("")
    action_cards = locate_cards(cards=cards.copy(), value_wl=value_wl)
    to_play = [playable(top, cards=action_cards, fill=False)]
    turn = [0]
    combo = [[]]
    depth = 0
    while depth != -1:
        if turn[depth] == len(to_play[depth]):
            if len(combo[-1]):
                last_color = values(combo[-1][-1])[0]
                if last_color == "wild":
                    add_card = playable(combo[-1][-1], cards=cards.copy(), exclude=action_list.copy(), fill=False)
                    if add_card:
                        add_card = add_card[0]
                else:
                    add_card = find_color(last_color, cards=playable(combo[-1][-1], cards=cards.copy(), exclude=action_list.copy(), fill=False), fill=False)
                if not add_card:
                    add_card = find_color("wild", cards=playable(combo[-1][-1], cards=cards.copy(), exclude=value_wl.copy(), fill=False), fill=False)
                combo += [combo[-1][0:-1]]
                if add_card:
                    combo[-2] += [add_card]
            depth -= 1
            continue
        combo[-1] += [to_play[depth][turn[depth]]]
        turn[depth] += 1
        depth += 1
        if depth >= len(to_play):
            to_play += [[]]
            turn += [0]
        next_to_play = action_cards.copy()
        for card in combo[-1]:
            next_to_play.remove(card)
        to_play[depth] = playable(combo[-1][-1], cards=next_to_play, fill=False)
        turn[depth] = 0
    combo = sorted(combo, key=len, reverse=True)
    return combo

def combo_wild4_filter(combo):
    for branch in reversed(range(len(combo.copy()))):
        if "wild draw four" in combo[branch] or "Wild draw four" in combo[branch]:
            combo.pop(branch)
    return combo

def human(key):
    index = random.randint(0, len(extra[key]) - 1)
    return extra[key][index]

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.event
async def on_message(message):
    global joined, hand, players, direction, prev, players_, remember_card, remember_length, act, table_call
    if message.author == bot.user:
        return
    content = message.content.lower()
    authorId = message.author.id
    if 'oli' in content: 
        if "join" in content:
            if not joined:
                await message.channel.send(human("join"))
                await message.channel.send("uno join")
            joined = True
        elif "start" in content:
            await message.channel.send("uno start")
        elif "quit" in content:
            await message.channel.send("uno quit")
    if authorId == uno_id:
        if "your deck" in content:
            contents = content.split("\n")
            if len(contents) > 1:
                hand = contents[1].split(" | ")
            else:
                reset()
                return
        if message.embeds:
            time.sleep(1)
            title = message.embeds[0].title
            content = message.embeds[0].description
            turn = p_id(content.split("\n")[-1], loc=-1)
            card = content.split("\n")[1].replace("*", "").lower()
            picking = "wild" in card and "(" not in card
            if not title and not picking:
                if not players:
                    if not table_call:
                        table_call = True
                        prev = turn
                        await message.channel.send("uno table")
                else:
                    if not act:
                        if "draw two" in card:
                            players[prev_player(turn)]["cards"] += 2
                        if "draw four" in card:
                            players[prev_player(turn)]["cards"] += 4
                        if "reverse" in card:
                            direction *= -1
                    act = False
                    if not prev:
                        if "draw two" in card:
                            players[prev_player(turn)]["cards"] += 2
                    if prev in players:
                        if players[prev]["clear"] == 1:
                            players[prev]["clear"] = 2
                        elif players[prev]["clear"] == 2:
                            players[prev]["clear"] = 0
                        players[prev]["cards"] -= 1
                        if players[prev]["cards"] <= 0:
                            return
                        if players[prev]["cards"] == 1 and players[prev]["clear"] == 0 and prev != bot.application_id:
                            await message.channel.send("uno callout")
                        last_color = values(card)[0]
                        if last_color != "wild":
                            if players[prev]["color"][0] != last_color:
                                players[prev]["color"] = [last_color, 0]
                            else:
                                players[prev]["color"][1] += 1
                        else:
                            last_color = card[card.find("(") + 1:card.find(")")]
                            players[prev]["color"] = [last_color, 0]
                    prev = turn
                if random.randint(0, 10) == 0:
                    await message.channel.send(human("trivia"))
            if turn == bot.application_id:
                to_play = playable(card)
                remember_card = card
                remember_length = len(hand)
                if not players:
                    to_play = playable(card, exclude=["wild"])
                if picking:
                    most = colors(exclude=["wild"])
                    desired = most[0]
                    if players:
                        next_player = prev_player(bot.application_id, multiplier=-1)
                        card_amount = players[next_player]["cards"]
                        if card_amount <= 3 and card_amount < len(hand) and players[next_player]["color"][1] >= 2:
                            next_desired = players[next_player]["color"][0]
                            if desired == next_desired:
                                desired = most[1]
                    await message.channel.send(f"uno color {desired}")
                    return
                if not to_play:
                    await message.channel.send("uno pickup")
                    return
                if players:
                    next_player = prev_player(turn, multiplier=-1)
                    card_amount = players[next_player]["cards"]
                    if card_amount <= 3 and card_amount < len(hand):
                        if "Wild draw four" in hand:
                            await play_card(message, "Wild draw four")
                            return
                        action_cards = locate_cards(cards=to_play, value_wl=action_list.copy())
                        if action_cards:
                            await play_card(message, action_cards[0])
                            return
                        elif "Wild" in hand:
                            if players[next_player]["color"][1] >= 2:
                                await play_card(message, "Wild")
                                return
                        elif card_amount == 1:
                            await message.channel.send("uno pickup")
                            return
                combo = combos(card)
                if combo[0] and len(players) == 2:
                    combo_ = combo_wild4_filter(combo.copy())
                    if len(combo[0]) == len(hand):
                        await play_card(message, combo[0][0])
                        return
                    elif len(hand) - len(combo_[0]) <= 3 and len(combo_[0]) or len(combo_[0]) > 2:
                        await play_card(message, combo_[0][0])
                        return
                most, most_n = colors(cards=to_play, exclude=["wild"], numbers=True)
                if not most_n[0]:
                    most[0] = "wild"
                playing_card = find_color(most[0], cards=to_play, exclude=["draw four"])
                if not playing_card:
                    playing_card = find_color(most[0], cards=to_play)
                await play_card(message, playing_card)
        if "has won" in content:
            if content and p_id(content) != bot.application_id:
                await message.channel.send(human("loss"))
                reset()
                return
            else:
                await message.channel.send(human("win"))
                reset()
                return
        if "clearance to put their second to last card down" in content:
            playerId = p_id(content)
            if playerId in players:
                players[playerId]["clear"] = 1
        if "automatically wins" in content or "too long" in content:
            reset()
            return
        if "quit the game" in content or "removed for inactivity" in content:
            playerId = p_id(content)
            if playerId in players:
                players.pop(playerId)
                players_.remove(playerId)
        drew = "picked up a card from the draw pile" in content
        skipped = "skipped their turn" in content
        if drew or skipped:
            if skipped:
                act = True
            playerId = p_id(content)
            if playerId in players:
                players[playerId]["cards"] += 1
            if drew and playerId == bot.application_id:
                to_play = playable(remember_card, cards=hand[-1::])
                if to_play:
                    await play_card(message, to_play[0])
                else:
                    await message.channel.send("uno skip")
        if "out for forgetting to say uno" in content and not "tried to" in content:
            playerId = p_id(content, loc=2)
            if playerId in players:
                players[playerId]["cards"] += 2
        if "players present" in content:
            players_ = []
            for player in content.split("\n")[1::]:
                playerId, cards = player.split(" | ")
                playerId = int(playerId.replace("<@", "").replace(">", "").replace(" ", ""))
                cards = int(cards.split(" ")[0].replace(" ", ""))
                players[playerId] = {}
                players[playerId]["cards"] = cards
                if "clear" not in players[playerId]:
                    players[playerId]["clear"] = 0
                if "color" not in players[playerId]:
                    players[playerId]["color"] = ["", 0]
                players_ += [playerId]

bot.run("<OLIVER BOT TOKEN>")
