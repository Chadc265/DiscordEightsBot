import configparser
import discord
from discord.ext import commands
from src.eights_bot import QueueBot
from src.queue import EightsCog
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

CFG_PATH = "data/config.ini"
TESTING = False

def get_bot_token(config_path:str):
    config = configparser.ConfigParser()
    config.read(config_path)
    return config['discord']['QueueBot_token']

bot = QueueBot("!", data_path="data/players.json")


@bot.command("4v4", help="Start a 4v4 queue")
async def load_eights(ctx:commands.Context, *, game:str):
    if TESTING:
        if ctx.channel.name != "testing":
            await ctx.channel.send("Wrong channel for that right now, try testing")
            return
    if len(bot.cogs) == 0:
        guild: discord.Guild = ctx.guild
        cog = EightsCog(bot, team_size=4, game=game)
        await cog.initialize_queue_channels(guild)
        bot.add_cog(cog)
        await ctx.channel.send("New 4v4 match queue for {g} started by {p}".format(g=game, p=ctx.author.name))

@bot.command("3v3", help="Start a 3v3 queue")
async def load_sixes(ctx:commands.Context, *, game:str):
    if TESTING:
        if ctx.channel.name != "testing":
            await ctx.channel.send("Wrong channel for that right now, try testing")
            return
    if len(bot.cogs) == 0:
        guild: discord.Guild = ctx.guild
        cog = EightsCog(bot, team_size=3, game=game)
        await cog.initialize_queue_channels(guild)
        bot.add_cog(cog)
        await ctx.channel.send("New 3v3 match queue for {g} started by {p}".format(g=game, p=ctx.author.name))

@bot.command("2v2", help="Start a 2v2 queue")
async def load_fours(ctx:commands.Context, *, game:str):
    if TESTING:
        if ctx.channel.name != "testing":
            await ctx.channel.send("Wrong channel for that right now, try testing")
            return
    if len(bot.cogs) == 0:
        guild: discord.Guild = ctx.guild
        cog = EightsCog(bot, team_size=2, game=game)
        await cog.initialize_queue_channels(guild)
        bot.add_cog(cog)
        await ctx.channel.send("New 2v2 match queue for {g} started by {p}".format(g=game, p=ctx.author.name))


@bot.command("shutdown")
async def shutdown(ctx):
    if TESTING:
        if ctx.channel.name != "testing":
            await ctx.channel.send("Wrong channel for that right now, try testing")
            return
    bot.save_players()
    if len(bot.cogs) > 0:
        cog:EightsCog = bot.get_cog("EightsCog")
        await cog.remove_queue_channels()
        bot.remove_cog("EightsCog")

# bot.add_cog(QueueCog(bot, 1))
bot.run(get_bot_token(CFG_PATH))