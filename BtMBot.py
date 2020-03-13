#Behind the Masks Discord Bot v0.1.0b
#Copyright (c) 2020 DJVoxel
#Behind the Masks is the intellectual property of VucubCaquix
#All Rights Reserved

import discord
from discord.ext import commands
from discord.ext.commands import bot
import asyncio

from collections import OrderedDict

import random

import datetime
from datetime import timedelta

COMMAND_PREFIX = '/'

BOT_KEY = '<Bot Key>'

bot = commands.Bot(COMMAND_PREFIX)

########## GLOBALS ##########
running = False
players = OrderedDict() #uid:[mask, role:[name, duel, dance, <ability charges>], gifts:[denies, encores, pswitches, GI?, Guess?, reserve], plate:[Poisoned?, Premium?], death]
dead = OrderedDict() #uid:[mask, role, death]

state = {'phase':None, 'round':1}
challenges = OrderedDict() #uid:[dance/duel, uid]
votes = OrderedDict() #uid:[uids of voters]

guild_settings = {} #guild id:{'channel':game channel, 'role': player role}

MAX_PLAYERS = 15
MIN_PLAYERS = 15
ROLES = [
    {'name':'Poisoner', 'duel':7, 'dance':8},
    {'name':'Barbarian', 'duel':14, 'dance':1, 'intimidate':3},
    {'name':'Blackmailer', 'duel':8, 'dance':11},
    {'name':'Blacksmith', 'duel':11, 'dance':2},
    {'name':'Court Jester', 'duel':3, 'dance':7},
    {'name':'Man-at-arms', 'duel':12, 'dance':4},
    {'name':'Monk', 'duel':0, 'dance':0, 'stance':''},
    {'name':'Musician', 'duel':2, 'dance':12},
    {'name':'Peasant', 'duel':9, 'dance':10},
    {'name':'Professor', 'duel':6, 'dance':6},
    {'name':'Royal', 'duel':1, 'dance':14},
    {'name':'Soldier', 'duel':13, 'dance':5},
    {'name':'Sorceror', 'duel':10, 'dance':9},
    {'name':'Student', 'duel':5, 'dance':3},
    {'name':'Thief', 'duel':4, 'dance':13}
    ]

CP_TIMEOUT = 300
VP_TIMEOUT = 300
DP_TIMEOUT = 300

game_info =  discord.Embed(title='The game has not started yet.')

########## INIT ############
@bot.event
async def on_ready():
    print (bot.user.name, 'is ready!')
    print ('Id:', bot.user.id)

########## ERRORS ##########
class NoGameChannel(commands.CheckFailure):
    pass

class NotGameChannel(commands.CheckFailure):
    pass

class GameStateError(commands.CheckFailure):
    pass

class PlayerStateError(commands.CheckFailure):
    pass

class GameSizeError(commands.CheckFailure):
    pass

class PhaseStateError(commands.CheckFailure):
    pass

########## CHECKS ##########
def in_game_channel(ctx):
    try:
        if guild_settings[ctx.guild.id]['channel'] is None:
            raise NoGameChannel
    except:
        raise NoGameChannel
    if ctx.channel != guild_settings[ctx.guild.id]['channel']:
        raise NotGameChannel
    return True

def is_running(ctx):
    if not running:
        raise GameStateError
    return True

def is_not_running(ctx):
    if running:
        raise GameStateError
    return True

def is_player(ctx):
    if ctx.author.id not in players:
        raise PlayerStateError
    return True

def is_not_player(ctx):
    if ctx.author.id in players:
        raise PlayerStateError
    return True

def game_full(ctx):
    if len(players) < MIN_PLAYERS:
        raise GameSizeError
    return True

def game_not_full(ctx):
    if len(players) >= MAX_PLAYERS:
        raise GameSizeError
    return True

def is_CP(ctx):
    if state['phase'] != 'CP':
        raise PhaseStateError
    return True

def is_VP(ctx):
    if state['phase'] != 'VP':
        raise PhaseStateError
    return True

