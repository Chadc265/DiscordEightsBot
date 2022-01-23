
class Player:
    def __init__(self, **kwargs):
        self.discord_name = kwargs.get('discord_name', None)
        self.total_wins = kwargs.get('total_wins', 0)
        self.total_losses = kwargs.get('total_losses', 0)
        self.win_streak = kwargs.get('win_streak', 0)
        self.loss_streak = kwargs.get('loss_streak', 0)

    @property
    def matches_played(self):
        return self.total_losses + self.total_wins

    def __eq__(self, other):
        return self.discord_name == other.discord_name

    def log_win(self):
        self.loss_streak = 0
        self.win_streak += 1
        self.total_wins += 1

    def log_loss(self):
        self.loss_streak += 1
        self.win_streak = 0
        self.total_losses += 1
