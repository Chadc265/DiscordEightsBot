import logging
import typing
import discord
from discord.ext import commands
from typing import List, Tuple

from src.player import Player
from src.embeds import EmbeddedRollCall, EmbeddedPicker

log = logging.getLogger(__name__)

class QueueProgress:
    def __init__(self):
        self.empty = True
        self.filled = False
        self.vote_in_progress = False
        self.vote_complete = False
        self.ready_to_start = False
        self.errored = False

class QueueIdentifier:
    def __init__(self, **kwargs):
        assert 'ctx' in kwargs or ('guild_id' in kwargs and 'channel_id' in kwargs)
        ctx:commands.Context = kwargs.get('ctx', None)
        guild_id:int = kwargs.get('guild_id', ctx.guild.id)
        channel_id:int = kwargs.get('channel_id', ctx.channel.id)
        self.game = kwargs.get('game', None)
        self.guild_id = guild_id
        self.channel_id = channel_id

    def __hash__(self):
        return hash((self.channel_id, self.guild_id, self.game))

    def __eq__(self, other):
        return (self.channel_id, self.guild_id, self.game) == (other.channel_id, other.guild_id, self.game)

    def __ne__(self, other):
        return not(self == other)

    def __str__(self):
        return '{gid} - {cid} - {g}'.format(gid=self.guild_id, cid=self.channel_id, g=self.game)

class KickVote:
    def __init__(self, player):
        self.target = player
        self.vote_count = 1

    @property
    def accepted(self):
        return self.vote_count > 1