def is_DP(ctx):
    if state['phase'] != 'DP':
        raise PhaseStateError
    return True

########## COMMANDS ##########
@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

#--------- Setup ---------#
@bot.command()
@commands.is_owner()
async def setup(ctx, role_name):
    global guild_settings

    for role in ctx.guild.roles: #Grabs player role if it exists, creates it if it does not.
        if role.name == role_name: 
            player_role = role
    try:       
        if player_role is not None:
            print('Player role {} already exists'.format(role_name))
    except NameError:
        player_role = await ctx.guild.create_role(name=role_name, hoist=True, mentionable=True)

    await ctx.channel.set_permissions(player_role, send_messages=True)
    await ctx.channel.set_permissions(ctx.me.top_role, send_messages=True)

    guild_settings[ctx.guild.id] = {'channel':ctx.channel, 'role':player_role}
    await ctx.send('Setup Complete!')

@setup.error
async def setup_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send('You do not have permission to use this command.')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Missing player role name.')

#--------- Help and Info ---------#
@bot.command()
async def info(ctx):
    await ctx.send(embed=game_info)

#--------- Join and Leave ---------#
@bot.command()
@commands.check(is_not_player)
@commands.check(game_not_full)
@commands.check(is_not_running)
@commands.check(in_game_channel)
async def join(ctx, mask):
    global players
    await ctx.author.add_roles(guild_settings[ctx.guild.id]['role'])
    players[ctx.author.id] = { 
        'mask':mask, 
        'role':{'name':'', 'duel':0, 'dance':0}, 
        'gifts':{'unclaimed': 0, 'deny':1, 'encore':0, 'plate switch':1, 'guess':False, 'guess immunity':False, 'reserve':0, 'premium':False},
        'votes':{'voted':False, 'votable':False}, 
        'plate':{'poisoned':False},
        'death':''
        }
    await ctx.send('{} has joined the game as **The {}**! {} more players neeeded.'.format(ctx.author.mention, mask, MAX_PLAYERS - len(players)))

@join.error
async def join_error(ctx, error):
    if isinstance(error, NoGameChannel):
        await ctx.send('There is no designated game channel on this server, please use the {}setup command to designate one.'.format(COMMAND_PREFIX))
    if isinstance(error, NotGameChannel):
        await ctx.send('This is not the game channel, please retry this command within {}'.format(guild_settings[ctx.guild.id]['channel'].mention))
    if isinstance(error, GameStateError):
        await ctx.send('You cannot join whie the game is running.')
    if isinstance(error, GameSizeError):
        await ctx.send('The game is already full. Please wait for the next game.')
    if isinstance(error, PlayerStateError):
        await ctx.send('You are already in the game.')
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Please list your mask. {}join <mask_name>'.format(COMMAND_PREFIX))

@bot.command()
@commands.check(is_player)
@commands.check(in_game_channel)
async def leave(ctx):
    global players
    if running:
        await kill_player(ctx, ctx.author, 'committed suicide')
    else:
        await ctx.send('**The {}** has left the game. {} more players needed.'.format(players[ctx.author.id]['mask'], MIN_PLAYERS - len(players) + 1))
        await ctx.author.remove_roles(guild_settings[ctx.guild.id]['role'])
        players.pop(ctx.author.id)

@leave.error
async def leave_error(ctx, error):
    if isinstance(error, NoGameChannel):
        await ctx.send('There is no designated game channel on this server, please use the {}setup command to designate one.'.format(COMMAND_PREFIX))
    if isinstance(error, NotGameChannel):
        await ctx.send('This is not the game channel, please retry this command within {}'.format(guild_settings[ctx.guild.id]['channel'].mention))
    if isinstance(error, PlayerStateError):
        await ctx.send('You are not in a game.')

