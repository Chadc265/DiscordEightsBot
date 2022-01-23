import discord
from discord.ext import commands
import typing
from src.player import Player
from src.eights_bot import QueueBot
from src.match import TeamPickSession

class EightsCog(commands.Cog):
    def __init__(self, bot:QueueBot, team_size:int=4, game:str=None):
        self.bot = bot
        self.game = game
        self.players = []
        self.team_size = team_size
        self.team_pick_session = None
        self.queue_category: typing.Union[discord.CategoryChannel,None] = None
        self.voting_channel: typing.Union[discord.TextChannel,None] = None
        self.roll_call_voice: typing.Union[discord.VoiceChannel,None] = None
        self.team_1_vc: typing.Union[discord.VoiceChannel,None] = None
        self.team_2_vc: typing.Union[discord.VoiceChannel,None] = None
        self._current_captain_name = None

    @property
    def filled(self):
        return len(self.players) == (self.team_size * 2)


    @commands.command(name='reset', help="Reset the queue after a match has completed.")
    async def reset_queue(self, ctx:commands.Context, *, new_game:str = None):
        if len(self.team_1_vc.members) > 0 or len(self.team_2_vc.members) > 0:
            await ctx.channel.send("I'm kinda dumb right now, please vacate the team chat channels so I can be sure that match is complete.")
            return
        if self.team_pick_session is None:
            await ctx.channel.send("There is a queue already in progress. Please leave it instead of resetting")
            return
        if self.team_pick_session.voting_message_id is not None:
            await ctx.channel.send('Previously queued players did not finish picking teams. I dont know how to handle this...')
            return
        # await self.voting_channel.edit(name="Empty Queue")
        self.players = []
        self.team_pick_session = None
        self.bot.save_players()
        if new_game is not None:
            self.game = new_game
        await ctx.channel.send("Queue has been cleared. Good to go again")

    @commands.command(name='leave', help="Leave the existing queue")
    async def leave_queue(self, ctx:commands.Context):
        if self.filled:
            await ctx.channel.send('Its too late, the queue filled. You messed up. Okay, mistakes happen... Just finish the voting and reset the queue because this situation is too complicated for me.')
            return
        if not any([x.discord_name == ctx.author.name for x in self.players]):
            await ctx.channel.send("LMAO YOU ARE TRYING TO QUIT AND YOU NEVER EVEN STARTED")
            return
        await self.remove_player(await self.bot.get_player_by_author(ctx.author))
        await ctx.channel.send('{p} has left the queue. {n} remain'.format(p=ctx.author.name,n=len(self.players)))

    @commands.command(name='q', help="Add the existing queue")
    async def queue(self, ctx:commands.Context):
        if self.filled:
            await ctx.channel.send("I'm a baby bot, I can only handle one queue at a time right now.")
            return
        if any([ctx.author.name == p.discord_name for p in self.players]):
            await ctx.channel.send("Hold your horses, you already joined the conga line")
            return
        # if team_size is not None and len(self.players) == 0:
        #     self.team_size = team_size
        await self.add_player(await self.bot.get_player_by_author(ctx.author))
        ppl = "people" if len(self.players) != 1 else "person"
        await ctx.channel.send("{p} Added to Queue! {n} {ppl} so far!".format(p=ctx.author.name,
                                                                              n=len(self.players),
                                                                              ppl=ppl))
        self.bot.save_players()
        if self.filled:
            await ctx.channel.send("Queue has been filled! Head to Roll Call now!")
            self.queue_category = await ctx.guild.create_category("Customs Queue")
            self.voting_channel = await self.queue_category.create_text_channel("pick-teams")
            self.roll_call_voice = await self.queue_category.create_voice_channel("Roll Call")
            # await self.voting_channel.edit(name="4v4 Filled!")
            # print("Changed name to 4v4 filled!")

    @commands.command(name='rollcall', help="List players in queue")
    async def number_players(self, ctx:commands.Context):
        player_list = '\n'.join([x.discord_name for x in self.players])
        if self.game is not None:
            await ctx.channel.send(
                "{n} out of {n2} players so far for {g}.\n{players}".format(n=len(self.players), n2=self.team_size * 2,
                                                                            g=self.game,
                                                                            players=player_list))
        else:
            await ctx.channel.send(
                "{n} out of {n2} players so far.\n{players}".format(n=len(self.players), n2=self.team_size * 2,
                                                                    players=player_list))


    @commands.command(name='go', help="Get moved to your assigned team chat. Will not work until teams have been chosen")
    async def go_to_team_chat(self, ctx:commands.Context):
        if self.team_pick_session is None:
            return
        if self.team_pick_session.voting_message_id is not None:
            return
        if ctx.channel.name != self.voting_channel.name:
            return
        if any([ctx.author.name == p.discord_name for p in self.team_pick_session.team_1]):
            await ctx.author.move_to(self.team_1_vc)
        elif any([ctx.author.name == p.discord_name for p in self.team_pick_session.team_2]):
            await ctx.author.move_to(self.team_2_vc)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, before:discord.VoiceState, after:discord.VoiceState):
        # Roll call or earlier
        if after.channel is None:
            return
        if self.roll_call_voice is None:
            return
        if after.channel.name == self.roll_call_voice.name:
            if len(self.roll_call_voice.members) == self.team_size*2:
                await self.voting_channel.send("All parties account for...")
                await self.pick_teams()
                return
        if self.team_pick_session is None:
            return

        if self.team_1_vc is None:
            return
        if self.team_2_vc is None:
            return
        if after.channel.name == self.team_1_vc.name:
            if not any([member.name == p.discord_name for p in self.team_pick_session.team_1]):
                await self.voting_channel.send("{name} tried to be a rat and join the wrong VC".format(name=member.name))
                await member.move_to(None)
        elif after.channel.name == self.team_2_vc.name:
            if not any([member.name == p.discord_name for p in self.team_pick_session.team_2]):
                await self.voting_channel.send("{name} tried to be a rat and join the wrong VC".format(name=member.name))
                await member.move_to(None)

        if len(self.team_1_vc.members) == self.team_size and len(self.team_2_vc.members) == self.team_size:
            await self.voting_channel.send("Match can begin!")
            await self.roll_call_voice.delete()
            self.roll_call_voice = None

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        sending_user = await self.bot.fetch_user(payload.user_id)
        if self.team_pick_session is None:
            return
        elif self.team_pick_session.voting_message_id is None:
            return
        elif payload.message_id != self.team_pick_session.voting_message_id:
            return
        elif payload.user_id == self.bot.user.id:
            return
        elif self._current_captain_name != sending_user.name:
            await self.team_pick_session.clear_add_reactions()
        else:
            if await self.team_pick_session.handle_last_pick():
                self._current_captain_name = await self.team_pick_session.pick_next()
            else:
                team1 = ", ".join([x.discord_name for x in self.team_pick_session.team_1])
                team2 = ", ".join([x.discord_name for x in self.team_pick_session.team_2])
                await self.team_pick_session.voting_channel.send("Team 1: {t1}".format(t1=team1))
                await self.team_pick_session.voting_channel.send("Team 2: {t2}".format(t2=team2))
                self.team_1_vc = await self.queue_category.create_voice_channel("Team 1 Chat")
                self.team_2_vc = await self.queue_category.create_voice_channel("Team 2 Chat")
                self.team_pick_session.voting_message_id = None
                self._current_captain_name = None

    async def pick_teams(self):
        self.team_pick_session = TeamPickSession(self.voting_channel, self.players)
        self._current_captain_name = await self.team_pick_session.choose_captains(False)
        await self.team_pick_session.begin_picking()

    async def initialize_queue_channels(self, guild:discord.Guild):
        existing_cat:discord.CategoryChannel = discord.utils.find(lambda x: x.name == "Customs Queue", guild.categories)
        if existing_cat is not None:
            channels = existing_cat.channels
            for channel in channels:
                try:
                    print(channel.name)
                    await channel.delete()
                except AttributeError:
                    pass
            await existing_cat.delete()
        if self.queue_category is not None:
            return



    async def remove_queue_channels(self):
        if self.queue_category is None:
            return
        await self.voting_channel.delete()
        await self.team_1_vc.delete()
        await self.team_2_vc.delete()
        await self.queue_category.delete()

    async def add_player(self, player:Player):
        # queue filled or player already in queue
        self.players.append(player)
        # await self.voting_channel.edit(name="{number_queued} of {size}".format(
        #     number_queued=len(self.players), size=self.team_size*2))

    async def remove_player(self, player:Player):
        if any(player == p for p in self.players):
            self.players.remove(player)
            # await self.voting_channel.edit(name="{number_queued} of {size}".format(
            #     number_queued=len(self.players), size=self.team_size * 2))



