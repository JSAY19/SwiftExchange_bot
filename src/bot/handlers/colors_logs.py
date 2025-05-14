import colorlog
import logging

def get_user_display(user):
    if user.username:
        return f"https://t.me/{user.username}"
    else:
        return f"'{user.id}'"

class AlternatingColorFormatter(colorlog.ColoredFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._counter = 0

    def format(self, record):
        if record.levelname == "INFO":
            # Чередуем цвет: чётная — cyan, нечётная — green
            color = 'cyan' if self._counter % 2 == 0 else 'green'
            self.log_colors['INFO'] = color
            self._counter += 1
        return super().format(record)

handler = colorlog.StreamHandler()
handler.setFormatter(AlternatingColorFormatter(
    '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
    log_colors={
        'DEBUG':    'cyan',
        'INFO':     'green',   
        'WARNING':  'yellow',
        'ERROR':    'red',
        'CRITICAL': 'bold_red',
    }
))
logging.basicConfig(level=logging.DEBUG, handlers=[handler])