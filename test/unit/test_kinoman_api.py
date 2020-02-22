# coding=utf-8
# pylint: disable=protected-access

import time
import json
import unittest

from collections import namedtuple, OrderedDict

from test.fake_player import FakePlayer

try:
    import mock
except ImportError:
    from unittest import mock

import requests

with mock.patch("sys.argv", ["plugin://test.plugin", "1", "/"]):
    from resources import kinoman_api


class TestMinorStuff(unittest.TestCase):
    def test_cleanhtml(self):
        self.assertEqual(kinoman_api._cleanhtml("<p>Some text</p>"), "Some text")

    @mock.patch("resources.kinoman_api.get_page")
    def test_get_video_url(self, mock_get_page):
        mock_get_page.return_value = {"url": "http://test.com/test_url"}
        self.assertEqual(
            kinoman_api.get_video_url("fake path"), "http://test.com/test_url"
        )

    def test_json_loads_byteified_dict(self):
        self.assertDictEqual(
            kinoman_api._json_loads_byteified('{"title": "тест"}'), {"title": "тест"}
        )

    def test_json_loads_byteified_list(self):
        self.assertListEqual(
            kinoman_api._json_loads_byteified('["тест1", "тест2"]'), ["тест1", "тест2"]
        )


class TestKinomanLogin(unittest.TestCase):
    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_cookie_fresh(self, mock_player):
        mock_session = mock.MagicMock()
        mock_player.set_setting("_cookie", "{}")
        mock_player.set_setting("_last_check", int(time.time()) + 1000)

        self.assertTrue(kinoman_api._kinoman_login(mock_session))

    @mock.patch("resources.kinoman_api.time")
    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_good_cookie_expired(self, mock_player, mock_time):
        mock_session = mock.MagicMock()
        mock_time.time.return_value = 1000
        mock_player.set_setting("_cookie", "{}")
        mock_player.set_setting("_last_check", 0)

        fake_page = namedtuple("FakePage", ["status_code", "text"])
        mock_session.get.return_value = fake_page(
            status_code=200,
            text='{"user": {"abon_time_is_active": true, "user_id": 100}}',
        )
        mock_session.cookies.get_dict.return_value = {"updated_cookie": "updated_value"}

        self.assertTrue(kinoman_api._kinoman_login(mock_session))
        self.assertEqual(
            json.loads(mock_player.get_setting("_cookie")),
            {"updated_cookie": "updated_value"},
        )
        self.assertEqual(mock_player.get_setting("_last_check", "int"), 1000)

    @mock.patch("resources.kinoman_api.time")
    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_good(self, mock_player, mock_time):
        mock_session = mock.MagicMock()
        mock_time.time.return_value = 1000
        mock_player.set_setting("_cookie", "")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", "fake_login")
        mock_player.set_setting("password", "fake_password")

        fake_page = namedtuple("FakePage", ["status_code", "text"])
        mock_session.post.return_value = fake_page(
            status_code=200,
            text='{"user": {"user_id": 100, "abon_time_is_active": true}}',
        )
        mock_session.cookies.get_dict.return_value = {"new_cookie": "new_value"}

        self.assertTrue(kinoman_api._kinoman_login(mock_session))
        self.assertEqual(
            json.loads(mock_player.get_setting("_cookie")), {"new_cookie": "new_value"}
        )
        self.assertEqual(mock_player.get_setting("_last_check", "int"), 1000)
        self.assertEqual(mock_player.get_setting("_user_id", "int"), 100)

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_cookie_access_denied(self, mock_player):
        mock_session = mock.MagicMock()
        mock_player.set_setting("_cookie", "{}")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", "")
        mock_player.set_setting("password", "")

        fake_page = namedtuple("FakePage", ["status_code", "text"])
        mock_session.get.return_value = fake_page(status_code=401, text="{}")

        with self.assertRaises(kinoman_api.LoginError):
            kinoman_api._kinoman_login(mock_session)

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_cookie_unknown_error(self, mock_player):
        mock_session = mock.MagicMock()
        mock_player.set_setting("_cookie", "{}")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", "")
        mock_player.set_setting("password", "")

        fake_page = namedtuple("FakePage", ["status_code", "text"])
        mock_session.get.return_value = fake_page(status_code=500, text="{}")

        with self.assertRaises(kinoman_api.LoginError):
            kinoman_api._kinoman_login(mock_session)

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_network_error(self, mock_player):
        mock_session = mock.MagicMock()
        mock_player.set_setting("_cookie", "{}")
        mock_player.set_setting("_last_check", 0)

        mock_session.get.side_effect = requests.ConnectionError

        with self.assertRaises(kinoman_api.NetworkError):
            kinoman_api._kinoman_login(mock_session)

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_empty_credentials(self, mock_player):
        mock_session = mock.MagicMock()
        mock_player.set_setting("_cookie", "")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", "")
        mock_player.set_setting("password", "")

        with self.assertRaises(kinoman_api.LoginError):
            kinoman_api._kinoman_login(mock_session)

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_network_error_credentials(self, mock_player):
        mock_session = mock.MagicMock()
        mock_player.set_setting("_cookie", "")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", "fake_login")
        mock_player.set_setting("password", "fake_password")

        mock_session.post.side_effect = requests.ConnectionError

        with self.assertRaises(kinoman_api.NetworkError):
            kinoman_api._kinoman_login(mock_session)

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_bad(self, mock_player):
        mock_session = mock.MagicMock()
        mock_player.set_setting("_cookie", "")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", "fake_login")
        mock_player.set_setting("password", "fake_password")

        fake_page = namedtuple("FakePage", ["status_code", "text"])
        mock_session.post.return_value = fake_page(
            status_code=401, text="Логин или пароль неверны"
        )

        with self.assertRaises(kinoman_api.LoginError):
            kinoman_api._kinoman_login(mock_session)

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_banned_ip_error(self, mock_player):
        mock_session = mock.MagicMock()
        mock_player.set_setting("_cookie", "")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", "fake_login")
        mock_player.set_setting("password", "fake_password")

        fake_page = namedtuple("FakePage", ["status_code", "text"])
        mock_session.post.return_value = fake_page(status_code=500, text="")

        with self.assertRaises(kinoman_api.LoginError):
            kinoman_api._kinoman_login(mock_session)

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_unknown_error(self, mock_player):
        mock_session = mock.MagicMock()
        mock_player.set_setting("_cookie", "")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", "fake_login")
        mock_player.set_setting("password", "fake_password")

        fake_page = namedtuple("FakePage", ["status_code", "text"])
        mock_session.post.return_value = fake_page(status_code=404, text="")

        with self.assertRaises(kinoman_api.LoginError):
            kinoman_api._kinoman_login(mock_session)

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_bad_unknown(self, mock_player):
        mock_session = mock.MagicMock()
        mock_player.set_setting("_cookie", "")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", "fake_login")
        mock_player.set_setting("password", "fake_password")

        fake_page = namedtuple("FakePage", ["status_code", "text"])
        mock_session.post.return_value = fake_page(status_code=200, text="{}")

        with self.assertRaises(kinoman_api.LoginError):
            kinoman_api._kinoman_login(mock_session)

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_bad_expired_subscription(self, mock_player):
        mock_session = mock.MagicMock()
        mock_player.set_setting("_cookie", "")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", "fake_login")
        mock_player.set_setting("password", "fake_password")

        fake_page = namedtuple("FakePage", ["status_code", "text"])
        mock_session.post.return_value = fake_page(
            status_code=200, text='{"user": {"abon_time_is_active": false}}'
        )

        with self.assertRaises(kinoman_api.LoginError):
            kinoman_api._kinoman_login(mock_session)