class MatchQueue:
    def __init__(self,
                 ctx:commands.Context=None,
                 team_size:int=4,
                 game:typing.Union[str, None]=None):
        self.queue_id:QueueIdentifier = QueueIdentifier(ctx=ctx)

        self.game:typing.Union[str, None] = game
        self.team_size:int = team_size
        self.queue_category: typing.Union[discord.CategoryChannel, None] = None
        self.team_1_vc: typing.Union[discord.VoiceChannel, None] = None
        self.team_2_vc: typing.Union[discord.VoiceChannel, None] = None
        self.voting_channel: typing.Union[discord.TextChannel, None] = None
        self.players: List[Player] = []
        self.team_1: List[Player] = []
        self.team_2: List[Player] = []

        self.progress = QueueProgress()
        self.kick_vote = None


    def is_player_queued(self, player_id:str) -> bool:
        return any([x.discord_id == player_id for x in self.players])


    async def add_dummy_players(self, number=4):
        self.players.extend([Player(discord_name='Dummy Player {n}'.format(n=n)) for n in range(number)])

    # queue building
    def _get_added_to_queue_msg(self, author_name) -> str:
        ppl = "people" if len(self.players) != 1 else "person"
        if self.game is not None:
            msg = "{p} Added to {g} Queue! {n} {ppl} so far!".format(p=author_name,
                                                                     g=self.game,
                                                                     n=len(self.players),
                                                                     ppl=ppl)
        else:
            msg = "{p} Added to Queue! {n} {ppl} so far!".format(p=author_name,
                                                                 n=len(self.players),
                                                                 ppl=ppl)
        return msg

    def _get_remove_from_queue_msg(self, author_name) -> str:
        if self.game is not None:
            msg = '{p} has left the {g} queue. {n} remain'.format(p=author_name, g=self.game, n=len(self.players))
        else:
            msg = '{p} has left the queue. {n} remain'.format(p=author_name,n=len(self.players))
        return msg

    @staticmethod
    def _get_category_name() -> str:
        return "Custom Games"
        # if self.game is not None:
        #     return "{g} Customs".format(g=self.game)
        # else:
        #     return "Custom Games"

    def add_player(self, player:Player):
        self.progress.empty = False
        self.players.append(player)
        self.progress.filled = len(self.players) == self.team_size * 2

    def remove_player(self, player:Player):
        if any(player == p for p in self.players):
            self.players.remove(player)
        self.progress.empty = len(self.players) == 0
        self.progress.filled = len(self.players) == self.team_size * 2

    async def try_add_player(self, ctx:commands.Context, player:Player) -> Tuple[bool, typing.Union[str]]:
        if self.progress.filled:
            return True, "This queue has been filled. I'm a baby bot, so I can't just make a new one all willy-nilly yet."
        if any([ctx.author.id == p.discord_id for p in self.players]):
            return False, "Hold your horses, you already joined the conga line"
        self.add_player(player)
        if self.progress.filled:
            return True, "Queue has been filled! Roll call will start soon!"
        return False, self._get_added_to_queue_msg(ctx.author.display_name)

    async def try_add_fake(self, player:Player):
        if self.progress.filled:
            return True, "This queue has been filled. I'm a baby bot, so I can't just make a new one all willy-nilly yet."
        if any([player.discord_name == p.discord_name for p in self.players]):
            return False, "Hold your horses, you already joined the conga line"
        self.add_player(player)
        if self.progress.filled:
            return True, "Queue has been filled! Roll call will start soon!"
        return False, self._get_added_to_queue_msg(player.display_name)

    async def try_remove_player(self, ctx:commands.Context, player:Player) -> Tuple[bool, typing.Union[str]]:
        if self.progress.filled:
            msg = 'Its too late, the queue filled. You messed up. Okay, mistakes happen... Just finish the voting and reset the queue because this situation is too complicated for me.'
            return False, msg
        if not any([x.discord_id == ctx.author.id for x in self.players]):
            msg = "LMAO YOU ARE TRYING TO QUIT AND YOU NEVER EVEN STARTED"
            return False, msg
        self.remove_player(player)
        return True, self._get_remove_from_queue_msg(ctx.author.display_name)

    async def do_roll_call_and_pick_teams(self, ctx:commands.Context, testing=False):
        self.voting_channel = ctx.channel
        rollcall:EmbeddedRollCall = EmbeddedRollCall(self.players, timeout=300, testing=testing)
        log.info("Starting rollcall")
        self.progress.vote_in_progress = await rollcall.send_message(ctx)
        if self.progress.vote_in_progress:
            log.info("Rollcall successfully completed")
            pick_team:EmbeddedPicker = EmbeddedPicker(self.players, timeout=300, testing=testing)
            log.info("Starting team picking")
            self.progress.vote_complete = await pick_team.send_message(ctx)
            if self.progress.vote_complete:
                self.team_1 = pick_team.team_1
                self.team_2 = pick_team.team_2
                log.info("Teams successfully chosen")
            return self.progress.vote_complete
        return self.progress.vote_in_progress

        # self.queue_category = await ctx.guild.create_category(self._get_category_name())

    def get_roll_call_message(self) -> discord.Embed:
        player_list = '\n'.join([x.display_name for x in self.players])

        if self.game is not None:
            title = "{n} out of {n2} players so far for {g}".format(
                n=len(self.players),
                n2=self.team_size * 2,
                g=self.game)
        else:
            title = "{n} out of {n2} players so far".format(
                n=len(self.players),
                n2=self.team_size * 2)

        return discord.Embed(title=title, description=player_list)

    # VC Handling
    async def remove_queue_channels(self):
        if self.queue_category is None:
            return
        await self.team_1_vc.delete()
        await self.team_2_vc.delete()
        await self.queue_category.delete()

    async def add_voice_channels(self, ctx:commands.Context):
        if self.queue_category is None:
            self.queue_category = await ctx.guild.create_category(self._get_category_name())
            self.team_1_vc = await self.queue_category.create_voice_channel(self.team_1[0].display_name)
            self.team_2_vc = await self.queue_category.create_voice_channel(self.team_2[0].display_name)

    async def handle_relevant_voice_event(self, member:discord.Member, before:discord.VoiceState, voice_state:discord.VoiceState):
        log.info("Voice event being handled by queue_session %s", self.queue_id)
        # Teams haven't been pick yet, not reason to pay attention
        if not self.progress.vote_complete:
            return

        # If vote is done, check if someone joined a team chat.
        if self.progress.vote_complete and not self.progress.ready_to_start:
            if voice_state.channel.id == self.team_1_vc.id:
                if not any([member.id == p.discord_id for p in self.team_1]):
                    await self.voting_channel.send(
                        "{name} tried to be a rat and join the wrong VC".format(name=member.display_name))
                    await member.move_to(before.channel)
                else:
                    players_in_vc = len(self.team_1_vc.members) + len(self.team_2_vc.members)
                    await self.voting_channel.send(
                        "{n} out of {t} players have found the Team Chats!".format(n=players_in_vc,
                                                                                   t=self.team_size * 2))

            elif voice_state.channel.id == self.team_2_vc.id:
                if not any([member.id == p.discord_id for p in self.team_2]):
                    await self.voting_channel.send(
                        "{name} tried to be a rat and join the wrong VC".format(name=member.display_name))
                    await member.move_to(before.channel)
                else:
                    players_in_vc = len(self.team_1_vc.members) + len(self.team_2_vc.members)
                    await self.voting_channel.send(
                        "{n} out of {t} players have found the Team Chats!".format(n=players_in_vc,
                                                                                   t=self.team_size * 2))

        if len(self.team_1_vc.members) == self.team_size and len(self.team_2_vc.members) == self.team_size:
            await self.voting_channel.send("Match can begin!")
            self.progress.ready_to_start = True