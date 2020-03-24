#Behind the Masks Discord Bot v0.1.0b
#Copyright (c) 2020 DJVoxel
#Behind the Masks is the intellectual property of VucubCaquix
#All Rights Reserved

import asyncio
import datetime
import random
import traceback
from collections import OrderedDict
from datetime import timedelta

import discord
from discord.ext import commands
from discord.ext.commands import bot

from Settings import *

bot = commands.Bot(COMMAND_PREFIX)

########## GLOBALS ##########
running = False
player_info = OrderedDict() #uid:[mask, role:[name, duel, dance, <ability charges>], gifts:[denies, encores, pswitches, GI?, Guess?, reserve], plate:[Poisoned?, Premium?], death]
masks = {} #mask:discord.Member
dead = OrderedDict() #uid:[mask, role, death]

state = {'phase':None, 'round':1}
challenges = OrderedDict() #uid:[dance/duel, uid]
votes = OrderedDict() #uid:[uids of voters]
end_phase = False

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

game_info =  discord.Embed(title='The game has not started yet.')
player_status = discord.Embed(title='The game has not started yet.')

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

class GameRunningError(commands.CheckFailure):
    pass

class GameNotRunningError(commands.CheckFailure):
    pass

class IsPlayerError(commands.CheckFailure):
    pass

class NotPlayerError(commands.CheckFailure):
    pass

class GameFullError(commands.CheckFailure):
    pass

class GameNotFullError(commands.CheckFailure):
    pass

class NotCPError(commands.CheckFailure):
    pass

class NotVPError(commands.CheckFailure):
    pass

class NotDPError(commands.CheckFailure):
    pass

class GameEnded(Exception):
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
        raise GameNotRunningError
    return True

def is_not_running(ctx):
    if running:
        raise GameRunningError
    return True

def is_player(ctx):
    if ctx.author.id not in player_info:
        raise NotPlayerError
    return True

def is_not_player(ctx):
    if ctx.author.id in player_info:
        raise IsPlayerError
    return True

def game_full(ctx):
    if len(player_info) < MIN_PLAYERS:
        raise GameNotFullError
    return True

def game_not_full(ctx):
    if len(player_info) >= MAX_PLAYERS:
        raise GameFullError
    return True

def is_CP(ctx):
    if state['phase'] != 'CP':
        raise NotCPError
    return True

def is_VP(ctx):
    if state['phase'] != 'VP':
        raise NotVPError
    return True

def is_DP(ctx):
    if state['phase'] != 'DP':
        raise NotDPError
    return True

########## COMMANDS ##########
@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

#--------- Setup ---------#
@bot.command()
@commands.is_owner()
@commands.guild_only()
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
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}setup <Role Name>'.format(COMMAND_PREFIX))
    else:
        await handle_errors(ctx, error)

#--------- Help and Info ---------#
@bot.command()
@commands.check(is_running)
@commands.guild_only()
async def info(ctx):
    await ctx.send(embed=game_info)

@bot.command()
@commands.check(is_running)
@commands.guild_only()
async def status(ctx):
    await ctx.send(embed=player_status)

#--------- Join and Leave ---------#
@bot.command()
@commands.check(is_not_player)
@commands.check(game_not_full)
@commands.check(is_not_running)
@commands.check(in_game_channel)
@commands.guild_only()
async def join(ctx, mask):
    global player_info
    global masks
    await ctx.author.add_roles(guild_settings[ctx.guild.id]['role'])
    player_info[ctx.author.id] = { 
        'mask':mask, 
        'role':{'name':'', 'duel':0, 'dance':0}, 
        'gifts':{'unclaimed': 0, 'deny':1, 'encore':0, 'plate switch':1, 'guess':False, 'guess immunity':False, 'reserve':0, 'premium':False},
        'votes':{'voted':False, 'votable':False}, 
        'plate':{'poisoned':False},
        'death':'',
        'waiting': 1
        }
    masks[mask] = ctx.author
    await ctx.send('{} has joined the game as **The {}**! {} more players needed.'.format(ctx.author.mention, mask, MAX_PLAYERS - len(player_info)))

@join.error
async def join_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('Please list your mask. {}join <mask_name>'.format(COMMAND_PREFIX))
    else:
        await handle_errors(ctx, error)

