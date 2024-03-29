
import os
import re
import requests
from bs4 import BeautifulSoup
from string import Template
import config

chap_url = Template("http://ncode.syosetu.com/${novel}/${chapter}/")
headers = {
    'User-Agent':
    "Mozilla/5.0 (X11; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0"
}


class NoChapterException(Exception):
    pass


def get_soup(url, verbose=False):
    if verbose:
        print(f'connecting...{url}', end='')
    r = requests.get(url, headers=headers)
    if r.status_code == 404:
        if verbose:
            print(': 404 Error.')
        raise NoChapterException
    if verbose:
        print(':Connected.')
    return BeautifulSoup(r.text, 'html.parser')


def get_chapter(novel, chap_no):
    soup = get_soup(chap_url.substitute(novel=novel, chapter=chap_no))
    entry = soup.find('div', {'id': 'novel_contents'})
    chapname = entry.find('p', {'class': 'novel_subtitle'})
    content = entry.find('div', {'id': 'novel_honbun'})

    chaptitle = chapname.text
    contents = content.text

    print(f'Completed::{chap_no}-{chaptitle}')
    return (chaptitle, contents)


def save_chapter(novel, chap_no, filename=None):
    chaptitle, contents = get_chapter(novel, chap_no)
    if filename is None:
        filename = os.path.join(config.root_path,
                                f'data/{novel}_{chap_no}.txt')
    with open(filename, 'w') as w:
        file_content = f'* {chaptitle}\n{contents}'
        file_content = re.sub(r'\n+ *', '\n\n', file_content)
        w.write(file_content)
    return filename