@bot.command()
@commands.check(in_game_channel)
@commands.is_owner()
async def fleave(ctx, member: discord.Member):
    global players
    if member.id in players:
        if running:
            await kill_player(ctx, member, 'died of a heart attack')
        else:
            await ctx.send('**The {}** is dragged away by his parents because it is past his bed time. {} more players needed.'.format(players[member.id]['mask'], MIN_PLAYERS - len(players) + 1))
            await member.remove_roles(guild_settings[ctx.guild.id]['role'])
            players.popitem(member.id)

@fleave.error
async def fleave_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send('You do not have the permissions to perform this command.')
    if isinstance(error, NoGameChannel):
        await ctx.send('There is no designated game channel on this server, please use the {}setup command to designate one.'.format(COMMAND_PREFIX))
    if isinstance(error, NotGameChannel):
        await ctx.send('This is not the game channel, please retry this command within {}'.format(guild_settings[ctx.guild.id]['channel'].mention))
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Please include the member you wish to kick from the game.')
    if isinstance(error, commands.BadArgument):
        await ctx.send('I could not find that member.')

#--------- Start and Stop ---------#
@bot.command()
@commands.check(game_full)
@commands.check(is_player)
@commands.check(is_running)
@commands.check(in_game_channel)
async def start(ctx):
    await ctx.send('Starting game...')
    await init_game(ctx)

@start.error
async def start_error(ctx, error):
    if isinstance(error, NoGameChannel):
        await ctx.send('There is no designated game channel on this server, please use the {}setup command to designate one.'.format(COMMAND_PREFIX))
    if isinstance(error, NotGameChannel):
        await ctx.send('This is not the game channel, please retry this command within {}'.format(guild_settings[ctx.guild.id]['channel'].mention))
    if isinstance(error, GameStateError):
        await ctx.send('A game is already running.')
    if isinstance(error, PlayerStateError):
        await ctx.send('You cannot start a game you are not apart of. Use {}join first.'.format(COMMAND_PREFIX))
    if isinstance(error, GameSizeError):
        await ctx.send('The game does not have enough players yet, you need at least {} more.'.format(MIN_PLAYERS - len(players)))

@bot.command()
@commands.check(is_not_running)
@commands.check(in_game_channel)
@commands.is_owner()
async def fstart(ctx): #Forces init_game()
    await ctx.send('Force starting game...')
    await init_game(ctx)

@fstart.error
async def fstart_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send('You do not have the permissions to perform this command.')
    if isinstance(error, NoGameChannel):
        await ctx.send('There is no designated game channel on this server, please use the {}setup command to designate one.'.format(COMMAND_PREFIX))
    if isinstance(error, NotGameChannel):
        await ctx.send('This is not the game channel, please retry this command within {}'.format(guild_settings[ctx.guild.id]['channel'].mention))
    if isinstance(error, GameStateError):
        await ctx.send('A game is already running.')

@bot.command()
@commands.check(is_running)
@commands.check(in_game_channel)
@commands.is_owner()
async def fstop(ctx): #Forces end_game()
    await end_game(ctx)
    await ctx.send('Force stopped game.')

@fstop.error
async def fstop_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send('You do not have the permissions to perform this command.')
    if isinstance(error, NoGameChannel):
        await ctx.send('There is no designated game channel on this server, please use the {}setup command to designate one.'.format(COMMAND_PREFIX))
    if isinstance(error, NotGameChannel):
        await ctx.send('This is not the game channel, please retry this command within {}'.format(guild_settings[ctx.guild.id]['channel'].mention))
    if isinstance(error, GameStateError):
        await ctx.send('There is no game running at the moment.')

#--------- Challenge Phase --------#
@bot.command()
@commands.check(is_CP)
@commands.check(is_player)
@commands.check(is_running)
@commands.check(in_game_channel)
async def challenge(ctx, member: discord.Member, challenge_type: str):
    global challenges
    if ctx.author.id not in challenges:
        if member.id in players:
            if challenge_type.lower() == 'dance' or challenge_type.lower() == 'duel':
                challenges[ctx.author.id] = {'type':challenge_type.lower(), 'opponent':member.id, 'status':'pending'}
                await ctx.send('**The {}** has challenged **The {}** to a **{}**!'.format(players[ctx.author.id]['mask'], players[member.id]['mask'], challenge_type.lower()))
            else:
                await ctx.send('"{}" is not a valid challenge type.'.format(challenge_type))
        else:
            await ctx.send('Please select a user that is playing in the current game.')
    else:
        await ctx.send('You have already challenged someone this phase.')