class TestGetPage(unittest.TestCase):
    @mock.patch("resources.kinoman_api._kinoman_login", mock.MagicMock())
    @mock.patch("requests.Session")
    def test_get_page_plain(self, mock_session):
        fake_page = namedtuple("FakePage", ["status_code", "text"])
        mock_session().get.return_value = fake_page(
            status_code=200, text='{"test": "test"}'
        )

        self.assertEqual(kinoman_api.get_page("http://www.test.com"), {"test": "test"})

    @mock.patch("resources.kinoman_api._kinoman_login", mock.MagicMock())
    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    @mock.patch("requests.Session")
    def test_get_page_payload(self, mock_session, mock_player):
        mock_player.set_setting("_user_id", 100)
        fake_page = namedtuple("FakePage", ["status_code", "text"])
        mock_session().post.return_value = fake_page(
            status_code=200, text='{"test": "test"}'
        )
        test_payload = {"payload": "test"}

        self.assertEqual(
            kinoman_api.get_page(
                "http://www.test.com", payload=test_payload, user_id_required=True
            ),
            {"test": "test"},
        )
        self.assertEqual(test_payload["user_id"], 100)

    @mock.patch("resources.kinoman_api._kinoman_login", mock.MagicMock())
    @mock.patch("requests.Session")
    def test_get_page_network_error(self, mock_session):
        mock_session().get.side_effect = requests.ConnectionError

        with self.assertRaises(kinoman_api.NetworkError):
            kinoman_api.get_page("http://www.test.com")


