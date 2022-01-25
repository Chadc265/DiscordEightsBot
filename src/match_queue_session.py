import random
import typing
import discord
from discord.ext import commands
from typing import List, Tuple

from src.player import Player

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
        self.voting_channel: typing.Union[discord.TextChannel, None] = None
        self.roll_call_voice: typing.Union[discord.VoiceChannel, None] = None
        self.team_1_vc: typing.Union[discord.VoiceChannel, None] = None
        self.team_2_vc: typing.Union[discord.VoiceChannel, None] = None
        self.players: List[Player] = []
        self.team_1: List[Player] = []
        self.team_2: List[Player] = []
        self.voting_message_id:typing.Union[int,None] = None
        self.all_emojis: List[str] = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
        self.kick_vote = None

    @property
    def filled(self) -> bool:
        return len(self.players) == (self.team_size * 2)

    @property
    def unplaced_players(self) -> List[Player]:
        return [x for x in self.players if not any([x in self.team_1, x in self.team_2])]

    @property
    def remaining_emojis(self) -> List[str]:
        return self.all_emojis[0:len(self.unplaced_players)]

    @property
    def current_captain_name(self) -> str:
        if len(self.remaining_emojis) % 2 == 0:
            return self.players[0].discord_name
        else:
            return self.players[1].discord_name

    @property
    def waiting_for_roll_call(self) -> bool:
        if self.roll_call_voice is not None:
            return len(self.roll_call_voice.members) == self.team_size*2
        else:
            return False

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
        self.players.append(player)

    def remove_player(self, player:Player):
        if any(player == p for p in self.players):
            self.players.remove(player)

    async def try_add_player(self, ctx:commands.Context, player:Player) -> Tuple[bool, typing.Union[str]]:
        if self.filled:
            return True, "I'm a baby bot, I can only handle one queue at a time right now."
        if any([ctx.author.name == p.discord_name for p in self.players]):
            return False, "Hold your horses, you already joined the conga line"
        # if team_size is not None and len(self.players) == 0:
        #     self.team_size = team_size
        self.add_player(player)
        if self.filled:
            self.queue_category = await ctx.guild.create_category(self._get_category_name())
            self.voting_channel = await self.queue_category.create_text_channel("pick-teams")
            self.roll_call_voice = await self.queue_category.create_voice_channel("Roll Call")
            return True, "Queue has been filled! Head to Roll Call now!"
        return False, self._get_added_to_queue_msg(ctx.author.name)

    async def try_remove_player(self, ctx:commands.Context, player:Player) -> Tuple[bool, typing.Union[str]]:
        if self.filled:
            msg = 'Its too late, the queue filled. You messed up. Okay, mistakes happen... Just finish the voting and reset the queue because this situation is too complicated for me.'
            return False, msg
        if not any([x.discord_name == ctx.author.name for x in self.players]):
            msg = "LMAO YOU ARE TRYING TO QUIT AND YOU NEVER EVEN STARTED"
            return False, msg
        self.remove_player(player)
        return True, self._get_remove_from_queue_msg(ctx.author.name)

    def get_roll_call_message(self) -> str:
        player_list = '\n'.join([x.discord_name for x in self.players])
        if self.game is not None:
            return "{n} out of {n2} players so far for {g}.\n{players}".format(n=len(self.players), n2=self.team_size * 2,
                                                                            g=self.game,
                                                                            players=player_list)
        else:
            return "{n} out of {n2} players so far.\n{players}".format(n=len(self.players), n2=self.team_size * 2,
                                                                    players=player_list)

    # VC Handling
    async def remove_queue_channels(self):
        if self.queue_category is None:
            return
        await self.voting_channel.delete()
        await self.team_1_vc.delete()
        await self.team_2_vc.delete()
        await self.queue_category.delete()

    async def handle_relevant_voice_event(self, member:discord.Member, voice_state:discord.VoiceState):
        # roll call not started, or it has but Team vc not available
        if self.roll_call_voice is None:
            return

        if voice_state.channel.name == self.roll_call_voice.name:
            if len(self.roll_call_voice.members) == self.team_size * 2:
                await self.voting_channel.send("All parties account for...")
                await self.choose_captains(False)
                await self.begin_picking()
            return

        if any([self.team_1_vc is None, self.team_2_vc is None]):
            return

        if voice_state.channel.name == self.team_1_vc.name:
            if not any([member.name == p.discord_name for p in self.team_1]):
                await self.voting_channel.send(
                    "{name} tried to be a rat and join the wrong VC".format(name=member.name))
                await member.move_to(self.roll_call_voice)
            else:
                players_in_vc = len(self.team_1_vc.members) + len(self.team_2_vc.members)
                await self.voting_channel.send(
                    "{n} out of {t} players have found the Team Chats!".format(n=players_in_vc, t=self.team_size*2))

        elif voice_state.channel.name == self.team_2_vc.name:
            if not any([member.name == p.discord_name for p in self.team_2]):
                await self.voting_channel.send(
                    "{name} tried to be a rat and join the wrong VC".format(name=member.name))
                await member.move_to(self.roll_call_voice)
            else:
                players_in_vc = len(self.team_1_vc.members) + len(self.team_2_vc.members)
                await self.voting_channel.send(
                    "{n} out of {t} players have found the Team Chats!".format(n=players_in_vc, t=self.team_size*2))

        if len(self.team_1_vc.members) == self.team_size and len(self.team_2_vc.members) == self.team_size:
            await self.voting_channel.send("Match can begin!")
            await self.roll_call_voice.delete()
            self.roll_call_voice = None

    async def handle_relevant_emote(self):
        if await self.handle_last_pick():
            await self.pick_next()
        else:
            team1 = ", ".join([x.discord_name for x in self.team_1])
            team2 = ", ".join([x.discord_name for x in self.team_2])
            await self.voting_channel.send("Team 1: {t1}".format(t1=team1))
            await self.voting_channel.send("Team 2: {t2}".format(t2=team2))
            self.team_1_vc = await self.queue_category.create_voice_channel("Team 1 Chat")
            self.team_2_vc = await self.queue_category.create_voice_channel("Team 2 Chat")
            self.voting_message_id = None

    async def choose_captains(self, add_dummies=False):
        random.shuffle(self.players)
        self.team_1.append(self.players[0])
        self.team_2.append(self.players[1])
        c1 = self.players[0].discord_name
        c2 = self.players[1].discord_name
        if add_dummies:
            await self.add_dummy_players(4)
        await self.voting_channel.send("The captains will be {cap1} and {cap2}\n".format(cap1=c1, cap2=c2))
        return c1

    async def begin_picking(self):
        if self.voting_message_id is None:
            msg_text = self.get_choice_message(self.players[0])
            msg = await self.voting_channel.send(content=msg_text)
            await self.clear_add_reactions(msg)
            self.voting_message_id = msg.id


    async def pick_next(self):
        message = await self.voting_channel.fetch_message(self.voting_message_id)
        # even number left, so c1 picks
        if len(self.remaining_emojis) % 2 == 0:
            # message.clear_reactions()
            msg_text = self.get_choice_message(self.players[0])
            await message.edit(content=msg_text)
            await self.clear_add_reactions()
        else:
            # message.clear_reactions()
            msg_text = self.get_choice_message(self.players[1])
            await message.edit(content=msg_text)
            await self.clear_add_reactions()


    async def handle_last_pick(self):
        message = await self.voting_channel.fetch_message(self.voting_message_id)
        if len(self.remaining_emojis) % 2 == 0:
            self.team_1.append(self.unplaced_players[self.get_selected_reaction_index(message)])
        else:
            self.team_2.append(self.unplaced_players[self.get_selected_reaction_index(message)])
        if len(self.unplaced_players) == 0:
            await message.delete()
        return len(self.unplaced_players) > 0


    @staticmethod
    def get_selected_reaction_index(message:discord.Message):
        for i in list(range(len(message.reactions))):
            if message.reactions[i].count > 1:
                return i

    async def clear_add_reactions(self, msg=None):
        if msg is not None:
            await msg.clear_reactions()
            for em in self.remaining_emojis:
                await msg.add_reaction(em)
        else:
            msg = await self.voting_channel.fetch_message(self.voting_message_id)
            await msg.clear_reactions()
            for em in self.remaining_emojis:
                await msg.add_reaction(em)

    def get_choice_message(self, captain):
        players = self.unplaced_players
        emojis = self.remaining_emojis

        txt_list = ["{p} = {em}".format(p=players[i].discord_name,em=emojis[i]) for i in list(range(len(players)))]
        txt = "{cap}, pick a player from the following choices\n".format(cap=captain.discord_name)
        return txt + "; ".join(txt_list)