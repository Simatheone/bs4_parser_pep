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
from outputs import control_output
from utils import compare_peps_statuses, find_tag, get_response


def whats_new(session):
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

    # Creating a filename
    filename = archive_url.split('/')[-1]

    # Creating a new directory "downloads"
    # Creating path to directory (merge download dir and filename)
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename

    # Downloading ZIP-archive from "archive_url"
    response = get_response(session, archive_url)
    if response is None:
        return

    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
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

        pep_0_page_status = EXPECTED_STATUS[pep_0_page_statuses[-1]]
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