@bot.command()
@commands.check(is_player)
@commands.check(in_game_channel)
@commands.guild_only()
async def leave(ctx):
    if running:
        await kill_player(ctx, ctx.author, 'committed suicide')
    else:
        await ctx.send('**The {}** has left the game. {} more players needed.'.format(player_info[ctx.author.id]['mask'], MIN_PLAYERS - len(player_info) + 1))
        await ctx.author.remove_roles(guild_settings[ctx.guild.id]['role'])
        masks.pop(player_info.pop(ctx.author.id)['mask'])

@bot.command()
@commands.check(in_game_channel)
@commands.is_owner()
@commands.guild_only()
async def fleave(ctx, member: discord.Member):
    global player_info
    if member.id in player_info:
        if running:
            await kill_player(ctx, member, 'died of a heart attack')
        else:
            await ctx.send('**The {}** is dragged away by his parents because it is past his bed time. {} more players needed.'.format(player_info[member.id]['mask'], MIN_PLAYERS - len(player_info) + 1))
            await member.remove_roles(guild_settings[ctx.guild.id]['role'])
            masks.pop(player_info.pop(member.id)['mask'])

@fleave.error
async def fleave_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}fleave <Player>'.format(COMMAND_PREFIX))
    elif isinstance(error, commands.BadArgument):
        await ctx.send('I could not find that member.')
    else:
        await handle_errors(ctx, error)

#--------- Start and Stop ---------#
@bot.command()
@commands.check(game_full)
@commands.check(is_player)
@commands.check(is_running)
@commands.check(in_game_channel)
async def start(ctx):
    await ctx.send('Starting game...')
    await init_game(ctx)

@bot.command()
@commands.check(is_not_running)
@commands.check(in_game_channel)
@commands.is_owner()
async def fstart(ctx): #Forces init_game()
    await ctx.send('Force starting game...')
    await init_game(ctx)

@fstart.error
async def fstart_error(ctx, error):
    await handle_errors(ctx, error)

@bot.command()
@commands.check(is_running)
@commands.check(in_game_channel)
@commands.is_owner()
async def fstop(ctx): #Forces end_game()
    await end_game(ctx)
    await ctx.send('Force stopping game....')

#--------- Skip ---------#
@bot.command()
@commands.check(is_running)
@commands.check(in_game_channel)
@commands.is_owner()
async def fskip(ctx):
    global end_phase
    end_phase = True
    await ctx.send('Force skipped phase.')

#--------- Challenge Phase --------#
@bot.command()
@commands.check(is_CP)
@commands.check(is_player)
@commands.check(is_running)
@commands.check(in_game_channel)
@commands.guild_only()
async def challenge(ctx, member: discord.Member, challenge_type): #TODO Prevent you from challenging yourself
    global challenges
    if ctx.author.id not in challenges:
        if member.id in player_info:
            if member.id != ctx.author.id:
                if challenge_type.lower() == 'dance' or challenge_type.lower() == 'duel':
                    challenges[ctx.author.id] = {'type':challenge_type.lower(), 'opponent':member.id, 'status':'Pending'}
                    await ctx.send('**The {}** has challenged **The {}** to a **{}**!'.format(player_info[ctx.author.id]['mask'], player_info[member.id]['mask'], challenge_type.lower()))
                    update_info(challenges[ctx.author.id], challenger_id=ctx.author.id, author_id=ctx.author.id)
                else:
                    await ctx.send('"{}" is not a valid challenge type.'.format(challenge_type))
            else:
                await ctx.send('You cannot challenge yourself.')
        else:
            await ctx.send('Please select a user that is playing in the current game.')
    else:
        await ctx.send('You have already challenged someone this phase.')

@challenge.error
async def challenge_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('I could not find that member, or your challenge type is invalid.')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}challenge <player> <dance/duel>'.format(COMMAND_PREFIX))
    else:
        await handle_errors(ctx, error)

