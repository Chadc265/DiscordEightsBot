import discord
from discord.ext import commands
import json
import os
import typing
from src.player import Player

class QueueBot(commands.Bot):
    def __init__(self, *args, data_path:str, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_path = data_path
        self.players = self.load_saved_players()

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')


    async def get_player_by_author(self, author:typing.Union[discord.Member,discord.User]):
        if author.id in self.players:
            return self.players[author.id]
        else:
            new_player = Player(discord_name=author.name)
            self.players[author.id] = new_player
            print(vars(new_player))
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
