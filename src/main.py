import logging
import re
from urllib.parse import urljoin

from requests_cache import CachedSession
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import (
    BASE_DIR, EXPECTED_STATUS, LATEST_VERSION_TABLE_HEADER, MAIN_DOC_URL,
    PEP_CATALOG, PEP_TABLE_HEADER, WHATS_NEW_TABLE_HEADER
)
from exceptions import UnexpectedPEPStatus
from outputs import control_output
from utils import find_tag, get_response


def whats_new(session):
    """Function parses Main docs page, section "what-s-new-in-python".
    After parsing the section finds link to version page and pases it.
    While parsing the link of python version function saves version link,
    h1 and info about the editor/author.

    Returns the list of tuples like:
        (SPECIFIC TABLE HEADER),
        (link, h1 text, Editor, author),
        ...
    """
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )

    results = [WHATS_NEW_TABLE_HEADER]
    for section in tqdm(sections_by_python, desc='Парсинг ссылок'):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)

        response = get_response(session, version_link)
        if response is None:
            continue

        soup = BeautifulSoup(response.text, features='lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append(
            (version_link, h1.text, dl_text)
        )
    return results


def latest_versions(session):
    """Function parses Main docs page, sidebar.
    While parsing function saves link to python version, python version
    and status of python version.
    Returns the list of tuples like:
        (SPECIFIC TABLE HEADER),
        (link, version, status),
        ...
    """
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return

    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Ничего не нашлось')

    results = [LATEST_VERSION_TABLE_HEADER]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (link, version, status)
        )
    return results


def download(session):
    """Function parses Main doc download page.
    Function creates /download directory if it does not
    exist and saves as zip archive A4 pdf file.
    """
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(soup, 'div', {'role': 'main'})
    table_tag = find_tag(main_div, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(
        table_tag, 'a', attrs={'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]

    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename

    response = get_response(session, archive_url)
    if response is None:
        return

    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def compare_peps_statuses(
    pep_0_page_status, peps_card_status, link_to_pep_card
):
    """Function compares statuses from PEP0 page and PEP card.
    If statuses are not equal function writes difference in logs.
    """
    if peps_card_status not in pep_0_page_status:
        log_message = f"""
            Несовпадающие статусы:
            {link_to_pep_card}
            Статус в карточке: {peps_card_status}
            Ожидаемые статусы: {pep_0_page_status}
        """
        logging.info(log_message)


def pep(session):
    """Function parses the PEP0 page with all PEPs.
    While parsing the PEP0 page function saves PEPs statuses, gets part
    of a link for every PEP and parses them.
    As a result function:
        - counts amount of PEPs;
        - gets statuses from page with all PEPs and PEP's card page;
        - compares statuses and writes difference in log file;
        - counts every status from PEP card and saves it in dict().
    Returns the list of tuples like:
        (SPECIFIC TABLE HEADER),
        (PEP status, amount of that status),
        ...
        ('Total:', total amount of PEPs)
    """
    response = get_response(session, PEP_CATALOG)
    if response is None:
        return

    soup = BeautifulSoup(response.text, features='lxml')
    peps_numerical_section = find_tag(
        soup, 'section', attrs={'id': 'numerical-index'}
    )
    tbody_with_peps_info = find_tag(
        peps_numerical_section, 'tbody'
    )
    peps_tr = tbody_with_peps_info.find_all('tr')

    results = [PEP_TABLE_HEADER]
    total_peps = 0
    pep_0_page_statuses = []
    parsed_statuses = dict()
    for row in tqdm(peps_tr, desc='Парсинг страниц PEP'):
        pep_status = find_tag(row, 'td')
        pep_0_page_statuses.append(pep_status.text[1:])

        a_tag = find_tag(row, 'a', {'class': 'pep reference internal'})
        href_to_pep_page = a_tag['href']
        link_to_pep_card = urljoin(PEP_CATALOG, href_to_pep_page)
        total_peps += 1

        response = get_response(session, link_to_pep_card)
        if response is None:
            continue

        soup = BeautifulSoup(response.text, features='lxml')
        dl = find_tag(soup, 'dl')
        splitted_dl = dl.text.split('\n')
        current_pep_status = None
        for index in range(2, len(splitted_dl)):
            if splitted_dl[index] == 'Status:':
                status = splitted_dl[index + 1]
                current_pep_status = status
                parsed_statuses[status] = parsed_statuses.get(status, 0) + 1
                break

        pep_0_page_status = EXPECTED_STATUS.get(pep_0_page_statuses[-1], None)
        if pep_0_page_status is None:
            error_message = f"""
                Неизвестный статус:
                {pep_0_page_statuses[-1]}
                Неизвестный статус обнаружен в:
                PEP{a_tag.text}
            """
            logging.error(error_message)
            raise UnexpectedPEPStatus(error_message)

        compare_peps_statuses(
            pep_0_page_status, current_pep_status, link_to_pep_card
        )

    for pep_status, status_amount in parsed_statuses.items():
        results.append((pep_status, status_amount))
    results.append(('Total', total_peps))
    return results


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep
}


def main():
    """Function which controls the entire parser.
    Main function sets logging configuration, caches session and
    calls configure_argument_parser function for parsing termial
    inputs.
    """
    configure_logging()
    logging.info('Парсер запущен!')

    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')

    session = CachedSession()
    if args.clear_cache:
        session.cache.clear()

    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)

    if results is not None:
        control_output(results, args)
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