@bot.command()
@commands.check(is_CP)
@commands.check(is_player)
@commands.check(is_running)
@commands.check(in_game_channel)
@commands.guild_only()
async def accept(ctx, member: discord.Member):
    global challenges
    if member.id in player_info:
        if member.id in challenges:
            if challenges[member.id]['opponent'] == ctx.author.id:
                if challenges[member.id]['status'] == 'Pending':
                    challenges[member.id]['status'] = 'Accepted'
                    await ctx.send("**The {}** has accepted **The {}'s** {}!".format(player_info[ctx.author.id]['mask'], player_info[member.id]['mask'], challenges[member.id]['type']))
                    update_info(challenges[member.id], challenger_id=member.id, author_id=ctx.author.id)
                else:
                    await ctx.send('You have already accepted or denied this challenge.')
            else:
                await ctx.send('This player has not challenged you')
        else:
            await ctx.send('This player has not challenged yet')
    else:
        await ctx.send('Please select a user that is playing in the current game.')

@accept.error
async def accept_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('I could not find that member.')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}accept <player>'.format(COMMAND_PREFIX))
    else:
        await handle_errors(ctx, error)

@bot.command()
@commands.check(is_CP)
@commands.check(is_player)
@commands.check(is_running)
@commands.check(in_game_channel)
@commands.guild_only()
async def deny(ctx, member: discord.Member):
    global challenges
    if player_info[ctx.author.id]['gifts']['deny'] >= 1:
        if member.id in player_info:
            if member.id in challenges:
                if challenges[member.id]['opponent'] == ctx.author.id:
                    if challenges[member.id]['status'] == 'Pending':
                        player_info[ctx.author.id]['gifts']['deny'] -= 1
                        challenges[member.id]['status'] = 'Denied'
                        await ctx.send("**The {}** has denied **The {}'s** {}!".format(player_info[ctx.author.id]['mask'], player_info[member.id]['mask'], challenges[member.id]['type']))
                        update_info(challenges[member.id], challenger_id=member.id, author_id=ctx.author.id)
                    else:
                        await ctx.send('You have already accepted or denied this challenge.')
                else:
                    await ctx.send('This player has not challenged you')
            else:
                await ctx.send('This player has not challenged yet')
        else:
            await ctx.send('Please select a user that is playing in the current game.')
    else:
        await ctx.send('You do not have any denies.')

@deny.error
async def deny_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('I could not find that member.')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}deny <player>'.format(COMMAND_PREFIX))
    else:
        await handle_errors(ctx, error)

@bot.command()
@commands.check(is_CP)
@commands.check(is_player)
@commands.check(is_running)
@commands.check(in_game_channel)
@commands.guild_only()
async def nochallenge(ctx):
    challenges[ctx.author.id] = {'status':'Coward'}
    await ctx.send('**The {}** has chickened out.'.format(player_info[ctx.author.id]['mask']))
    update_info(challenges[ctx.author.id], challenger_id=ctx.author.id, author_id=ctx.author.id)

#--------- Voting Phase ---------#
@bot.command()
@commands.check(is_VP)
@commands.check(is_player)
@commands.check(is_running)
@commands.dm_only()
async def claim(ctx, gift):
    global player_info
    if player_info[ctx.player.id]['gifts']['unclaimed'] >= 1:
        if gift.lower() == 'deny' or gift.lower() == 'encore' or gift.lower() == 'plate switch' or gift.lower() == 'reserve':
            player_info[ctx.author.id]['gifts']['unclaimed'] -= 1
            player_info[ctx.author.id]['gifts'][gift.lower()] += 1
            await ctx.send('You have claimed a {}.'.format(gift.lower()))
        elif gift.lower() == 'guess' or gift.lower() == 'guess immunity' or gift.lower() == 'premium':
            if not player_info[ctx.author.id]['gifts'][gift.lower()]:
                player_info[ctx.author.id]['gifts']['unclaimed'] -= 1
                player_info[ctx.author.id]['gifts'][gift.lower()] = True
                await ctx.send('You have claimed a {}.'.format(gift.lower()))
            else:
                await ctx.send('You have already claimed that gift this round.')
        else:
            await ctx.send('That gift does not exist.')
    else:
        await ctx.send('You have already claimed your maximum number of gifts this round.')

@claim.error
async def claim_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('That gift does not exist.')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}claim <gift>'.format(COMMAND_PREFIX))
    else:
        await handle_errors(ctx, error)