class TestGetMovieData(unittest.TestCase):
    def setUp(self):
        self.test_movie_data = {
            "movie": {
                "id": 1001,
                "title": "Test Movie",
                "type_id": 1,
                "release_date": "2019-10-02T05:00:00+05:00",
                "poster_url": "img.kinoman.uz/p00000_11111",
                "release_year": 2019,
                "has_update": False,
                "is_favorite": False,
                "alt_title": None,
                "original_title": "Test Movie Original",
                "description": "Test description",
                "age_rating": 18,
                "kinopoisk_url": "https://www.kinopoisk.ru/film/0000000/",
                "countries": [
                    {"id": 100, "title": "Test Country 1"},
                    {"id": 200, "title": "Test Country 2"},
                    {"id": 300, "title": "Test Country 3"},
                ],
                "genres": [
                    {"id": 10, "title": "test genre 1"},
                    {"id": 20, "title": "test genre 2"},
                ],
                "directors": [
                    {"id": 10000, "title": "Test Director 1"},
                    {"id": 10000, "title": "Test Director 2"},
                ],
                "actors": [
                    {"id": 20000, "title": "Test Actor 1"},
                    {"id": 30000, "title": "Test Actor 2"},
                ],
                "screenshots": [
                    {"id": 100001, "title": "img.kinoman.uz/s00000_100001"},
                    {"id": 100002, "title": "img.kinoman.uz/s00000_100002"},
                    {"id": 100003, "title": "img.kinoman.uz/s00000_100003"},
                ],
                "trailers": [],
                # Usually these are filled
                "online_files": [],
                "download_files": [],
            }
        }

        self.test_files_data_movie = {
            "online_files": [
                {
                    "id": 0,
                    "secure_id": "secure_id1_base64",
                    "title": "o_test_movie_2019.mp4",
                    "url": "",
                }
            ],
            "download_files": [
                {
                    "file_id": 0,
                    "secure_id": "secure_id2_base64",
                    "file_name": "test_movie_2019.mkv",
                    "title": "профессиональное (многоголосое)",
                    "name": "HDTVRIP",
                    "file_size": "1139736015",
                    "width": "768",
                    "height": "320",
                    "lang_title": "русский",
                },
                {
                    "file_id": 0,
                    "secure_id": "secure_id3_base64",
                    "file_name": "test_movie_2019_720p.mkv",
                    "title": "профессиональное (многоголосое)",
                    "name": "HDTVRIP",
                    "file_size": "1139736015",
                    "width": "1280",
                    "height": "720",
                    "lang_title": "русский",
                },
                {
                    "file_id": 0,
                    "secure_id": "secure_id4_base64",
                    "file_name": "test_movie_2019_1080p_dub.mkv",
                    "title": "профессиональное (многоголосое)",
                    "name": "BDRIP",
                    "file_size": "7302446693",
                    "width": "1920",
                    "height": "1080",
                    "lang_title": "русский и английский",
                },
            ],
        }

        self.test_files_expected_result_movie = OrderedDict(
            [
                (
                    "online",
                    [
                        [
                            "o_test_movie_2019.mp4",
                            "https://www.kinoman.uz/api/v1/movie/online/"
                            "secure_id1_base64",
                            None,
                            None,
                        ]
                    ],
                ),
                (
                    "sd",
                    [
                        [
                            "test_movie_2019.mkv",
                            "https://www.kinoman.uz/api/v1/movie/download/"
                            "secure_id2_base64",
                            None,
                            "Видео: HDTVRIP (768x320)[CR]Аудио: профессиональное"
                            " (многоголосое)",
                        ]
                    ],
                ),
                (
                    "hd",
                    [
                        [
                            "test_movie_2019_720p.mkv",
                            "https://www.kinoman.uz/api/v1/movie/download/"
                            "secure_id3_base64",
                            None,
                            "Видео: HDTVRIP (1280x720)[CR]Аудио: профессиональное"
                            " (многоголосое)",
                        ]
                    ],
                ),
                (
                    "full_hd",
                    [
                        [
                            "test_movie_2019_1080p_dub.mkv",
                            "https://www.kinoman.uz/api/v1/movie/download/"
                            "secure_id4_base64",
                            None,
                            "Видео: BDRIP (1920x1080)[CR]Аудио: профессиональное"
                            " (многоголосое)",
                        ]
                    ],
                ),
            ]
        )

        self.test_files_data_series = {
            "title": "Test Series (Сезон 1)",
            "online_files": [
                {
                    "id": 0,
                    "secure_id": "secure_id1_base64",
                    "title": "o_test_series_s01e01.mp4",
                    "url": "",
                },
                {
                    "id": 0,
                    "secure_id": "secure_id2_base64",
                    "title": "o_test_series_s01e02.mp4",
                    "url": "",
                },
                {
                    "id": 0,
                    "secure_id": "secure_id3_base64",
                    "title": "o_test_series_s01e03.mp4",
                    "url": "",
                },
            ],
            "download_files": [
                {
                    "file_id": 0,
                    "secure_id": "secure_id4_base64",
                    "file_name": "test_series_s01e01.avi",
                    "title": "любительское (двухголосое)",
                    "name": "HDTVRIP",
                    "file_size": "1573770620",
                    "width": "720",
                    "height": "400",
                    "lang_title": "русский",
                },
                {
                    "file_id": 0,
                    "secure_id": "secure_id5_base64",
                    "file_name": "test_series_s01e02.avi",
                    "title": "любительское (двухголосое)",
                    "name": "HDTVRIP",
                    "file_size": "1632606732",
                    "width": "720",
                    "height": "400",
                    "lang_title": "русский",
                },
                {
                    "file_id": 0,
                    "secure_id": "secure_id6_base64",
                    "file_name": "test_series_s01e03.avi",
                    "title": "любительское (двухголосое)",
                    "name": "HDTVRIP",
                    "file_size": "1671801250",
                    "width": "720",
                    "height": "400",
                    "lang_title": "русский",
                },
            ],
        }

        self.test_files_expected_result_series = OrderedDict(
            [
                (
                    "online",
                    [
                        [
                            "o_test_series_s01e01.mp4",
                            "https://www.kinoman.uz/api/v1/movie/online/"
                            "secure_id1_base64",
                            {"season": 1, "episode": 1, "title": "Test Series S01E01"},
                            None,
                        ],
                        [
                            "o_test_series_s01e02.mp4",
                            "https://www.kinoman.uz/api/v1/movie/online/"
                            "secure_id2_base64",
                            {"season": 1, "episode": 2, "title": "Test Series S01E02"},
                            None,
                        ],
                        [
                            "o_test_series_s01e03.mp4",
                            "https://www.kinoman.uz/api/v1/movie/online/"
                            "secure_id3_base64",
                            {"season": 1, "episode": 3, "title": "Test Series S01E03"},
                            None,
                        ],
                    ],
                ),
                (
                    "sd",
                    [
                        [
                            "test_series_s01e01.avi",
                            "https://www.kinoman.uz/api/v1/movie/download/"
                            "secure_id4_base64",
                            {"season": 1, "episode": 1, "title": "Test Series S01E01"},
                            "Видео: HDTVRIP (720x400)[CR]Аудио: любительское"
                            " (двухголосое)",
                        ],
                        [
                            "test_series_s01e02.avi",
                            "https://www.kinoman.uz/api/v1/movie/download/"
                            "secure_id5_base64",
                            {"season": 1, "episode": 2, "title": "Test Series S01E02"},
                            "Видео: HDTVRIP (720x400)[CR]Аудио: любительское"
                            " (двухголосое)",
                        ],
                        [
                            "test_series_s01e03.avi",
                            "https://www.kinoman.uz/api/v1/movie/download/"
                            "secure_id6_base64",
                            {"season": 1, "episode": 3, "title": "Test Series S01E03"},
                            "Видео: HDTVRIP (720x400)[CR]Аудио: любительское"
                            " (двухголосое)",
                        ],
                    ],
                ),
            ]
        )

    @mock.patch("resources.kinoman_api._generate_movie_file_lists")
    @mock.patch("resources.kinoman_api.get_page")
    def test_get_movie_data_good(self, mock_get_page, mock_gen_files):
        expected_result = {
            "movie_info": {
                "art": {
                    "banner": "https://img.kinoman.uz/p00000_11111mp.jpg",
                    "icon": "https://img.kinoman.uz/p00000_11111mp.jpg",
                    "poster": "https://img.kinoman.uz/p00000_11111mp.jpg",
                    "thumb": "https://img.kinoman.uz/p00000_11111mp.jpg",
                },
                "info": {
                    "title": "Test Movie",
                    "originaltitle": "Test Movie Original",
                    "premiered": "2019-10-02",
                    "year": 2019,
                    "rating": 18,
                    "plot": "Test description",
                    "cast": ["Test Actor 1", "Test Actor 2"],
                    "country": "Test Country 1 / Test Country 2 / Test Country 3",
                    "director": "Test Director 1 / Test Director 2",
                    "genre": "test genre 1 / test genre 2",
                },
                "properties": {},
            },
            "file_lists": [],
            "series_season_n": None,
        }

        mock_gen_files.return_value = []
        mock_get_page.return_value = self.test_movie_data

        result = kinoman_api.get_movie_data(1001)

        # Fanart is picked from random screenshot
        # so check if it's OK and remove it from assertion
        self.assertEqual(
            result["movie_info"]["art"]["fanart"],
            result["movie_info"]["properties"]["Fanart_Image"],
        )
        self.assertRegexpMatches(
            result["movie_info"]["art"]["fanart"],
            r"https://img\.kinoman\.uz/s00000_10000[0-9]b\.jpg",
        )

        del result["movie_info"]["art"]["fanart"]
        del result["movie_info"]["properties"]["Fanart_Image"]

        self.assertDictEqual(result, expected_result)

    @mock.patch("resources.kinoman_api._generate_movie_file_lists")
    @mock.patch("resources.kinoman_api.get_page")
    def test_get_movie_data_series(self, mock_get_page, mock_gen_files):
        self.test_movie_data["movie"]["title"] = "Test Movie (Сезон 10)"
        self.test_movie_data["movie"]["type_id"] = 2

        mock_gen_files.return_value = []
        mock_get_page.return_value = self.test_movie_data

        result = kinoman_api.get_movie_data(1001)

        self.assertEqual(result["series_season_n"], "10")

    @mock.patch("resources.kinoman_api._generate_movie_file_lists")
    @mock.patch("resources.kinoman_api.get_page")
    def test_get_movie_data_series_odd_title(self, mock_get_page, mock_gen_files):
        self.test_movie_data["movie"]["type_id"] = 2

        mock_gen_files.return_value = []
        mock_get_page.return_value = self.test_movie_data

        result = kinoman_api.get_movie_data(1001)

        self.assertEqual(result["series_season_n"], "01")

    @mock.patch("resources.kinoman_api._generate_movie_file_lists")
    @mock.patch("resources.kinoman_api.get_page")
    def test_get_movie_data_no_screenshots(self, mock_get_page, mock_gen_files):
        self.test_movie_data["movie"]["screenshots"] = []

        mock_gen_files.return_value = []
        mock_get_page.return_value = self.test_movie_data

        result = kinoman_api.get_movie_data(1001)

        self.assertEqual(
            result["movie_info"]["art"]["fanart"], result["movie_info"]["art"]["poster"]
        )
        self.assertEqual(
            result["movie_info"]["properties"]["Fanart_Image"],
            result["movie_info"]["art"]["poster"],
        )

    def test_generate_movie_file_lists_movie(self):
        self.assertDictEqual(
            kinoman_api._generate_movie_file_lists(self.test_files_data_movie),
            self.test_files_expected_result_movie,
        )

    def test_generate_movie_file_lists_series(self):
        self.assertDictEqual(
            kinoman_api._generate_movie_file_lists(self.test_files_data_series, "01"),
            self.test_files_expected_result_series,
        )

    def test_generate_movie_file_lists_series_no_episode_numbers(self):
        test_files_data = {
            "title": "Test Series (Сезон 1)",
            "online_files": [
                {
                    "id": 0,
                    "secure_id": "secure_id1_base64",
                    "title": "o_test_series_episode_1.mp4",
                    "url": "",
                },
                {
                    "id": 0,
                    "secure_id": "secure_id2_base64",
                    "title": "o_test_series_episode_2.mp4",
                    "url": "",
                },
                {
                    "id": 0,
                    "secure_id": "secure_id3_base64",
                    "title": "o_test_series_episode_3.mp4",
                    "url": "",
                },
            ],
            "download_files": [],
        }

        expected_result = OrderedDict(
            [
                (
                    "online",
                    [
                        [
                            "o_test_series_episode_1.mp4",
                            "https://www.kinoman.uz/api/v1/movie/online/"
                            "secure_id1_base64",
                            {"season": 1, "episode": 1, "title": "Test Series S01E1"},
                            None,
                        ],
                        [
                            "o_test_series_episode_2.mp4",
                            "https://www.kinoman.uz/api/v1/movie/online/"
                            "secure_id2_base64",
                            {"season": 1, "episode": 2, "title": "Test Series S01E2"},
                            None,
                        ],
                        [
                            "o_test_series_episode_3.mp4",
                            "https://www.kinoman.uz/api/v1/movie/online/"
                            "secure_id3_base64",
                            {"season": 1, "episode": 3, "title": "Test Series S01E3"},
                            None,
                        ],
                    ],
                )
            ]
        )

        self.assertDictEqual(
            kinoman_api._generate_movie_file_lists(test_files_data, "01"),
            expected_result,
        )

    def test_get_movie_files_list_movie(self):
        expected_result = [
            [
                "Воспроизвести (стрим)",
                "https://www.kinoman.uz/api/v1/movie/online/secure_id1_base64",
                None,
                None,
            ],
            [
                "Воспроизвести (SD)",
                "https://www.kinoman.uz/api/v1/movie/download/secure_id2_base64",
                None,
                "Видео: HDTVRIP (768x320)[CR]Аудио: профессиональное (многоголосое)",
            ],
            [
                "Воспроизвести (HD)",
                "https://www.kinoman.uz/api/v1/movie/download/secure_id3_base64",
                None,
                "Видео: HDTVRIP (1280x720)[CR]Аудио: профессиональное (многоголосое)",
            ],
            [
                "Воспроизвести (Full HD)",
                "https://www.kinoman.uz/api/v1/movie/download/secure_id4_base64",
                None,
                "Видео: BDRIP (1920x1080)[CR]Аудио: профессиональное (многоголосое)",
            ],
        ]

        self.assertListEqual(
            kinoman_api.get_movie_files_list(self.test_files_expected_result_movie),
            expected_result,
        )

    def test_get_movie_files_list_series_menu(self):
        expected_result = [
            ["Смотреть серии (стрим)", "online", None, None],
            ["Смотреть серии (SD)", "sd", None, None],
        ]

        self.assertListEqual(
            kinoman_api.get_movie_files_list(
                self.test_files_expected_result_series, season_n="01"
            ),
            expected_result,
        )

    def test_get_movie_files_list_series_category(self):
        expected_result = [
            [
                "o_test_series_s01e01.mp4",
                "https://www.kinoman.uz/api/v1/movie/online/secure_id1_base64",
                {"season": 1, "episode": 1, "title": "Test Series S01E01"},
                None,
            ],
            [
                "o_test_series_s01e02.mp4",
                "https://www.kinoman.uz/api/v1/movie/online/secure_id2_base64",
                {"season": 1, "episode": 2, "title": "Test Series S01E02"},
                None,
            ],
            [
                "o_test_series_s01e03.mp4",
                "https://www.kinoman.uz/api/v1/movie/online/secure_id3_base64",
                {"season": 1, "episode": 3, "title": "Test Series S01E03"},
                None,
            ],
        ]

        self.assertListEqual(
            kinoman_api.get_movie_files_list(
                self.test_files_expected_result_series,
                video_category="online",
                season_n="01",
            ),
            expected_result,
        )

    def test_get_movie_files_list_exception_empty_list(self):
        with self.assertRaises(kinoman_api.MissingVideoError):
            kinoman_api.get_movie_files_list({})

    def test_get_movie_files_list_exception_empty_category(self):
        with self.assertRaises(kinoman_api.MissingVideoError):
            kinoman_api.get_movie_files_list(
                {"fake_category": []}, video_category="online", season_n="01"
            )


