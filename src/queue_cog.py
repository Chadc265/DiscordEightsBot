import discord
from discord.ext import commands
from typing import Dict, List, Tuple

from src.queue_bot import QueueBot
from src.match_queue_session import MatchQueue, QueueIdentifier, KickVote

class QueueManagerCog(commands.Cog):
    def __init__(self, bot:QueueBot):
        self.bot = bot
        self.match_queues: Dict[QueueIdentifier, MatchQueue] = {}

    @commands.command(
        name='n',
        help="Start a new queue. You must include the team size but the name of the game is optional",
        brief='Start a new queue')
    async def new_queue(self, ctx:commands.Context, team_size:int, *, game:str=None):
        guild_id = ctx.guild.id
        current_queues = self.get_current_guild_queues(guild_id)
        if len(current_queues) < 1:
            queue_id = QueueIdentifier(ctx=ctx)
            self.match_queues[queue_id] = MatchQueue(ctx=ctx, team_size=team_size, game=game)
            await ctx.channel.send("New {t}v{t} match queue for {g} started by {p}".format(g=game, t=team_size, p=ctx.author.name))
        else:
            await ctx.channel.send("Only one queue can be created at a time. Try resetting the old one")

    @commands.command(
        name='reset',
        help="Reset the queue after a match has completed. Specify new team size and game or it will use the same params as before. The current queue must be empty and queue-related channels vacated.",
        brief="Reset the queue when you're ready to go again",
        )
    async def reset_queue(self, ctx:commands.Context, team_size:int=None, *, game:str=None):
        guild_id = ctx.guild.id
        current_queues = self.get_current_guild_queues(guild_id)
        if len(current_queues) < 1:
            await ctx.channel.send("You gotta build something before you blow it up. There is not an active queue to reset.")
            return
        queue_id, queue = current_queues[0]
        if not queue.filled and len(queue.players) > 0:
            await ctx.channel.send("There is a queue already in progress with people in it. Please leave it instead of resetting. If someone went afk, try the 'kick' command")
            return

        if queue.voting_message_id is None and len(queue.players) > 0:
            await ctx.channel.send(
                'Previously queued players did not finish picking teams. I dont know how to handle this...')
            return

        if queue.team_1_vc is not None and queue.team_2_vc is not None:
            if len(queue.team_1_vc.members) > 0 or len(queue.team_2_vc.members) > 0:
                await ctx.channel.send("I'm kinda dumb right now, please vacate the team chat channels so I can be sure that match is complete.")
                return
        if ctx.channel.id == queue.voting_channel.id:
            await ctx.channel.send("This channel must be deleted to reset the queue. Please reset somewhere else")
            return

        await self.clean_up_queue_channels(ctx.guild)
        new_size = queue.team_size if team_size is None else team_size
        new_game = queue.game if game is None else game
        self.match_queues[queue_id] = MatchQueue(
            ctx=ctx,
            team_size=new_size,
            game=new_game)
        await ctx.channel.send("Queue has been cleared. Good to go again")

    @commands.command(
        name='kick',
        help="The first time this is called, it initiates the processes to kick {player_name} from the queue. {player_name} will be kicked when this is called by a second person",
        brief='Kick a person from the queue')
    async def kick_player(self, ctx:commands.Context, *, player_name):
        queue_id = QueueIdentifier(ctx=ctx)
        if queue_id in self.match_queues:
            queue = self.match_queues[queue_id]
            for p in queue.players:
                if p.discord_name == player_name:
                    if queue.kick_vote is None:
                        queue.kick_vote = KickVote(p)
                        await ctx.channel.send('Vote has been initiated to kick {p}. One more player is needed to complete the kick'.format(p=player_name))
                        return
                    else:
                        if queue.filled:
                            await ctx.channel.send(
                                "Voting already began before anyone noticed {p} was missing. Resetting the queue to empty. Blame {p}".format(p=player_name))
                            await self.clean_up_queue_channels(ctx.guild)
                            self.match_queues[queue_id] = MatchQueue(
                                ctx=ctx,
                                team_size=queue.team_size,
                                game=queue.game)
                            await ctx.channel.send("Queue has been cleared. Good to go again")
                            return
                        queue.remove_player(p)
                        queue.kick_vote = None
                        await ctx.channel.send('{p} has been kicked by the group'.format(p=player_name))
                        return
            await ctx.channel.send('{p} was not found in the queue. Check spelling/capitalization and try again. Make sure you are using this from a channel other than "pick-teams"'.format(p=player_name))


    @commands.command(name='leave', help="Leave the existing queue")
    async def leave_queue(self, ctx:commands.Context):
        queue_id = QueueIdentifier(ctx=ctx)
        if queue_id in self.match_queues:
            queue = self.match_queues[queue_id]
            player = await self.bot.get_player_from_db(ctx.author, ctx.guild.id, queue.game)
            _, leave_msg = await queue.try_remove_player(ctx, player)
            await ctx.channel.send(leave_msg)
            self.bot.save_players()
        else:
            await ctx.channel.send("No queue exists in this channel yet")

    @commands.command(name='q', help="Add yourself to the existing queue")
    async def queue(self, ctx:commands.Context):
        queue_id = QueueIdentifier(ctx=ctx)
        if queue_id in self.match_queues:
            queue = self.match_queues[queue_id]
            player = await self.bot.get_player_from_db(ctx.author, ctx.guild.id, queue.game)
            _, add_msg = await queue.try_add_player(ctx, player)
            await ctx.channel.send(add_msg)
            return

        if any([ctx.guild.id == k.guild_id for k,v in self.match_queues.items()]):
            queue_id, _ = self.get_current_guild_queues(ctx.guild.id)[0]
            channel = await self.bot.fetch_channel(queue_id.channel_id)
            await ctx.channel.send("This queue is being held in {channel}. Please head there and try again".format(channel=channel.name))
            return

        # handle make new queue

    @commands.command(name='rollcall', help="List the players that are in the current queue")
    async def number_players(self, ctx:commands.Context):
        guild_queues = self.get_current_guild_queues(ctx.guild.id)
        if len(guild_queues) > 0:
            for k,v in guild_queues:
                roll_call_msg = v.get_roll_call_message()
                await ctx.channel.send(roll_call_msg)


    @commands.command(name='go', help="Get moved to your assigned team chat. Will not work until teams have been chosen")
    async def go_to_team_chat(self, ctx:commands.Context):
        queue_id = QueueIdentifier(ctx=ctx)
        if queue_id not in self.match_queues:
            await ctx.channel.send("There must be a queue and team selection must be done before using this command")
            return
        queue = self.match_queues[queue_id]

        if queue.voting_message_id is not None:
            return
        if ctx.channel.name != queue.voting_channel.name:
            return
        if any([ctx.author.name == p.discord_name for p in queue.team_1]):
            await ctx.author.move_to(queue.team_1_vc)
        elif any([ctx.author.name == p.discord_name for p in queue.team_2]):
            await ctx.author.move_to(queue.team_2_vc)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member:discord.Member, _:discord.VoiceState, after:discord.VoiceState):
        # Roll call or earlier
        if after.channel is None:
            return
        guild_id = member.guild.id
        current_queues = self.get_current_guild_queues(guild_id)
        if len(current_queues) < 1:
            return
        queue_id, queue = current_queues[0]
        await queue.handle_relevant_voice_event(member, after)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        guild_id = payload.guild_id
        current_queues = self.get_current_guild_queues(guild_id)
        if len(current_queues) < 1:
            return
        queue_id, queue = current_queues[0]
        if not queue.filled:
            return
        elif queue.voting_message_id is None:
            return
        elif payload.message_id != queue.voting_message_id:
            return

        sending_user = await self.bot.fetch_user(payload.user_id)
        if queue.current_captain_name != sending_user.name:
            await queue.clear_add_reactions()
        else:
            await queue.handle_relevant_emote()

    def get_current_guild_queues(self, guild_id:int) -> List[Tuple[QueueIdentifier, MatchQueue]]:
        queues = [(k,v) for k,v in self.match_queues.items() if k.guild_id == guild_id]
        return queues

    def get_players_queues(self, member_id):
        queue_ids = []
        for k,v in self.match_queues:
            if any([x.discord_id == member_id for x in v.players]):
                queue_ids.append(k)
        return queue_ids


    # async def pick_teams(self):
    #     self.team_pick_session = MatchQueue(self.voting_channel, self.players)
    #     self._current_captain_name = await self.team_pick_session.choose_captains(False)
    #     await self.team_pick_session.begin_picking()

    @staticmethod
    async def clean_up_queue_channels(guild:discord.Guild):
        existing_cat:discord.CategoryChannel = discord.utils.find(lambda x: x.name == "Custom Games", guild.categories)
        if existing_cat is not None:
            channels = existing_cat.channels
            for channel in channels:
                try:
                    print(channel.name)
                    await channel.delete()
                except AttributeError:
                    pass
            await existing_cat.delete()