@bot.command()
@commands.check(is_VP)
@commands.check(is_player)
@commands.dm_only()
async def redeem(ctx, gift):
    global player_info
    if player_info[ctx.player.id]['gifts']['reserve'] >= 1:
        if gift.lower() == 'deny' or gift.lower() == 'encore' or gift.lower() == 'plate switch':
            player_info[ctx.author.id]['gifts']['reserve'] -= 1
            player_info[ctx.author.id]['gifts'][gift.lower()] += 1
            await ctx.send('You have redeemed a {}.'.format(gift.lower()))
        elif gift.lower() == 'guess' or gift.lower() == 'guess immunity' or gift.lower() == 'premium':
            if not player_info[ctx.author.id]['gifts'][gift.lower()]:
                player_info[ctx.author.id]['gifts']['reserve'] -= 1
                player_info[ctx.author.id]['gifts'][gift.lower()] = True
                await ctx.send('You have redeemed a {}.'.format(gift.lower()))
            else:
                await ctx.send('You have already claimed or redeemed that gift this round.')
        else:
            await ctx.send('That gift does not exist.')
    else:
        await ctx.send('You have no reserves left.')

@redeem.error
async def redeem_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('That gift does not exist.')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}redeem <gift>'.format(COMMAND_PREFIX))
    else:
        await handle_errors(ctx, error)

@bot.command()
@commands.check(is_VP)
@commands.check(is_player)
@commands.check(is_running)
@commands.dm_only()
async def vote(ctx, member: discord.Member):
    global player_info
    global votes
    if not player_info[ctx.author.id]['votes']['voted']:
        if member.id in player_info:
            if player_info[member.id]['votes']['votable']:
                if member.id in votes:
                    votes[member.id].append(ctx.author.id)
                else:
                    votes[member.id] = [ctx.author.id]
                player_info[ctx.author.id]['votes']['voted'] = True
                await ctx.send('**The {}** has voted for **The {}**, bringing their vote count to **{}**!'.format(player_info[ctx.author.id]['mask'], player_info[member.id]['mask'], len(votes[member.id])))
            else:
                await ctx.send('You cannot vote for that player as they did not lose a challenge this round.')
        else:
            await ctx.send('Please select a user that is playing in the current game.')
    else:
        await ctx.send('You have already voted this phase.')

@vote.error
async def vote_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('I could not find that member.')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}vote <player>'.format(COMMAND_PREFIX))
    else:
        await handle_errors(ctx, error)

#--------- Dinner Phase ---------#
@bot.command()
@commands.check(is_DP)
@commands.check(is_player)
@commands.check(is_running)
@commands.check(in_game_channel)
@commands.guild_only()
async def switch(ctx, member: discord.Member):
    global player_info
    if player_info[ctx.author.id]['gifts']['plate switch'] >= 1:
        if member.id in player_info:
            player_info[ctx.author.id]['gifts']['plate switch'] -= 1
            player_info[ctx.author.id]['plate'], player_info[member.id]['plate'] = player_info[member.id]['plate'], player_info[ctx.author.id]['plate']
            player_info[ctx.author.id]['gifts']['premium'], player_info[member.id]['gifts']['premium'] = player_info[member.id]['gifts']['premium'], player_info[ctx.author.id]['gifts']['premium']
            await ctx.send('**The {}** has switched plates with **The {}**!'.format(player_info[ctx.author.id]['mask'], player_info[member.id]['mask']))
        else:
            await ctx.send('Please select a user that is playing in the current game.')
    else:
        await ctx.send('You do not have any remaining plate switches.')

@switch.error
async def switch_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('I could not find that member.')
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('{}switch <player>'.format(COMMAND_PREFIX))
    else:
        await handle_errors(ctx, error)

########## FUNCTIONS ##########
async def init_game(ctx):
    global running
    global state
    global player_info
    global end_phase
    end_phase = False
    running = True #Game is running
    state['round'] = 0

    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False) #Prevents non-players from posting in the channel
    player_keys = list(player_info)
    random.shuffle(player_keys)
    for key in player_keys:
        player_info.move_to_end(key)
    i = 0
    for player in player_info:
        player = await commands.MemberConverter().convert(ctx, str(player))
        player_info[player.id]['role'] = ROLES[i]
        await player.send('You are **The {}**!'.format(player_info[player.id]['role']['name']))
        i += 1

    bot.loop.create_task(game_loop(ctx))

