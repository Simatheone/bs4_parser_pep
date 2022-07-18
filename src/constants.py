from pathlib import Path

BASE_DIR = Path(__file__).parent
MAIN_DOC_URL = 'https://docs.python.org/3/'
PEP_CATALOG = 'https://peps.python.org/'
DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'
LOG_FORMAT = '"%(asctime)s - [%(levelname)s] - %(message)s"'
LOG_DT_FORMAT = '%d.%m.%Y %H:%M:%S'
EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred',),
    'F': ('Final',),
    'P': ('Provisional',),
    'R': ('Rejected',),
    'S': ('Superseded',),
    'W': ('Withdrawn',),
    '': ('Draft', 'Active'),
}
WHATS_NEW_TABLE_HEADER = ('Ссылка на статью', 'Заголовок', 'Редактор, Автор')
LATEST_VERSION_TABLE_HEADER = ('Ссылка на документацию', 'Версия', 'Статус')
PEP_TABLE_HEADER = ('Статус', 'Количество')
