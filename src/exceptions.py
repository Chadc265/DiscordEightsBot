
class QueueBotException(Exception):
    def __init__(self, message):
        super().__init__(message)
        self._message = message

    @property
    def message(self):
        return self._message

class ConfigError(QueueBotException):
    def __init__(self, message_fmt, *, missing_file=None, missing_section=None, missing_key=None):
        if missing_key is not None and missing_file is None:
            return
        self._fmt = message_fmt
        self.missing_file = missing_file
        self.missing_section = missing_section
        self.missing_key = missing_key

    @property
    def message(self):
        if self.missing_file is not None:
            return self._fmt.format(file=self.missing_file)
        if self.missing_key is not None:
            return self._fmt.format(section=self.missing_section, key=self.missing_key)
        if self.missing_section is not None:
            return self._fmt.format(section=self.missing_section)