@challenge.error
async def challenge_error(ctx, error):
    if isinstance(error, NoGameChannel):
        await ctx.send('There is no designated game channel on this server, please use the {}setup command to designate one.'.format(COMMAND_PREFIX))
    if isinstance(error, NotGameChannel):
        await ctx.send('This is not the game channel, please retry this command within {}'.format(guild_settings[ctx.guild.id]['channel'].mention))
    if isinstance(error, GameStateError):
        await ctx.send('There is no game running at the moment.')
    if isinstance(error, PlayerStateError):
        await ctx.send('You are not playing in the current game. please wait for the next one.')
    if isinstance(error, PhaseStateError):
        await ctx.send('It is not currently the Challenge Phase.')
    if isinstance(error, commands.BadArgument):
        await ctx.send('I could not find that member, or your challenge type is invalid.')
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}challenge <player> <dance/duel>'.format(COMMAND_PREFIX))

@bot.command()
@commands.check(is_CP)
@commands.check(is_player)
@commands.check(is_running)
@commands.check(in_game_channel)
async def accept(ctx, member: discord.Member):
    global challenges
    if member.id in players:
        try:
            if challenges[member.id]['opponent'] == ctx.author.id:
                if challenges[member.id]['status'] == 'pending':
                    challenges[member.id]['status'] = 'accepted'
                    await ctx.send("**The {}** has accepted **The {}'s** {}!".format(players[ctx.author.id]['mask'], players[member.id]['mask'], challenges[member.id]['type']))
                else:
                    await ctx.send('You have already accepted or denied this challenge.')
            else:
                await ctx.send('This player has not challenged you')
        except KeyError as e:
            print(e)
            await ctx.send('This player has not challenged you')
    else:
        await ctx.send('Please select a user that is playing in the current game.')

@accept.error
async def accept_error(ctx, error):
    if isinstance(error, NoGameChannel):
        await ctx.send('There is no designated game channel on this server, please use the {}setup command to designate one.'.format(COMMAND_PREFIX))
    if isinstance(error, NotGameChannel):
        await ctx.send('This is not the game channel, please retry this command within {}'.format(guild_settings[ctx.guild.id]['channel'].mention))
    if isinstance(error, GameStateError):
        await ctx.send('There is no game running at the moment.')
    if isinstance(error, PlayerStateError):
        await ctx.send('You are not playing in the current game. please wait for the next one.')
    if isinstance(error, PhaseStateError):
        await ctx.send('It is not currently the Challenge Phase.')
    if isinstance(error, commands.BadArgument):
        await ctx.send('I could not find that member.')
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}accept <player>'.format(COMMAND_PREFIX))

@bot.command()
@commands.check(is_CP)
@commands.check(is_player)
@commands.check(is_running)
@commands.check(in_game_channel)
async def deny(ctx, member: discord.Member):
    global challenges
    if players[ctx.author.id]['gifts']['deny'] >= 1:
        if member.id in players:
            try:
                if challenges[member.id]['opponent'] == ctx.author.id:
                    if challenges[member.id]['status'] == 'pending':
                        players[ctx.author.id]['gifts']['deny'] -= 1
                        challenges[member.id]['status'] = 'denied'
                        await ctx.send("**The {}** has denied **The {}'s** {}!".format(players[ctx.author.id]['mask'], players[member.id]['mask'], challenges[member.id]['type']))
                    else:
                        await ctx.send('You have already accepted or denied this challenge.')
                else:
                    await ctx.send('This player has not challenged you')
            except KeyError as e:
                    print(e)
                    await ctx.send('This player has not challenged you')
        else:
            await ctx.send('Please select a user that is playing in the current game.')
    else:
        await ctx.send('You do not have any denies.')

