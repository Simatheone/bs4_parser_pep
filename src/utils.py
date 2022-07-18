import logging
from requests import RequestException

from exceptions import ParserFindTagException


def get_response(session, url):
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
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag


def compare_peps_statuses(
    pep_0_page_status, peps_card_status, link_to_pep_card
):
    if peps_card_status not in pep_0_page_status:
        log_message = f"""
            Несовпадающие статусы:
            {link_to_pep_card}
            Статус в карточке: {peps_card_status}
            Ожидаемые статусы: {pep_0_page_status}
        """
        logging.info(log_message)