async def game_loop(ctx): #TODO
    global challenges
    global state
    global phase_start
    global game_info
    global end_phase
    try:
        while running:
            state['round'] += 1
            challenges = OrderedDict()
            phase_start = datetime.datetime.now()
            end_phase = False

            game_info = discord.Embed(title='CP{}'.format(state['round']))
            game_info.add_field(name='Pending Challenges', value='None', inline=False)
            game_info.add_field(name='Accepted Challenges', value='None', inline=False)
            game_info.add_field(name='Denied Challenges', value='None', inline=False)
            game_info.add_field(name='Cowards', value='None', inline=False)
            game_info.add_field(name='Waiting On', value=''.join(['The {}\n'.format(player_info[player]['mask']) for player in player_info]), inline=False)

            for player in player_info:
                player_info[player]['waiting']  = 1

            await ctx.send('It is now CP{}. You may make challenges with /challenge and accept them with /accept and /deny'.format(state['round']))
            state['phase'] = 'CP'

            while datetime.datetime.now() < phase_start + timedelta(seconds=CP_TIMEOUT):
                if not running:
                    raise GameEnded
                if end_phase:
                    break
                game_info.title = 'CP{} | Time Remaining: {}'.format(state['round'], str(phase_start + timedelta(seconds = CP_TIMEOUT) - datetime.datetime.now()))
                await asyncio.sleep(0.1)

            for item in challenges:
                if challenges[item]['status'] != 'Coward':
                    if challenges[item]['status'] == 'Denied':
                        await ctx.send("**The {}**'s {} with **The {}** was denied.".format(player_info[item]['mask'], challenges[item]['type'], player_info[challenges[item]['opponent']]['mask']))
                    else:
                        if player_info[item]['role'][challenges[item]['type']] > player_info[challenges[item]['opponent']]['role'][challenges[item]['type']]:
                            winner = player_info[item]['mask']
                            loser = player_info[challenges[item]['opponent']]['mask']
                            player_info[challenges[item]['opponent']]['votes']['votable'] = True
                        else:
                            loser = player_info[item]['mask']
                            winner = player_info[challenges[item]['opponent']]['mask']
                            player_info[item]['votes']['votable'] = True
                        player_info[item]['gifts']['unclaimed'] += 1
                        player_info[challenges[item]['opponent']]['gifts']['unclaimed'] +=1
                        await ctx.send('**The {}** won the {} with the {}.'.format(winner, challenges[item]['type'], loser))    
    except GameEnded:
        await ctx.send('Game was forced to stop.')

def update_info(new_info, challenger_id = None, author_id=None):
    global game_info
    global end_phase
    global player_info
    messages = []
    if state['phase'] == 'CP':
        if new_info['status'] == 'Pending':
            print('Pend')
            field_id = 0
            if player_info[new_info['opponent']]['waiting'] == 0:
                game_info.set_field_at(4, name=game_info.fields[4].name, value=''.join([game_info.fields[4].value, 'The {}\n'.format(player_info[new_info['opponent']]['mask'])]), inline=False)
            player_info[new_info['opponent']]['waiting'] += 1
            messages.append('The {} has challenged the {} to a {}\n'.format(player_info[challenger_id]['mask'], player_info[new_info['opponent']]['mask'], new_info['type']))
        elif new_info['status'] == 'Coward':
            print('Cow')
            field_id = 3
            messages.append('The {}\n'.format(player_info[challenger_id]['mask']))
        else:
            print('A/D')    
            if new_info['status'] == 'Accepted':
                print('acc')
                field_id = 1
                messages.append('The {} will {} with The {}\n'.format(player_info[challenger_id]['mask'], new_info['type'], player_info[new_info['opponent']]['mask']))
            elif new_info['status'] == 'Denied':
                print('den')
                field_id = 2
                messages.append("The {} has denied The {}'s {}\n".format(player_info[challenger_id]['mask'], player_info[new_info['opponent']]['mask'], new_info['type']))
                
            pending = game_info.fields[0].value.split('The {} has challenged the {} to a {}\n'.format(player_info[challenger_id]['mask'], player_info[new_info['opponent']]['mask'], new_info['type']))

            if pending[0] == '' and pending[1] == '':
                game_info.set_field_at(0, name=game_info.fields[0].name, value='None', inline=False)
            else:
                game_info.set_field_at(0, name=game_info.fields[0].name, value=''.join(pending), inline=False)

        if game_info.fields[field_id].value != 'None':
            messages.insert(0, game_info.fields[field_id].value)

        player_info[author_id]['waiting'] -= 1
        print(player_info[author_id]['waiting'])
        if player_info[author_id]['waiting'] == 0:
            waiting = game_info.fields[4].value.split('The {}\n'.format(player_info[author_id]['mask']))
            print(waiting)
            if waiting[0] == '' and waiting[1] == '':
                game_info.set_field_at(4, name=game_info.fields[4].name, value='None', inline=False)
                end_phase = True
            else:
                game_info.set_field_at(4, name=game_info.fields[4].name, value=''.join(waiting), inline=False)

    game_info.set_field_at(field_id, name=game_info.fields[field_id].name, value=''.join(messages), inline=False)