@accept.error
async def deny_error(ctx, error):
    if isinstance(error, NoGameChannel):
        await ctx.send('There is no designated game channel on this server, please use the {}setup command to designate one.'.format(COMMAND_PREFIX))
    if isinstance(error, NotGameChannel):
        await ctx.send('This is not the game channel, please retry this command within {}'.format(guild_settings[ctx.guild.id]['channel'].mention))
    if isinstance(error, GameStateError):
        await ctx.send('There is no game running at the moment.')
    if isinstance(error, PlayerStateError):
        await ctx.send('You are not playing in the current game. please wait for the next one.')
    if isinstance(error, PhaseStateError):
        await ctx.send('It is not currently the Challenge Phase.')
    if isinstance(error, commands.BadArgument):
        await ctx.send('I could not find that member.')
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}deny <player>'.format(COMMAND_PREFIX))

#--------- Voting Phase ---------#
@bot.command()
@commands.check(is_VP)
@commands.check(is_player)
@commands.check(is_running)
@commands.check(in_game_channel)
async def claim(ctx, gift):
    global players
    if players[ctx.player.id]['gifts']['unclaimed'] >= 1:
        if gift.lower() == 'deny' or gift.lower() == 'encore' or gift.lower() == 'plate switch' or gift.lower() == 'reserve':
            players[ctx.author.id]['gifts']['unclaimed'] -= 1
            players[ctx.author.id]['gifts'][gift.lower()] += 1
            await ctx.send('You have claimed a {}.'.format(gift.lower()))
        elif gift.lower() == 'guess' or gift.lower() == 'guess immunity' or gift.lower() == 'premium':
            if not players[ctx.author.id]['gifts'][gift.lower()]:
                players[ctx.author.id]['gifts']['unclaimed'] -= 1
                players[ctx.author.id]['gifts'][gift.lower()] = True
                await ctx.send('You have claimed a {}.'.format(gift.lower()))
            else:
                await ctx.send('You have already claimed that gift this round.')
        else:
            await ctx.send('That gift does not exist.')
    else:
        await ctx.send('You have already claimed your maximum number of gifts this round.')

@claim.error
async def claim_error(ctx, error):
    if isinstance(error, commands.PrivateMessageOnly):
        await ctx.send('Please claim gifts in DMs.')
    if isinstance(error, PlayerStateError):
        await ctx.send('You are not playing in the current game, please wait for the next one.')
    if isinstance(error, commands.BadArgument):
        await ctx.send('That gift does not exist.')
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}claim <gift>'.format(COMMAND_PREFIX))

@bot.command()
@commands.check(is_VP)
@commands.check(is_player)
@commands.dm_only()
async def redeem(ctx, gift):
    global players
    if players[ctx.player.id]['gifts']['reserve'] >= 1:
        if gift.lower() == 'deny' or gift.lower() == 'encore' or gift.lower() == 'plate switch':
            players[ctx.author.id]['gifts']['reserve'] -= 1
            players[ctx.author.id]['gifts'][gift.lower()] += 1
            await ctx.send('You have redeemed a {}.'.format(gift.lower()))
        elif gift.lower() == 'guess' or gift.lower() == 'guess immunity' or gift.lower() == 'premium':
            if not players[ctx.author.id]['gifts'][gift.lower()]:
                players[ctx.author.id]['gifts']['reserve'] -= 1
                players[ctx.author.id]['gifts'][gift.lower()] = True
                await ctx.send('You have redeemed a {}.'.format(gift.lower()))
            else:
                await ctx.send('You have already claimed or redeemed that gift this round.')
        else:
            await ctx.send('That gift does not exist.')
    else:
        await ctx.send('You have no reserves left.')

