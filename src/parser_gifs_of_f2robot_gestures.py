"""Загружает GIF-анимации жестов с сайта поддержки F2Robot."""

import os
import re
import time
from urllib.parse import urljoin, urlparse, unquote

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


PAGE_URL = "https://f2robot.com/support/gest/"
OUT_DIR = "src/data/f2robot_gifs"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def create_session() -> requests.Session:
    """Создает HTTP-сессию с повторными попытками загрузки."""
    session = requests.Session()
    session.headers.update(HEADERS)

    retries = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=2,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=("GET",),
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def safe_filename(name: str) -> str:
    """Преобразует часть URL в безопасное имя файла."""
    name = unquote(name)
    name = os.path.basename(name)
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name


def get_gif_links(session: requests.Session, page_url: str) -> list[str]:
    """Возвращает найденные на странице ссылки на GIF-файлы."""
    print("Загружаю страницу...")

    response = session.get(
        page_url,
        timeout=(30, 120),  # 30 сек на подключение, 120 сек на чтение
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    links = set()

    for img in soup.find_all("img"):
        src = img.get("src")
        if src and ".gif" in src.lower():
            links.add(urljoin(page_url, src))

    for a in soup.find_all("a"):
        href = a.get("href")
        if href and ".gif" in href.lower():
            links.add(urljoin(page_url, href))

    return sorted(links)


def download_file(session: requests.Session, url: str, out_dir: str) -> None:
    """Загружает GIF-файл, если его еще нет в целевом каталоге."""
    os.makedirs(out_dir, exist_ok=True)

    filename = safe_filename(urlparse(url).path)

    if not filename:
        return

    if not filename.lower().endswith(".gif"):
        filename += ".gif"

    filepath = os.path.join(out_dir, filename)

    if os.path.exists(filepath):
        print(f"Уже есть: {filename}")
        return

    print(f"Скачиваю: {url}")

    response = session.get(
        url,
        timeout=(30, 120),
    )
    response.raise_for_status()

    with open(filepath, "wb") as file:
        file.write(response.content)

    print(f"Готово: {filename}")


def main() -> None:
    """Загружает все GIF-анимации с настроенной страницы."""
    session = create_session()

    try:
        gif_links = get_gif_links(session, PAGE_URL)
    except requests.exceptions.RequestException as error:
        print(f"Не удалось загрузить страницу: {error}")
        return

    print(f"Найдено GIF: {len(gif_links)}")

    for url in gif_links:
        try:
            download_file(session, url, OUT_DIR)
            time.sleep(0.5)
        except requests.exceptions.RequestException as error:
            print(f"Не удалось скачать {url}: {error}")


if __name__ == "__main__":
    main()
