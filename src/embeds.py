import asyncio
import logging
import random
import time
from typing import List
import discord
from discord.ext import commands

from src.player import Player

log = logging.getLogger(__name__)

class EmbeddedRollCall:
    def __init__(self, players:List[Player], timeout:int=300, testing=False):
        self.testing=testing
        self.players = players
        self.timeout:int = timeout
        self.presence_dict = {x.display_name: "Missing" for x in self.players}
        if self.testing:
            self.presence_dict = self._make_fakes_present()
        self.page:discord.Embed = self._get_rollcall_page()
        self.good_to_go = False

    @property
    def all_present(self):
        return all([v == 'Present' for k,v in self.presence_dict.items()])

    async def send_message(self, ctx:commands.Context):
        msg:discord.Message = await ctx.channel.send(embed=self.page)
        wait_for_players = True
        bot: commands.Bot = ctx.bot
        time_started = time.time()
        running_timeout = self.timeout
        while wait_for_players:
            try:
                def check_reaction(payload:discord.RawReactionActionEvent):
                    if payload.user_id != bot.user.id and msg.id == payload.message_id:
                        return True
                payload:discord.RawReactionActionEvent = await bot.wait_for(
                    "raw_reaction_add", timeout=running_timeout, check=check_reaction
                )

                running_timeout -= int(time.time() - time_started)
                responding_player:Player = self.get_player_from_id(payload.user_id)
                if responding_player is not None:
                    self.presence_dict[responding_player.display_name] = "Present"
                    embed = self._get_rollcall_page()
                    await msg.edit(embed=embed)
                else:
                    await msg.reactions.remove(payload.emoji)

                if self.all_present:
                    wait_for_players = False
                    return True

            except asyncio.TimeoutError:
                wait_for_players = False
        await ctx.channel.send('Roll call has timed out because someone did not show. Queue will reset now...')
        return False

    def _get_rollcall_page(self):
        description = 'Everyone must be preset before we pick teams'
        footer = 'React with any emoji when you are ready'
        embed:discord.Embed = discord.Embed(title='Roll Call', description=description)
        embed.set_footer(text=footer)
        for k,v in self.presence_dict.items():
            embed.add_field(name=k, value=v)
        return embed

    def _make_fakes_present(self):
        ret = {}
        for p in self.players:
            if p.discord_id is None:
                ret[p.display_name] = "Present"
            else:
                ret[p.display_name] = 'Missing'
        return ret

    def get_player_from_id(self, player_id):
        for p in self.players:
            if p.discord_id == player_id:
                return p
        return None

class EmbeddedPicker:
    def __init__(self, players:List[Player], timeout=300, testing=False):
        self.testing = testing
        self.players = players
        self.timeout = timeout
        self.all_emojis: List[str] = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
        self.team_1 = []
        self.team_2 = []
        self.choose_captains()

    @property
    def team_1_field_value(self):
        return '\n'.join([x.display_name for x in self.team_1])

    @property
    def team_2_field_value(self):
        return '\n'.join([x.display_name for x in self.team_2])

    @property
    def unplaced_players(self) -> List[Player]:
        return [x for x in self.players if not any([x in self.team_1, x in self.team_2])]

    @property
    def remaining_emojis(self) -> List[str]:
        return self.all_emojis[0:len(self.unplaced_players)]

    async def send_message(self, ctx:commands.Context):
        embed:discord.Embed = self._get_page(self.team_1[0].display_name)
        msg:discord.Message = await ctx.channel.send(embed=embed)
        bot: commands.Bot = ctx.bot
        time_started = time.time()
        running_timeout = self.timeout
        blame_captain = None
        while blame_captain is None:
            await self._clear_add_reactions(msg)
            current_captain, current_team = (self.team_1[0], 1) if len(self.remaining_emojis) % 2 == 0 else (
            self.team_2[0], 2)
            try:
                def check_reaction(payload: discord.RawReactionActionEvent):
                    if payload.user_id == current_captain.discord_id and msg.id == payload.message_id:
                        return True

                payload: discord.RawReactionActionEvent = await bot.wait_for(
                    "raw_reaction_add", timeout=running_timeout, check=check_reaction
                )

                running_timeout -= int(time.time() - time_started)
                selected_player_index = self.remaining_emojis.index(payload.emoji.name)
                if current_team == 1:
                    self.team_1.append(self.unplaced_players[selected_player_index])
                else:
                    self.team_2.append(self.unplaced_players[selected_player_index])


                if len(self.unplaced_players) < 1:
                    await msg.edit(embed=self._get_final_page())
                    return True
                else:
                    if current_team == 1:
                        await msg.edit(embed=self._get_page(self.team_2[0].display_name))
                    else:
                        await msg.edit(embed=self._get_page(self.team_1[0].display_name))

            except asyncio.TimeoutError:
                blame_captain = current_captain
        await ctx.channel.send('Team picking has timed out because {c} could not make a decision. The queue will be reset'.format(c=blame_captain))


    async def _clear_add_reactions(self, msg:discord.Message):
        await msg.clear_reactions()
        for em in self.remaining_emojis:
            await msg.add_reaction(em)

    def choose_captains(self):
        if not self.testing:
            random.shuffle(self.players)

        self.team_1.append(self.players[0])
        self.team_2.append(self.players[1])

    def _get_page(self, captain):
        description = 'The captains are picking their teams now'
        footer = '{c} should react with the player they wish to pick'.format(c=captain)
        embed:discord.Embed = discord.Embed(title='Choose Teams', description=description)
        embed.set_footer(text=footer)
        embed.add_field(
            name='Team {c1}'.format(c1=self.team_1[0].display_name),
            value=self.team_1_field_value,
            inline=True)
        embed.add_field(
            name='Team {c2}'.format(c2=self.team_2[0].display_name),
            value=self.team_2_field_value,
            inline=True)

        players = self.unplaced_players
        emojis = self.remaining_emojis
        txt_list = ["{em} -> {p}".format(p=players[i].display_name,em=emojis[i]) for i in list(range(len(players)))]
        embed.add_field(name="Player Pool", value='\n'.join(txt_list), inline=False)
        return embed

    def _get_final_page(self):
        description = 'Head to your team chats once they are available'
        # footer = 'Good luck or something'
        embed: discord.Embed = discord.Embed(title='Chosen Teams', description=description)
        embed.add_field(
            name='Team {c1}'.format(c1=self.team_1[0].display_name),
            value=self.team_1_field_value,
            inline=True)
        embed.add_field(
            name='Team {c2}'.format(c2=self.team_2[0].display_name),
            value=self.team_2_field_value,
            inline=True)
        return embed