@redeem.error
async def redeem_error(ctx, error):
    if isinstance(error, NoGameChannel):
        await ctx.send('There is no designated game channel on this server, please use the {}setup command to designate one.'.format(COMMAND_PREFIX))
    if isinstance(error, NotGameChannel):
        await ctx.send('This is not the game channel, please retry this command within {}'.format(guild_settings[ctx.guild.id]['channel'].mention))
    if isinstance(error, GameStateError):
        await ctx.send('There is no game running at the moment.')
    if isinstance(error, PlayerStateError):
        await ctx.send('You are not playing in the current game, please wait for the next one.')
    if isinstance(error, commands.BadArgument):
        await ctx.send('That gift does not exist.')
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}redeem <gift>'.format(COMMAND_PREFIX))

@bot.command()
@commands.check(is_VP)
@commands.check(is_player)
@commands.check(is_running)
@commands.check(in_game_channel)
async def vote(ctx, member: discord.Member):
    global players
    global votes
    if not players[ctx.author.id]['votes']['voted']:
        if member.id in players:
            if players[member.id]['votes']['votable']:
                if member.id in votes:
                    votes[member.id].append(ctx.author.id)
                else:
                    votes[member.id] = [ctx.author.id]
                players[ctx.author.id]['votes']['voted'] = True
                await ctx.send('**The {}** has voted for **The {}**, bringing their vote count to **{}**!'.format(players[ctx.author.id]['mask'], players[member.id]['mask'], len(votes[member.id])))
            else:
                await ctx.send('You cannot vote for that player as they did not lose a challenge this round.')
        else:
            await ctx.send('Please select a user that is playing in the current game.')
    else:
        await ctx.send('You have already voted this phase.')

@vote.error
async def vote_error(ctx, error):
    if isinstance(error, NoGameChannel):
        await ctx.send('There is no designated game channel on this server, please use the {}setup command to designate one.'.format(COMMAND_PREFIX))
    if isinstance(error, NotGameChannel):
        await ctx.send('This is not the game channel, please retry this command within {}'.format(guild_settings[ctx.guild.id]['channel'].mention))
    if isinstance(error, GameStateError):
        await ctx.send('There is no game running at the moment.')
    if isinstance(error, PlayerStateError):
        await ctx.send('You are not playing in the current game. please wait for the next one.')
    if isinstance(error, PhaseStateError):
        await ctx.send('It is not currently the Voting Phase.')
    if isinstance(error, commands.BadArgument):
        await ctx.send('I could not find that member.')
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}vote <player>'.format(COMMAND_PREFIX))

#--------- Dinner Phase ---------#
@bot.command()
@commands.check(is_DP)
@commands.check(is_player)
@commands.check(is_running)
@commands.check(in_game_channel)
async def switch(ctx, member: discord.Member):
    global players
    if players[ctx.author.id]['gifts']['plate switch'] >= 1:
        if member.id in players:
            players[ctx.author.id]['gifts']['plate switch'] -= 1
            players[ctx.author.id]['plate'], players[member.id]['plate'] = players[member.id]['plate'], players[ctx.author.id]['plate']
            players[ctx.author.id]['gifts']['premium'], players[member.id]['gifts']['premium'] = players[member.id]['gifts']['premium'], players[ctx.author.id]['gifts']['premium']
            await ctx.send('**The {}** has switched plates with **The {}**!'.format(players[ctx.author.id]['mask'], players[member.id]['mask']))
        else:
            await ctx.send('Please select a user that is playing in the current game.')
    else:
        await ctx.send('You do not have any remaining plate switches.')

@switch.error
async def switch_error(ctx, error):
    if isinstance(error, NoGameChannel):
        await ctx.send('There is no designated game channel on this server, please use the {}setup command to designate one.'.format(COMMAND_PREFIX))
    if isinstance(error, NotGameChannel):
        await ctx.send('This is not the game channel, please retry this command within {}'.format(guild_settings[ctx.guild.id]['channel'].mention))
    if isinstance(error, GameStateError):
        await ctx.send('There is no game running at the moment.')
    if isinstance(error, PlayerStateError):
        await ctx.send('You are not playing in the current game. please wait for the next one.')
    if isinstance(error, PhaseStateError):
        await ctx.send('It is not currently the Dinner Phase.')
    if isinstance(error, commands.BadArgument):
        await ctx.send('I could not find that member.')
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}switch <player>'.format(COMMAND_PREFIX))

