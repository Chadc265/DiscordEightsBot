class PlayerIdentifier:
    def __init__(self, discord_id:int, guild_id:int, game:str):
        self.discord_id = discord_id
        self.guild_id = guild_id
        self.game = game

    def __hash__(self):
        return hash((self.guild_id, self.discord_id, self.game))

    def __eq__(self, other):
        return (self.discord_id, self.guild_id, self.game) == (other.discord_id, other.guild_id, other.game)

    def __ne__(self, other):
        return not(self == other)


class Player:
    def __init__(self, **kwargs):
        self.discord_name = kwargs.get('discord_name', None)
        self.display_name = kwargs.get('display_name', None)
        self.discord_id = kwargs.get('discord_id', None)
        self.guild_id = kwargs.get('guild_id', None)
        self.game = kwargs.get("game", None)
        self.total_wins = kwargs.get('total_wins', 0)
        self.total_losses = kwargs.get('total_losses', 0)
        self.win_streak = kwargs.get('win_streak', 0)
        self.loss_streak = kwargs.get('loss_streak', 0)
        self.current_queue_game = None

    @property
    def matches_played(self):
        return self.total_losses + self.total_wins

    def __hash__(self):
        return hash((self.discord_name, self.discord_id, self.guild_id, self.game))

    def __eq__(self, other):
        return (self.discord_name, self.discord_id, self.guild_id, self.game) == (other.discord_name, other.discord_id, other.guild_id, other.game)

    def __ne__(self, other):
        return not(self == other)


    def log_win(self):
        self.loss_streak = 0
        self.win_streak += 1
        self.total_wins += 1

    def log_loss(self):
        self.loss_streak += 1
        self.win_streak = 0
        self.total_losses += 1
