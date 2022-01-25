import configparser
import os

from src.exceptions import ConfigError

class BotConfig:
    def __init__(self, config_path='data/config.ini'):
        self.path = config_path
        config = self._read_config()
        self.token = config.get('credentials', 'QueueBot_token', fallback=ConfigDefaults.token)
        self._check_token()
        self.bot_admin_id = config.get('permissions', 'bot_admin_id', fallback=ConfigDefaults.bot_admin_id)
        self.player_data_path = config.get('paths', 'player_data', fallback=ConfigDefaults.player_data_path)


    def _config_exists(self) -> bool:
        return os.path.isfile(self.path)

    def _read_config(self) -> configparser.ConfigParser():
        config = configparser.ConfigParser()
        if not self._config_exists():
            config['credentials'] = {}
            config['credentials']['QueueBot_token'] = ConfigDefaults.token
            config['permissions'] = {}
            config['permissions']['bot_admin_id'] = ConfigDefaults.bot_admin_id
            config['paths'] = {}
            config['paths']['player_data'] = ConfigDefaults.player_data_path
            with open(self.path, 'w') as f:
                config.write(f)
            raise ConfigError("Config file, {file}, did not exist. It has been created, please fill it out accordingly.")
        else:
            config = configparser.ConfigParser()
            config.read(self.path)

        self._check_sections(config)
        return config

    @staticmethod
    def _check_sections(config):
        sections = ['credentials', 'permissions', 'paths']
        for s in sections:
            if not config.has_section(s):
                raise ConfigError("{section} does not exist in the config file provided. Please add it",
                                  missing_section=s)

    def _check_token(self):
        if not self.token:
            raise ConfigError(
                "The {section} section in the config file did not contain the key, {key}. Please add this key with your token",
                missing_section="credentials",
                missing_key="QueueBot_token")

class ConfigDefaults:
    token = None
    bot_admin_id = None
    player_data_path = 'data/players.json'