########## FUNCTIONS ##########
async def init_game(ctx):
    global running
    global state
    global players
    running = True #Game is running
    state['round'] = 0

    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False) #Prevents non-players from posting in the channel
    player_keys = list(players)
    random.shuffle(player_keys)
    for key in player_keys:
        players.move_to_end(key)
    i = 0
    for player in players:
        player = await commands.MemberConverter().convert(ctx, str(player))
        players[player.id]['role'] = ROLES[i]
        await player.send('You are **The {}**!'.format(players[player.id]['role']['name']))
        i += 1

    bot.loop.create_task(game_loop(ctx))

async def game_loop(ctx): #TODO
    global challenges
    global state
    global phase_start
    global game_info
    while running:
        state['round'] += 1
        challenges = OrderedDict()
        phase_start = datetime.datetime.now()
        print(phase_start)

        game_info = discord.Embed(title='CP{}'.format(state['round']))
        game_info.add_field(name='Pending Challenges', value='None')
        game_info.add_field(name='Accepted Challenges', value='None')
        game_info.add_field(name='Denied Challenges', value='None')
        game_info.add_field(name='Cowards', value='None')
        game_info.add_field(name='Waiting On', value='None')

        await ctx.send('It is now CP{}. You may make challenges with /challenge and accept them with /accept and /deny'.format(state['round']))
        state['phase'] = 'CP'
        try:
            while (datetime.datetime.now() - phase_start) < timedelta(seconds=30):
                print(phase_start)
                print(datetime.datetime.now())
                print(phase_start - datetime.datetime.now())
                await asyncio.sleep(0.1)
        except Exception as e:
            print(e.__traceback__)
        try:
            for item in challenges:
                if item['status'] == 'denied':
                    await ctx.send("**The {}**'s {} with **The {}** was denied.".format(players[item]['mask'], challenges[item]['type'], players[challenges[item]['opponent']]['mask']))
                else:
                    if players[item]['role'][challenges[item]['type']] > players[challenges[item]['opponent']]['role'][challenges[item]['type']]:
                        winner = players[item]['mask']
                        loser = players[challenges[item]['opponent']]['mask']
                        players[challenges[item]['opponent']]['votes']['votable'] = True
                    else:
                        loser = players[item]['mask']
                        winner = players[challenges[item]['opponent']]['mask']
                        players[item]['votes']['votable'] = True
                    players[item]['gifts']['unclaimed'] += 1
                    players[challenges[item]['opponent']]['gifts']['unclaimed'] +=1
                    await ctx.send('**The {}** won the {} with the {}.'.format(winner, challenges[item]['type'], loser))
        except Exception as e:
            print(e.__traceback__)     
            
async def remove_role(ctx, member):
    try:
        member = await commands.MemberConverter().convert(ctx, str(member))
        await member.remove_roles(guild_settings[ctx.guild.id]['role'])
    except Exception as e:
        print(e)

async def kill_player(ctx, member, reason):
    global dead
    try:
        member = await commands.MemberConverter().convert(ctx, str(member))
        await remove_role(ctx, member.id)
        dead[member.id] = {'mask':players[member.id]['mask'], 'role':players[member.id]['role']['name'], 'death':reason, 'time':'{}{}'.format(state['phase'], state['round'])}
        players.pop(member.id)
        await ctx.send('**The {}** {}. They were **The {}**! *{} players remain*.'.format(dead[member.id]['mask'], reason, dead[member.id]['role'], len(players)))
    except Exception as e:
        print(e)

async def end_game(ctx):
    global running
    global players
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=None) #Resets channel permissions for @everyone

    for player in players:
        await remove_role(ctx, player)
    
    players = OrderedDict()
    running = False

bot.run(BOT_KEY)