async def convert_member(ctx, key): #TODO
    if key is str:
        if key in masks:
            return masks[key]
    return await commands.MemberConverter().convert(ctx, str(key))

async def remove_role(ctx, member):
    try:
        member = await commands.MemberConverter().convert(ctx, str(member))
        await member.remove_roles(guild_settings[ctx.guild.id]['role'])
    except Exception as e:
        print(e)

async def kill_player(ctx, member, reason, reveal=True):
    global dead
    try:
        member = await commands.MemberConverter().convert(ctx, str(member))
        await remove_role(ctx, member.id)
        dead[member.id] = {'mask':player_info[member.id]['mask'], 'role':player_info[member.id]['role']['name'], 'death':reason, 'time':'{}{}'.format(state['phase'], state['round'])}
        masks.pop(player_info.pop(member.id)['mask'])
        if reveal:
            await ctx.send('**The {}** {}. They were **The {}**! *{} players remain*.'.format(dead[member.id]['mask'], reason, dead[member.id]['role'], len(player_info)))
        else:
            await ctx.send('**The {}** {}. *{} players remain*.'.format(dead[member.id]['mask'], reason, len(player_info)))
    except Exception as e:
        print(e)

async def end_game(ctx):
    global running
    global player_info
    global masks
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=None) #Resets channel permissions for @everyone

    for player in player_info:
        await remove_role(ctx, player)
    
    player_info = OrderedDict()
    masks = {}
    running = False

@info.error
@leave.error
@start.error
@fskip.error
@fstop.error
@nochallenge.error
async def handle_errors(ctx, error):
    if isinstance(error, commands.PrivateMessageOnly):
        await ctx.send('Please only use this command in DMs.')
    if isinstance(error, commands.NoPrivateMessage):
        await ctx.send('Please use this command in the game channel.')
    if isinstance(error, NoGameChannel):
        await ctx.send('There is no designated game channel on this server, please use the {}setup command to designate one.'.format(COMMAND_PREFIX))
    if isinstance(error, NotGameChannel):
        await ctx.send('This is not the game channel, please retry this command within {}'.format(guild_settings[ctx.guild.id]['channel'].mention))
    if isinstance(error, commands.NotOwner):
        await ctx.send('You do not have permission to use this command.')
    if isinstance(error, GameNotRunningError):
        await ctx.send('There is no game currently running.')
    if isinstance(error, GameRunningError):
        await ctx.send('You cannot join whie the game is running.')
    if isinstance(error, GameFullError):
        await ctx.send('The game is already full. Please wait for the next game.')
    if isinstance(error, GameNotFullError):
        await ctx.send('The game does not have enough players yet, you need at least {} more.'.format(MIN_PLAYERS - len(player_info)))
    if isinstance(error, IsPlayerError):
        await ctx.send('You are already in the game.')
    if isinstance(error, NotPlayerError):
        await ctx.send('You are not playing in the current game. Please join using {}join or wait for the game to end.'.format(COMMAND_PREFIX))
    if isinstance(error, NotCPError):
        await ctx.send('It is not currently the Challenge Phase.')
    if isinstance(error, NotVPError):
        await ctx.send('It is not currently the Voting Phase.')
    if isinstance(error, NotDPError):
        await ctx.send('It is not currently the Dinner Phase.')

bot.run(BOT_KEY)
