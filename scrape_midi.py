from lxml import html
import requests
from collections import defaultdict
import re
import shutil
import os
from datetime import datetime
from time import sleep


class VGMusicScraper(object):
    """A basic scraper object that can be used to download midis from vgmusic.com."""
    def __init__(self, download_directory):
        self._base_url = "https://www.vgmusic.com/music/console/"
        self._games_to_scrape = defaultdict(set)
        self._download_directory = download_directory
        self._title_re = re.compile(r'<tr class="header"><td class="header" colspan="\d+"><a name=".+?">(?P<name>.+?)</a></td></tr>(?P<content>.+?)<tr><td colspan="5">&nbsp;</td></tr>')
        self._file_name_re = re.compile(r'[^ \w_\-]')
        self._last_time = None

    def throttle(self, throttle):
        if self._last_time is None:
            self._last_time = datetime.now()
        else:
            time_delta = (datetime.now() - self._last_time).total_seconds()
            if time_delta < throttle:
                sleep(throttle - time_delta)
                self._last_time = datetime.now()

    @staticmethod
    def _make_dir(directory):
        """This method creates, if non-existent, the specified (potentially nested) directories."""
        if not os.path.exists(directory):
            os.makedirs(directory)

    def add_game(self, platform_company, device, game):
        """Adds a game to the list of games to scrape. The parameters must be the exact names from the website to
        scrape from, except for capitalization. No attempts of normalization are made at this point."""
        platform_company, device, game = map(str.lower, [platform_company, device, game])
        self._games_to_scrape[(platform_company, device)].add(game)

    @staticmethod
    def _get_download_links(content):
        """Returns all download links in the html structure of content."""
        root = html.fromstring(content)
        links = root.xpath(".//td//a[contains(@href, '.mid')]/@href")
        return links

    def _download(self, path, platform_company, device, game, file_name):
        """Downloads the specified file from path + "/" file_name. The file is stored in a directory of the structure
        download_directory/platform_company/device/game/file_name."""
        url = "/".join([path, file_name])
        platform_company, device, game = [self._file_name_re.sub("", x) for x in [platform_company, device, game]]
        target_path = "/".join([self._download_directory, platform_company, device, game])
        response = requests.get(url, stream=True)
        self._make_dir(target_path)
        with open(os.path.join(target_path, file_name), 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        del response

    def scrape_all(self, throttle=.5):
        """Scrapes all midi files for the games in self._games_to_scrape. Before each download, it is checked whether
        the last access to the site is longer than throttle seconds in the past. It it is not, the remaining duration
        will be pass before the next download is triggered."""
        for (platform_company, device), game_set in self._games_to_scrape.items():
            self.throttle(throttle)
            path = None
            try:
                path = "/".join([self._base_url, platform_company, device])
                page = requests.get(path)
            except requests.exceptions.RequestException as e:
                print("Page", path, "could not be accessed:", e)
                break
            text = page.text.replace("\n", "")
            matches = self._title_re.finditer(text, re.IGNORECASE)
            for match in matches:
                (game, content) = match.groups([1, 2])
                if game.lower() in game_set:
                    download_links = self._get_download_links(content)
                    for download_link in download_links:
                        self.throttle(throttle)
                        self._download(path, platform_company, device, game, download_link)
        self._games_to_scrape.clear()

if __name__ == "__main__":
    test = VGMusicScraper("Midis")
    # test.add_game("Nintendo", "GBA", "Golden Sun")
    # test.add_game("Nintendo", "GBA", "Golden Sun: The Lost Age")
    # test.add_game("Nintendo", "GBA", "Legend of Zelda, The: A Link to the Past / Four Swords")
    # test.add_game("Nintendo", "GBA", "Legend of Zelda, The: The Minish Cap")
    # test.add_game("Nintendo", "GBA", "Pok&#233;mon (Black, White)")
    # test.add_game("Nintendo", "GBA", "Pok&#233;mon (Fire Red, Leaf Green)")
    # test.add_game("Nintendo", "GBA", "Pok&#233;mon (FireRed, LeafGreen)")
    # test.add_game("Nintendo", "GBA", "Pok&#233;mon (Ruby, Sapphire)")
    # test.add_game("Nintendo", "N64", "F-Zero X")
    # test.add_game("Nintendo", "N64", "Legend of Zelda, The: Majora's Mask")
    test.add_game("sega", "dreamcast", "Sonic Adventure")
    test.add_game("sega", "dreamcast", "Sonic Adventure 2")
    test.scrape_all(3)