class TestMenuGenerators(unittest.TestCase):
    @mock.patch("resources.kinoman_api.get_page")
    def test_list_genres(self, mock_get_page):
        test_data = {
            "genreList": [
                {"id": 1, "title": "Драма", "code": "drama"},
                {"id": 2, "title": "Фантастика", "code": "fantastic"},
                {"id": 3, "title": "Ужасы", "code": "horror"},
            ]
        }

        expected_result = [("Драма", 1), ("Ужасы", 3), ("Фантастика", 2)]

        mock_get_page.return_value = test_data

        self.assertListEqual(kinoman_api._list_genres(), expected_result)

    def test_gen_categories_video(self):
        expected_result = [
            (
                "Все категории",
                {"category": "all", "genre_black_list": 12, "content_type_id": 0},
            ),
            (
                "Фильмы",
                {"category": "movies", "genre_black_list": 12, "content_type_id": 1},
            ),
            (
                "Сериалы",
                {"category": "tv-series", "genre_black_list": 12, "content_type_id": 2},
            ),
            (
                "Мультфильмы",
                {"category": "cartoons", "genre_list": 12, "content_type_id": 0},
            ),
            (
                "ТВ-программы",
                {"category": "tv-shows", "genre_black_list": 12, "content_type_id": 3},
            ),
            (
                "Видеоблоги",
                {"category": "vlogs", "genre_black_list": 12, "content_type_id": 4},
            ),
        ]

        self.assertListEqual(list(kinoman_api.gen_categories_video()), expected_result)

    def test_gen_categories_age(self):
        expected_result = [
            ("Без ограничений", {}),
            ("Все возраста", {"age_rating_type": 0}),
            ("0", {"age_rating_type": 1}),
            ("0-12", {"age_rating_type": 2}),
            ("12-18", {"age_rating_type": 3}),
            ("18+", {"age_rating_type": 4}),
        ]

        self.assertListEqual(list(kinoman_api.gen_categories_age()), expected_result)

    @mock.patch("resources.kinoman_api._list_genres")
    def test_gen_categories_genre(self, mock_list_genres):
        test_genres = [("Драма", 1), ("Ужасы", 3), ("Фантастика", 2)]

        expected_result = [
            ("Все жанры", {}),
            ("Драма", {"genre_list": 1}),
            ("Ужасы", {"genre_list": 3}),
            ("Фантастика", {"genre_list": 2}),
        ]

        mock_list_genres.return_value = test_genres

        self.assertListEqual(list(kinoman_api.gen_categories_genre()), expected_result)

    @mock.patch("resources.kinoman_api.datetime")
    def test_gen_categories_year(self, mock_datetime):
        expected_result = [
            ("Все года", {}),
            ("1930", {"year": 1930}),
            ("1929", {"year": 1929}),
            ("1928", {"year": 1928}),
            ("1927", {"year": 1927}),
            ("1926", {"year": 1926}),
            ("1925", {"year": 1925}),
        ]

        mock_datetime.now().year = 1930

        self.assertListEqual(list(kinoman_api.gen_categories_year()), expected_result)

    @mock.patch("resources.kinoman_api.gen_categories_video")
    def test_list_categories_video_menu(self, mock_categories):
        test_categories = [
            (
                "Все категории",
                {"category": "all", "genre_black_list": 12, "content_type_id": 0},
            ),
            (
                "Фильмы",
                {"category": "movies", "genre_black_list": 12, "content_type_id": 1},
            ),
            (
                "Сериалы",
                {"category": "tv-series", "genre_black_list": 12, "content_type_id": 2},
            ),
        ]

        expected_result = [
            (
                "Фильмы",
                {"category": "movies", "genre_black_list": 12, "content_type_id": 1},
            ),
            (
                "Фильмы (премьеры)",
                {
                    "category": "movies",
                    "sort_type": 1,
                    "genre_black_list": 12,
                    "content_type_id": 1,
                },
            ),
            (
                "Сериалы",
                {"category": "tv-series", "genre_black_list": 12, "content_type_id": 2},
            ),
            (
                "Сериалы (премьеры)",
                {
                    "category": "tv-series",
                    "sort_type": 1,
                    "genre_black_list": 12,
                    "content_type_id": 2,
                },
            ),
            (
                "Избранное",
                {
                    "category": "favorite",
                    "favorite": True,
                    "content_type_id": 0,
                    "title": "избранное",
                },
            ),
        ]

        mock_categories.return_value = test_categories

        self.assertListEqual(
            list(kinoman_api.list_categories_video_menu()), expected_result
        )


