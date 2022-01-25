import logging

import discord
from discord.ext import commands

from src.config import BotConfig
from src.queue_bot import QueueBot
from src.queue_cog import QueueManagerCog


logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

CFG_PATH = "data/config.ini"
TESTING = False

# bot.add_cog(QueueCog(bot, 1))


if __name__ == "__main__":
    logger.info("Loading config file")
    config = BotConfig(CFG_PATH)
    logger.info("Config load successful")

    intents = discord.Intents.default()
    intents.typing = False
    intents.presences = False

    bot = QueueBot("!", data_path=config.player_data_path, intents=intents)

    @bot.command(name='allow_queues')
    async def load_cog(ctx:commands.Context):
        if ctx.author.id == config.bot_admin_id:
            if len(bot.cogs) < 1:
                logger.info("Loading Queue Cog")
                cog = QueueManagerCog(bot)
                bot.add_cog(cog)
                logger.info("Queue Cog successfully loaded and added to bot")
                await ctx.channel.send("Queue cog ready! Maybe?")
        else:
            await ctx.channel.send("{author} does not have permission to use that function".format(author=ctx.author.name))

    @bot.command(name='shutdown')
    async def remove_cog(ctx:commands.Context):
        if ctx.author.id == config.bot_admin_id:
            if len(bot.cogs) == 1:
                bot.save_players()
                logger.info("Stopping Queue Cog")
                cog:QueueManagerCog = bot.get_cog('QueueManagerCog')
                logger.info("Cleaning up queue channels")
                await cog.clean_up_queue_channels(ctx.guild)
                logger.info("Channels cleaned")
                bot.remove_cog("QueueManagerCog")
                logger.info("Queue Cog successfully unloaded from the bot")
                await ctx.channel.send("Queue cog successfully unloaded from the bot. I'm sorry it was annoying...")
        else:
            await ctx.channel.send("{author} does not have permission to use that function".format(author=ctx.author.name))


    @bot.command(name="save_player_data")
    async def save_data(ctx: commands.Context):
        if ctx.author.id == config.bot_admin_id:
            bot.save_players()

    bot.run(config.token)