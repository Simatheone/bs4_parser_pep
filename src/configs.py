import argparse
import logging
from logging.handlers import RotatingFileHandler

from constants import BASE_DIR, LOG_DT_FORMAT, LOG_FORMAT


def configure_argument_parser(available_modes):
    """Function creates argument parser for command line.
    Sets modes, commands for running the parser.
    Function chooses modes from "available_modes".
    Commands:
        -c  - for clearing cache;
        -o  - the ways result of parsing can be presented.
              Choices:
                - pretty (as table in terminal);
                - file (as a file saved in directory "results/")
    """
    parser = argparse.ArgumentParser(description='Парсер документации Python')
    parser.add_argument(
        'mode',
        choices=available_modes,
        help='Режимы работы парсера'
    )
    parser.add_argument(
        '-c',
        '--clear-cache',
        action='store_true',
        help='Очистка кеша'
    )
    parser.add_argument(
        '-o',
        '--output',
        choices=('pretty', 'file'),
        help='Дополнительные способы вывода данных'
    )
    return parser


def configure_logging():
    """Function sets configuration for logger.
    Creates:
        - directory for saving logs and .log file.
    Sets:
        - settings for rotating handler;
        - log date format, log format, level and handlers
          for logger config.
    """
    log_dir = BASE_DIR / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'parser.log'

    rotating_handler = RotatingFileHandler(
        log_file, maxBytes=10 ** 6, backupCount=5
    )
    logging.basicConfig(
        datefmt=LOG_DT_FORMAT,
        format=LOG_FORMAT,
        level=logging.INFO,
        handlers=(rotating_handler, logging.StreamHandler())
    )