class TestGetMovies(unittest.TestCase):
    @mock.patch("resources.kinoman_api.get_page")
    def test_get_movies_good(self, mock_get_page):
        test_query = {
            "page": 1,
            "sort_type": "0",
            "genre_list": "10",
            "genre_black_list": "12",
            "content_type_id": "1",
            "year": "2010",
            "age_rating_type": "0",
            "favorite": "0",
        }

        expected_query = {
            "page": 1,
            "sort_type": 0,
            "genre_list": [10],
            "genre_black_list": [12],
            "content_type_id": 1,
            "year": 2010,
            "age_rating_type": 0,
            "favorite": False,
        }

        test_movies = {
            "movies": [
                {
                    "id": 10001,
                    "title": "Test Movie 1",
                    "type_id": 1,
                    "release_date": "2019-10-02T05:00:00+05:00",
                    "poster_url": "img.kinoman.uz/p10001_00001",
                    "release_year": 2019,
                    "has_update": False,
                    "is_favorite": False,
                    "countries": "Country 1, Country 2, Country 3",
                },
                {
                    "id": 10002,
                    "title": "Test Movie 2",
                    "type_id": 1,
                    "release_date": "2019-01-22T05:00:00+05:00",
                    "poster_url": "img.kinoman.uz/p10002_00001",
                    "release_year": 2019,
                    "has_update": False,
                    "is_favorite": False,
                    "countries": "Country 4, Country 5, Country 6",
                },
                {
                    "id": 10003,
                    "title": "Test Movie 3",
                    "type_id": 1,
                    "release_date": "2019-02-01T05:00:00+05:00",
                    "poster_url": "img.kinoman.uz/p10003_00001",
                    "release_year": 2019,
                    "has_update": False,
                    "is_favorite": False,
                    "countries": "Country 7, Country 8",
                },
            ],
            "total_page": 10,
        }

        expected_result = [
            [
                "Test Movie 1 (2019)",
                10001,
                {
                    "info": {
                        "plot": "",
                        "year": 2019,
                        "premiered": "2019-10-02T05:00:00+05:00",
                        "title": "Test Movie 1 (2019)",
                    },
                    "art": {
                        "fanart": "https://img.kinoman.uz/p10001_00001mm.jpg",
                        "poster": "https://img.kinoman.uz/p10001_00001mm.jpg",
                        "banner": "https://img.kinoman.uz/p10001_00001mm.jpg",
                        "thumb": "https://img.kinoman.uz/p10001_00001mm.jpg",
                        "icon": "https://img.kinoman.uz/p10001_00001mm.jpg",
                    },
                    "properties": {
                        "Fanart_Image": "https://img.kinoman.uz/p10001_00001mm.jpg"
                    },
                },
            ],
            [
                "Test Movie 2 (2019)",
                10002,
                {
                    "info": {
                        "plot": "",
                        "year": 2019,
                        "premiered": "2019-01-22T05:00:00+05:00",
                        "title": "Test Movie 2 (2019)",
                    },
                    "art": {
                        "fanart": "https://img.kinoman.uz/p10002_00001mm.jpg",
                        "poster": "https://img.kinoman.uz/p10002_00001mm.jpg",
                        "banner": "https://img.kinoman.uz/p10002_00001mm.jpg",
                        "thumb": "https://img.kinoman.uz/p10002_00001mm.jpg",
                        "icon": "https://img.kinoman.uz/p10002_00001mm.jpg",
                    },
                    "properties": {
                        "Fanart_Image": "https://img.kinoman.uz/p10002_00001mm.jpg"
                    },
                },
            ],
            [
                "Test Movie 3 (2019)",
                10003,
                {
                    "info": {
                        "plot": "",
                        "year": 2019,
                        "premiered": "2019-02-01T05:00:00+05:00",
                        "title": "Test Movie 3 (2019)",
                    },
                    "art": {
                        "fanart": "https://img.kinoman.uz/p10003_00001mm.jpg",
                        "poster": "https://img.kinoman.uz/p10003_00001mm.jpg",
                        "banner": "https://img.kinoman.uz/p10003_00001mm.jpg",
                        "thumb": "https://img.kinoman.uz/p10003_00001mm.jpg",
                        "icon": "https://img.kinoman.uz/p10003_00001mm.jpg",
                    },
                    "properties": {
                        "Fanart_Image": "https://img.kinoman.uz/p10003_00001mm.jpg"
                    },
                },
            ],
            ["--> (2 / 10)", None, None],
        ]

        mock_get_page.return_value = test_movies

        self.assertListEqual(kinoman_api.get_movies(test_query), expected_result)
        mock_get_page.assert_called_once_with(
            "https://www.kinoman.uz/api/v1/movie/search_by_filter", expected_query, True
        )

    @mock.patch("resources.kinoman_api.get_page")
    def test_get_movies_search(self, mock_get_page):
        test_query = {"q": "test search"}

        mock_get_page.return_value = {"movies": []}

        self.assertListEqual(kinoman_api.get_movies(test_query), [])
        mock_get_page.assert_called_once_with(
            "https://www.kinoman.uz/api/v1/movie/search_by_name",
            {"q": "test search"},
            False,
        )


if __name__ == "__main__":
    unittest.main()
