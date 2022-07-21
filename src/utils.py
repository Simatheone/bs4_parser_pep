import logging
from requests import RequestException

from exceptions import ParserFindTagException


def get_response(session, url):
    """Function makes request to url.
    If response has been got returns it.
    Otherwise raises RequestException and writes
    information in logs, log level exception.
    """
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        return response
    except RequestException:
        logging.exception(
            f'Возникла ошибка при загрузке страницы {url}',
            stack_info=True
        )


def find_tag(soup, tag, attrs=None):
    """Function looks for a tag.
    If tag has been found returns it.
    Otherwise raises ParserFindTagException and writes
    information in logs, log level error.

    """
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag
