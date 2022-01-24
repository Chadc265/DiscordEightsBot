import configparser
import discord
from discord.ext import commands
from src.eights_bot import QueueBot
from src.queue_cog import QueueManagerCog
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

CFG_PATH = "data/config.ini"
TESTING = False

def get_bot_token(config_path:str):
    config = configparser.ConfigParser()
    config.read(config_path)
    return config['discord']['QueueBot_token']

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
bot = QueueBot("!", data_path="data/players.json", intents=intents)


@bot.command("allow_queues", help="Load the queue cog")
async def allow_queues(ctx:commands.Context):
    if ctx.author.name == "CRZYCLWN13":
        if len(bot.cogs) == 0:
            guild: discord.Guild = ctx.guild
            cog = QueueManagerCog(bot)
            bot.add_cog(cog)
            await ctx.channel.send("Queue cog ready! Maybe?")


@bot.command("shutdown")
async def shutdown(ctx:commands.Context):
    if ctx.author.name == "CRZYCLWN13":
        bot.save_players()
        if len(bot.cogs) > 0:
            cog:QueueManagerCog = bot.get_cog("QueueManagerCog")
            await cog.clean_up_queue_channels(ctx.guild)
            bot.remove_cog("QueueManagerCog")

# bot.add_cog(QueueCog(bot, 1))
bot.run(get_bot_token(CFG_PATH))