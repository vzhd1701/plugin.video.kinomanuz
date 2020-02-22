# coding=utf-8
# pylint: disable=protected-access, no-self-use

import os
import json
import re
import unittest

from test.fake_xbmcaddon import Addon

try:
    import mock
except ImportError:
    from unittest import mock

import urllib3
import requests

FAKE_ADDON = Addon()

with mock.patch("sys.argv", ["plugin://test.plugin", "1", "/"]):
    import addon

# kinoman.uz cert is invalid, disable SSL warnings
urllib3.disable_warnings()

KINOMAN_USER = os.getenv("KINOMAN_USER")
KINOMAN_PASS = os.getenv("KINOMAN_PASS")
KINOMAN_USER_ID = int(os.getenv("KINOMAN_USER_ID") or 0)


@unittest.skipUnless(
    all([KINOMAN_USER, KINOMAN_PASS]), "Need credentials for real test"
)
@mock.patch("addon.player.ADDON", FAKE_ADDON)
class TestAddonPaths(unittest.TestCase):
    @classmethod
    @mock.patch("addon.player.ADDON", FAKE_ADDON)
    def setUpClass(cls):
        addon.player.set_setting("username", KINOMAN_USER)
        addon.player.set_setting("password", KINOMAN_PASS)

        addon.player.set_setting("search_history_status", False)
        session = requests.Session()
        session.headers.update({"User-Agent": addon.kinoman_api.SPOOF_USER_AGENT})

        cls.login_success = addon.kinoman_api._kinoman_login(session)

        session.close()

    def setUp(self):
        if not self.login_success:
            self.fail("Failed to login for test")

    @classmethod
    @mock.patch("addon.player.ADDON", FAKE_ADDON)
    def tearDownClass(cls):
        session = requests.Session()
        session.headers.update({"User-Agent": addon.kinoman_api.SPOOF_USER_AGENT})

        session.cookies.update(json.loads(addon.player.get_setting("_cookie")))

        session.post(
            "https://www.kinoman.uz/api/v1/user/logout", data="{}", verify=False
        )

        session.close()

    @mock.patch("addon.player.print_items")
    def test_root(self, mock_print):
        expected_result = [
            {
                "label": "Фильмы",
                "path": "/list_movies/?category=movies&"
                "content_type_id=1&genre_black_list=12",
                "is_folder": True,
            },
            {
                "label": "Фильмы (премьеры)",
                "path": "/list_movies/?category=movies&"
                "content_type_id=1&genre_black_list=12&sort_type=1",
                "is_folder": True,
            },
            {
                "label": "Сериалы",
                "path": "/list_movies/?category=tv-series&"
                "content_type_id=2&genre_black_list=12",
                "is_folder": True,
            },
            {
                "label": "Сериалы (премьеры)",
                "path": "/list_movies/?category=tv-series&"
                "content_type_id=2&genre_black_list=12&sort_type=1",
                "is_folder": True,
            },
            {
                "label": "Мультфильмы",
                "path": "/list_movies/?category=cartoons&"
                "content_type_id=0&genre_list=12",
                "is_folder": True,
            },
            {
                "label": "Мультфильмы (премьеры)",
                "path": "/list_movies/?category=cartoons&"
                "content_type_id=0&genre_list=12&sort_type=1",
                "is_folder": True,
            },
            {
                "label": "ТВ-программы",
                "path": "/list_movies/?category=tv-shows&"
                "content_type_id=3&genre_black_list=12",
                "is_folder": True,
            },
            {
                "label": "ТВ-программы (премьеры)",
                "path": "/list_movies/?category=tv-shows&"
                "content_type_id=3&genre_black_list=12&sort_type=1",
                "is_folder": True,
            },
            {
                "label": "Видеоблоги",
                "path": "/list_movies/?category=vlogs&"
                "content_type_id=4&genre_black_list=12",
                "is_folder": True,
            },
            {
                "label": "Видеоблоги (премьеры)",
                "path": "/list_movies/?category=vlogs&"
                "content_type_id=4&genre_black_list=12&sort_type=1",
                "is_folder": True,
            },
            {
                "label": "Избранное",
                "path": "/list_movies/?category=favorite&content_type_id=0&favorite=1"
                "&title=%D0%B8%D0%B7%D0%B1%D1%80%D0%B0%D0%BD%D0%BD%D0%BE%D0%B5",
                "is_folder": True,
            },
            {
                "label": "Поиск по фильтру",
                "path": "/search_filter/",
                "video_data": {"art": {"icon": "DefaultAddonsSearch.png"}},
                "is_folder": True,
            },
            {
                "label": "Поиск",
                "path": "/search/",
                "video_data": {"art": {"icon": "DefaultAddonsSearch.png"}},
                "is_folder": True,
            },
        ]

        with mock.patch("sys.argv", ["plugin://test.plugin", "1", "/"]):
            addon.main()

        mock_print.assert_called_once_with(expected_result, cache=False)

    @mock.patch("addon.player.print_items")
    def test_movie_sections(self, mock_print):
        with mock.patch("sys.argv", ["plugin://test.plugin", "1", "/"]):
            addon.main()

        movie_sections = mock_print.call_args[0][0]

        for section in movie_sections:
            if section["label"] == "Избранное":
                break

            with mock.patch("sys.argv", ["plugin://test.plugin", "1", section["path"]]):
                mock_print.reset_mock()
                addon.main()

                movies_list = mock_print.call_args[0][0]

                self.assertRegexpMatches(movies_list[0]["path"], r"^/movie/[0-9]+/$")

                # Checking if paginator works by going to last two pages
                # of the list (if this list has multiple pages)
                if movies_list[-1]["label"].startswith("-->"):
                    last_page = int(
                        re.search(
                            r"^--> \(2 / ([0-9]+)\)$", movies_list[-1]["label"]
                        ).group(1)
                    )

                    for page_n in range(last_page - 1, last_page + 1):
                        with mock.patch(
                            "sys.argv",
                            [
                                "plugin://test.plugin",
                                "1",
                                section["path"] + "&page={}".format(page_n),
                            ],
                        ):
                            mock_print.reset_mock()
                            addon.main()

                            page_movies = mock_print.call_args[0][0]

                            # I think there is an off-by-one error somewhere on server
                            # side, it glitched once, so putting this special case here
                            if not page_movies and page_n == last_page:
                                continue

                            if page_n == last_page - 1:
                                self.assertRegexpMatches(
                                    page_movies[-1]["label"],
                                    r"^--> \({} / {}\)$".format(last_page, last_page),
                                )
                            elif page_n == last_page:
                                self.assertNotRegexpMatches(
                                    page_movies[-1]["label"],
                                    r"^--> \([0-9]+ / [0-9]+\)$",
                                )

    @mock.patch("addon.player.play")
    @mock.patch("addon.player.print_items")
    def test_movie_playback(self, mock_print, mock_play):
        with mock.patch("sys.argv", ["plugin://test.plugin", "1", "/movie/73/"]):
            addon.main()

        video_types = mock_print.call_args[0][0]

        for video in video_types:
            self.assertRegexpMatches(video["path"], r"^/play/http.*$")
            self.assertRegexpMatches(video["label"], r"^Воспроизвести \(.*\)$")

            with mock.patch("sys.argv", ["plugin://test.plugin", "1", video["path"]]):
                mock_play.reset_mock()
                addon.main()

                playback_url = mock_play.call_args[0][0]

                self.assertRegexpMatches(
                    playback_url,
                    r"^https://(online|dl)[0-9]+\.kinoman\.uz/dl/(online|movie)"
                    r"/[0-9]+/.*\..*?$",
                )

    @mock.patch("addon.player.play")
    @mock.patch("addon.player.print_items")
    def test_series_playback(self, mock_print, mock_play):
        with mock.patch("sys.argv", ["plugin://test.plugin", "1", "/movie/166/"]):
            addon.main()

        video_types = mock_print.call_args[0][0]

        for video in video_types:
            self.assertRegexpMatches(video["path"], r"^/movie/166/[a-z]+/$")
            self.assertRegexpMatches(video["label"], r"^Смотреть серии \(.*\)$")

            with mock.patch("sys.argv", ["plugin://test.plugin", "1", video["path"]]):
                mock_print.reset_mock()
                addon.main()

                episodes_list = mock_print.call_args[0][0]

                for e_video in [episodes_list[0], episodes_list[-1]]:
                    self.assertRegexpMatches(e_video["path"], r"^/play/http.*$")

                    with mock.patch(
                        "sys.argv", ["plugin://test.plugin", "1", e_video["path"]]
                    ):
                        mock_play.reset_mock()
                        addon.main()

                        playback_url = mock_play.call_args[0][0]

                        self.assertRegexpMatches(
                            playback_url,
                            r"^https://(online|dl)[0-9]+\.kinoman\.uz/dl/(online|movie)"
                            r"/[0-9]+/.*\..*?$",
                        )

    @mock.patch("addon.player.print_items")
    def test_search_filter(self, mock_print):
        with mock.patch("sys.argv", ["plugin://test.plugin", "1", "/search_filter/"]):
            addon.main()

        # 4 steps -> video category, age rating, genre, year
        for i in range(1, 5):
            next_menu = mock_print.call_args[0][0][1]

            with mock.patch(
                "sys.argv", ["plugin://test.plugin", "1", next_menu["path"]]
            ):
                mock_print.reset_mock()
                addon.main()

            if i <= 3:
                self.assertRegexpMatches(
                    next_menu["path"], r"^/search_filter/{}/.*$".format(i)
                )
            else:
                self.assertRegexpMatches(next_menu["path"], r"^/list_movies/.*$")

    @mock.patch("addon.player.print_items")
    def test_search(self, mock_print):
        with mock.patch(
            "sys.argv", ["plugin://test.plugin", "1", "/search/мастер и маргарита/"]
        ):
            addon.main()

        search_results = mock_print.call_args[0][0]

        for video in search_results:
            if video["path"] == "/movie/166/":
                self.assertEqual(video["label"], "Мастер и Маргарита (2005)")
                break
        else:
            self.fail("Test video not found in the listing, probably something wrong")

    @mock.patch("addon.list_movies", mock.MagicMock())
    @mock.patch("addon.player.print_items")
    def test_search_history(self, mock_print):
        addon.player.set_setting("search_history_status", True)
        addon.search_clear()

        with mock.patch(
            "sys.argv", ["plugin://test.plugin", "1", "/search/test search/"]
        ):
            addon.main()

        mock_print.reset_mock()
        with mock.patch("sys.argv", ["plugin://test.plugin", "1", "/"]):
            addon.main()

        main_menu = mock_print.call_args[0][0]

        for item in main_menu:
            if item["path"] == "/search_history/":
                break
        else:
            self.fail("Search history menu is missing with nonempty history")

        mock_print.reset_mock()
        with mock.patch("sys.argv", ["plugin://test.plugin", "1", "/search_history/"]):
            addon.main()

        search_menu = mock_print.call_args[0][0]

        self.assertEqual(search_menu[-1]["path"], "/search/test%20search/")
        self.assertEqual(search_menu[-1]["label"], "test search")

        addon.search_clear()
        addon.player.set_setting("search_history_status", False)
