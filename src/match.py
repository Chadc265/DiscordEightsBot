import random
import discord
from discord.ext import commands
from src.player import Player


class TeamPickSession:
    def __init__(self,
                 voting_channel:discord.TextChannel,
                 players:list[Player]):
        self.voting_channel = voting_channel
        self.players = players
        self.team_1 = []
        self.team_2 = []
        self.voting_message_id = None
        self.all_emojis = [ "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

    @property
    def remaining_players(self):
        return [x for x in self.players if not any([x in self.team_1, x in self.team_2])]
    @property
    def remaining_emojis(self):
        return self.all_emojis[0:len(self.remaining_players)]

    async def add_dummy_players(self, number=4):
        self.players.extend([Player(discord_name='Dummy Player {n}'.format(n=n)) for n in range(number)])


    async def choose_captains(self, add_dummies=False):
        random.shuffle(self.players)
        self.team_1.append(self.players[0])
        self.team_2.append(self.players[1])
        c1 = self.players[0].discord_name
        c2 = self.players[1].discord_name
        if add_dummies:
            await self.add_dummy_players(4)
        await self.voting_channel.send("The captains will be {cap1} and {cap2}. They will now pick teams".format(cap1=c1, cap2=c2))
        return c1

    async def begin_picking(self):
        if self.voting_message_id is None:
            msg_text = self.get_choice_message(self.players[0])
            msg = await self.voting_channel.send(content=msg_text)
            await self.clear_add_reactions(msg)
            self.voting_message_id = msg.id


    async def pick_next(self) -> str:
        message = await self.voting_channel.fetch_message(self.voting_message_id)
        # even number left, so c1 picks
        if len(self.remaining_emojis) % 2 == 0:
            # message.clear_reactions()
            msg_text = self.get_choice_message(self.players[0])
            await message.edit(content=msg_text)
            await self.clear_add_reactions()
            return self.players[0].discord_name
        else:
            # message.clear_reactions()
            msg_text = self.get_choice_message(self.players[1])
            await message.edit(content=msg_text)
            await self.clear_add_reactions()
            return self.players[1].discord_name


    async def handle_last_pick(self):
        message = await self.voting_channel.fetch_message(self.voting_message_id)
        if len(self.remaining_emojis) % 2 == 0:
            self.team_1.append(self.remaining_players[self.get_selected_reaction_index(message)])
        else:
            self.team_2.append(self.remaining_players[self.get_selected_reaction_index(message)])
        if len(self.remaining_players) == 0:
            await message.delete()
        return len(self.remaining_players) > 0


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
        players = self.remaining_players
        emojis = self.remaining_emojis

        txt_list = ["{p} = {em}".format(p=players[i].discord_name,em=emojis[i]) for i in list(range(len(players)))]
        txt = "{cap}, pick a player from the following choices\n".format(cap=captain.discord_name)
        return txt + "; ".join(txt_list)