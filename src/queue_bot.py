import discord
from discord.ext import commands
import json
import os
import typing

from typing import Dict

from src.player import Player, PlayerIdentifier

class QueueBot(commands.Bot):
    def __init__(self, *args, data_path:str, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_path = data_path
        self.players: Dict[PlayerIdentifier, Player] = self.load_saved_players()

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')


    async def get_player_from_db(self,
                                 author:typing.Union[discord.Member,discord.User],
                                 guild_id:int,
                                 game:typing.Union[str, None]):
        # player_id = PlayerIdentifier(author.id, guild_id, game)
        player_id = author.id
        if player_id in self.players:
            return self.players[player_id]
        else:
            new_player = Player(discord_name=author.name, display_name=author.display_name, discord_id=author.id, guild_id=guild_id)
            self.players[player_id] = new_player
            print(vars(new_player))
            return new_player

    @staticmethod
    def get_fake_player(fake_name, fake_display_name, guild_id):
        new_player = Player(discord_name=fake_name, display_name=fake_display_name, discord_id=None, guild_id=guild_id)
        return new_player

    def load_saved_players(self):
        player_dict = {}
        if os.path.exists(self.data_path):
            with open(self.data_path, 'r') as f:
                player_dict = json.load(f)
        players = {k: Player(**v) for k,v in player_dict.items()}
        return players

    def save_players(self):
        print(self.players)
        with open(self.data_path, 'w') as f:
            json.dump({k: vars(v) for k,v in self.players.items()}, f)
