# coding=utf-8
# pylint: disable=protected-access

import os
import re
import json
import unittest

from test.fake_player import FakePlayer

try:
    import mock
except ImportError:
    from unittest import mock

import urllib3
import requests

with mock.patch("sys.argv", ["plugin://test.plugin", "1", "/"]):
    from resources import kinoman_api

# kinoman.uz cert is invalid, disable SSL warnings
urllib3.disable_warnings()

KINOMAN_USER = os.getenv("KINOMAN_USER")
KINOMAN_PASS = os.getenv("KINOMAN_PASS")
KINOMAN_USER_ID = int(os.getenv("KINOMAN_USER_ID") or 0)


@unittest.skipUnless(
    all([KINOMAN_USER, KINOMAN_PASS]), "Need credentials for real test"
)
class TestKinomanLoginReal(unittest.TestCase):
    def setUp(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": kinoman_api.SPOOF_USER_AGENT})

    def kinoman_logout(self):
        self.session.post(
            "https://www.kinoman.uz/api/v1/user/logout", data="{}", verify=False
        )

        # requests' cookies cannot be retrieved directly if they are unset
        self.assertEqual(self.session.cookies.get_dict()["SESSIONID"], "")

    def tearDown(self):
        self.session.close()

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_good_cookie_expired(self, mock_player):
        mock_player.set_setting("_cookie", "")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", KINOMAN_USER)
        mock_player.set_setting("password", KINOMAN_PASS)

        self.assertTrue(kinoman_api._kinoman_login(self.session))

        mock_player.set_setting("_last_check", 0)

        self.assertTrue(kinoman_api._kinoman_login(self.session))
        self.assertIn("SESSIONID", json.loads(mock_player.get_setting("_cookie")))
        self.assertNotEqual(mock_player.get_setting("_last_check", "int"), 0)

        self.kinoman_logout()

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_good(self, mock_player):
        mock_player.set_setting("_cookie", "")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", KINOMAN_USER)
        mock_player.set_setting("password", KINOMAN_PASS)

        self.assertTrue(kinoman_api._kinoman_login(self.session))
        self.assertIn("SESSIONID", json.loads(mock_player.get_setting("_cookie")))
        self.assertEqual(mock_player.get_setting("_user_id", "int"), KINOMAN_USER_ID)

        self.kinoman_logout()

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_cookie_access_denied(self, mock_player):
        mock_player.set_setting("_cookie", "{}")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", "")
        mock_player.set_setting("password", "")

        with self.assertRaises(kinoman_api.LoginError):
            kinoman_api._kinoman_login(self.session)

    @mock.patch("resources.kinoman_api.player", new_callable=FakePlayer)
    def test_kinoman_login_bad(self, mock_player):
        mock_player.set_setting("_cookie", "")
        mock_player.set_setting("_last_check", 0)
        mock_player.set_setting("username", "fake_login")
        mock_player.set_setting("password", "fake_password")

        with self.assertRaises(kinoman_api.LoginError):
            kinoman_api._kinoman_login(self.session)


@unittest.skipUnless(
    all([KINOMAN_USER, KINOMAN_PASS]), "Need credentials for real test"
)
class TestKinomanAPIUpstream(unittest.TestCase):
    mock_player = None
    patcher = None

    @classmethod
    def setUpClass(cls):
        cls.patcher = mock.patch(
            "resources.kinoman_api.player", new_callable=FakePlayer
        )
        cls.mock_player = cls.patcher.start()

        cls.mock_player.set_setting("_cookie", "")
        cls.mock_player.set_setting("_last_check", 0)
        cls.mock_player.set_setting("username", KINOMAN_USER)
        cls.mock_player.set_setting("password", KINOMAN_PASS)

        session = requests.Session()
        session.headers.update({"User-Agent": kinoman_api.SPOOF_USER_AGENT})

        cls.login_success = kinoman_api._kinoman_login(session)

        session.close()

    def setUp(self):
        if not self.login_success:
            self.fail("Failed to login for test")

    @classmethod
    def tearDownClass(cls):
        session = requests.Session()
        session.headers.update({"User-Agent": kinoman_api.SPOOF_USER_AGENT})
        session.cookies.update(json.loads(cls.mock_player.get_setting("_cookie")))

        session.post(
            "https://www.kinoman.uz/api/v1/user/logout", data="{}", verify=False
        )

        session.close()

        cls.patcher.stop()

    def check_filed_types(self, data, expected_fields):
        for f_name, f_type in expected_fields:
            self.assertIn(f_name, data)

            if hasattr(f_type, "match"):
                self.assertIsNotNone(f_type.match(data[f_name]))
            else:
                self.assertIsInstance(data[f_name], f_type)

    def test_upstream_movie_data(self):
        movie_url = "https://www.kinoman.uz/api/v1/movie/details/73"
        movie_expected_result = {
            "movie": {
                "id": 73,
                "title": "Пираты Карибского моря: На краю Света",
                "type_id": 1,
                "release_date": "2007-05-19T05:00:00+05:00",
                "poster_url": "img.kinoman.uz/p73_20383",
                "release_year": 2007,
                "has_update": False,
                "is_favorite": False,
                "alt_title": "",
                "original_title": "Pirates of the Caribbean: At Worlds End",
                "description": "<p>Новые приключения Джека Спэрроу и его друзей Уилла"
                " Тернера и Элизабет Суонн. На этот раз Уиллу и Элизабет придется"
                " объединиться с самим Капитаном Барбоссой для того, чтобы отправиться"
                " на край света и спасти своего друга — Джека «Воробья». Ситуация"
                " осложняется тем, что Элизабет похищают китайские пираты…</p>",
                "age_rating": 12,
                "kinopoisk_url": None,
                "imdb_rating": 7.1,
                "kp_rating": 8.014,
                "countries": [{"id": 334, "title": "США"}],
                "genres": [
                    {"id": 13, "title": "приключения"},
                    {"id": 23, "title": "фэнтези"},
                    {"id": 7, "title": "боевик"},
                ],
                "directors": [{"id": 16, "title": "Гор Вербински"}],
                "actors": [
                    {"id": 1, "title": "Джонни Депп"},
                    {"id": 2, "title": "Джеффри Раш"},
                    {"id": 3, "title": "Орландо Блум"},
                    {"id": 4, "title": "Кира Найтли"},
                    {"id": 5, "title": "Джек Дэвенпорт"},
                    {"id": 6, "title": "Билл Найи"},
                    {"id": 7, "title": "Джонатан Прайс"},
                    {"id": 8, "title": "Ли Аренберг"},
                    {"id": 9, "title": "Макинзи Крук"},
                    {"id": 10, "title": "Кевин МакНелли"},
                    {"id": 11, "title": "Стеллан Скарсгард"},
                    {"id": 12, "title": "Том Холландер"},
                    {"id": 13, "title": "Чоу Юн-Фат"},
                    {"id": 14, "title": "Наоми Харрис"},
                    {"id": 15, "title": "Кейт Ричардс"},
                ],
                "online_files": [
                    {
                        "id": 0,
                        "secure_id": None,
                        "title": "o_pirates_of_the_caribbean_at_worlds_end_2007"
                        "_1080p.mp4",
                        "url": "",
                        "width": 1920,
                        "height": 800,
                    }
                ],
                "download_files": [
                    {
                        "file_id": 0,
                        "secure_id": None,
                        "file_name": "pirates_of_the_caribbean_at_worlds_end_2007"
                        "_1080p.mkv",
                        "title": "дублированное",
                        "name": "BDRIP",
                        "file_size": "8335527775",
                        "width": "1920",
                        "height": "800",
                        "lang_title": "русский и английский",
                    }
                ],
                "screenshots": [
                    {"id": 70432, "title": "img.kinoman.uz/s73_70432"},
                    {"id": 70433, "title": "img.kinoman.uz/s73_70433"},
                    {"id": 70434, "title": "img.kinoman.uz/s73_70434"},
                    {"id": 70435, "title": "img.kinoman.uz/s73_70435"},
                    {"id": 70436, "title": "img.kinoman.uz/s73_70436"},
                    {"id": 70437, "title": "img.kinoman.uz/s73_70437"},
                    {"id": 70438, "title": "img.kinoman.uz/s73_70438"},
                    {"id": 70439, "title": "img.kinoman.uz/s73_70439"},
                    {"id": 70440, "title": "img.kinoman.uz/s73_70440"},
                    {"id": 70441, "title": "img.kinoman.uz/s73_70441"},
                    {"id": 70442, "title": "img.kinoman.uz/s73_70442"},
                    {"id": 70443, "title": "img.kinoman.uz/s73_70443"},
                    {"id": 70444, "title": "img.kinoman.uz/s73_70444"},
                    {"id": 70445, "title": "img.kinoman.uz/s73_70445"},
                    {"id": 70446, "title": "img.kinoman.uz/s73_70446"},
                    {"id": 70447, "title": "img.kinoman.uz/s73_70447"},
                    {"id": 70448, "title": "img.kinoman.uz/s73_70448"},
                ],
                "trailers": [],
            }
        }

        series_url = "https://www.kinoman.uz/api/v1/movie/details/166"
        series_expected_result = {
            "movie": {
                "id": 166,
                "title": "Мастер и Маргарита",
                "type_id": 2,
                "release_date": "2005-12-19T05:00:00+05:00",
                "poster_url": "img.kinoman.uz/p166_20624",
                "release_year": 2005,
                "has_update": False,
                "is_favorite": False,
                "alt_title": "",
                "original_title": "Мастер и Маргарита",
                "description": "<p>Однажды весною, в час небывало жаркого заката, в"
                " Москве, на Патриарших прудах, появились два гражданина. Первый из"
                " них, одетый в летнюю серенькую пару, был маленького роста, упитан,"
                " лыс, свою приличную шляпу пирожком нес в руке, а на хорошо выбритом"
                " лице его помещались сверхъестественных размеров очки в черной"
                " роговой оправе. Второй — плечистый, рыжеватый, вихрастый молодой"
                " человек в заломленной на затылок клетчатой кепке — был в ковбойке,"
                " жеваных белых брюках и в черных тапочках.</p>",
                "age_rating": 18,
                "kinopoisk_url": None,
                "imdb_rating": 7.5,
                "kp_rating": 7.8,
                "countries": [{"id": 337, "title": "Россия"}],
                "genres": [
                    {"id": 5, "title": "триллер"},
                    {"id": 14, "title": "мелодрама"},
                    {"id": 1, "title": "драма"},
                    {"id": 9, "title": "детектив"},
                ],
                "directors": [{"id": 788, "title": "Владимир Бортко"}],
                "actors": [
                    {"id": 780, "title": "Анна Ковальчук"},
                    {"id": 781, "title": "Александр Галибин"},
                    {"id": 782, "title": "Олег Басилашвили"},
                    {"id": 93, "title": "Владислав Галкин"},
                    {"id": 783, "title": "Кирилл Лавров"},
                    {"id": 784, "title": "Александр Абдулов"},
                    {"id": 785, "title": "Александр Филиппенко"},
                    {"id": 786, "title": "Сергей Безруков"},
                    {"id": 329, "title": "Александр Баширов"},
                    {"id": 787, "title": "Семен Фурман"},
                ],
                "online_files": [
                    {
                        "id": 0,
                        "secure_id": None,
                        "title": "o_the_master_and_margarita_s01e01.mp4",
                        "url": "",
                        "width": 856,
                        "height": 480,
                    },
                    {
                        "id": 0,
                        "secure_id": None,
                        "title": "o_the_master_and_margarita_s01e02.mp4",
                        "url": "",
                        "width": 856,
                        "height": 480,
                    },
                    {
                        "id": 0,
                        "secure_id": None,
                        "title": "o_the_master_and_margarita_s01e03.mp4",
                        "url": "",
                        "width": 856,
                        "height": 480,
                    },
                    {
                        "id": 0,
                        "secure_id": None,
                        "title": "o_the_master_and_margarita_s01e04.mp4",
                        "url": "",
                        "width": 856,
                        "height": 480,
                    },
                    {
                        "id": 0,
                        "secure_id": None,
                        "title": "o_the_master_and_margarita_s01e05.mp4",
                        "url": "",
                        "width": 856,
                        "height": 480,
                    },
                    {
                        "id": 0,
                        "secure_id": None,
                        "title": "o_the_master_and_margarita_s01e06.mp4",
                        "url": "",
                        "width": 856,
                        "height": 480,
                    },
                    {
                        "id": 0,
                        "secure_id": None,
                        "title": "o_the_master_and_margarita_s01e07.mp4",
                        "url": "",
                        "width": 856,
                        "height": 480,
                    },
                    {
                        "id": 0,
                        "secure_id": None,
                        "title": "o_the_master_and_margarita_s01e08.mp4",
                        "url": "",
                        "width": 856,
                        "height": 480,
                    },
                    {
                        "id": 0,
                        "secure_id": None,
                        "title": "o_the_master_and_margarita_s01e09.mp4",
                        "url": "",
                        "width": 856,
                        "height": 480,
                    },
                    {
                        "id": 0,
                        "secure_id": None,
                        "title": "o_the_master_and_margarita_s01e10.mp4",
                        "url": "",
                        "width": 856,
                        "height": 480,
                    },
                ],
                "download_files": [
                    {
                        "file_id": 0,
                        "secure_id": None,
                        "file_name": "the_master_and_margarita_s01e01.mp4",
                        "title": "оригинал",
                        "name": "HDTVRIP",
                        "file_size": "1243673396",
                        "width": "856",
                        "height": "480",
                        "lang_title": "русский",
                    },
                    {
                        "file_id": 0,
                        "secure_id": None,
                        "file_name": "the_master_and_margarita_s01e02.mp4",
                        "title": "оригинал",
                        "name": "HDTVRIP",
                        "file_size": "1322074838",
                        "width": "856",
                        "height": "480",
                        "lang_title": "русский",
                    },
                    {
                        "file_id": 0,
                        "secure_id": None,
                        "file_name": "the_master_and_margarita_s01e03.mp4",
                        "title": "оригинал",
                        "name": "HDTVRIP",
                        "file_size": "1382619317",
                        "width": "856",
                        "height": "480",
                        "lang_title": "русский",
                    },
                    {
                        "file_id": 0,
                        "secure_id": None,
                        "file_name": "the_master_and_margarita_s01e04.mp4",
                        "title": "оригинал",
                        "name": "HDTVRIP",
                        "file_size": "1350140037",
                        "width": "856",
                        "height": "480",
                        "lang_title": "русский",
                    },
                    {
                        "file_id": 0,
                        "secure_id": None,
                        "file_name": "the_master_and_margarita_s01e05.mp4",
                        "title": "оригинал",
                        "name": "HDTVRIP",
                        "file_size": "1350021253",
                        "width": "856",
                        "height": "480",
                        "lang_title": "русский",
                    },
                    {
                        "file_id": 0,
                        "secure_id": None,
                        "file_name": "the_master_and_margarita_s01e06.mp4",
                        "title": "оригинал",
                        "name": "HDTVRIP",
                        "file_size": "1360818170",
                        "width": "856",
                        "height": "480",
                        "lang_title": "русский",
                    },
                    {
                        "file_id": 0,
                        "secure_id": None,
                        "file_name": "the_master_and_margarita_s01e07.mp4",
                        "title": "оригинал",
                        "name": "HDTVRIP",
                        "file_size": "1325699101",
                        "width": "856",
                        "height": "480",
                        "lang_title": "русский",
                    },
                    {
                        "file_id": 0,
                        "secure_id": None,
                        "file_name": "the_master_and_margarita_s01e08.mp4",
                        "title": "оригинал",
                        "name": "HDTVRIP",
                        "file_size": "1426852709",
                        "width": "856",
                        "height": "480",
                        "lang_title": "русский",
                    },
                    {
                        "file_id": 0,
                        "secure_id": None,
                        "file_name": "the_master_and_margarita_s01e09.mp4",
                        "title": "оригинал",
                        "name": "HDTVRIP",
                        "file_size": "1405376019",
                        "width": "856",
                        "height": "480",
                        "lang_title": "русский",
                    },
                    {
                        "file_id": 0,
                        "secure_id": None,
                        "file_name": "the_master_and_margarita_s01e10.mp4",
                        "title": "оригинал",
                        "name": "HDTVRIP",
                        "file_size": "1334563166",
                        "width": "856",
                        "height": "480",
                        "lang_title": "русский",
                    },
                ],
                "screenshots": [
                    {"id": 71454, "title": "img.kinoman.uz/s166_71454"},
                    {"id": 71455, "title": "img.kinoman.uz/s166_71455"},
                    {"id": 71456, "title": "img.kinoman.uz/s166_71456"},
                ],
                "trailers": [],
            }
        }

        movie_data = kinoman_api.get_page(movie_url)
        series_data = kinoman_api.get_page(series_url)

        # secure_id's are generated each time, so bypass them for the test
        for data in (movie_data, series_data):
            for file_type in ("online_files", "download_files"):
                for i, _ in enumerate(data["movie"][file_type]):
                    data["movie"][file_type][i]["secure_id"] = None

        self.maxDiff = None
        self.assertEqual(movie_expected_result, movie_data)
        self.assertEqual(series_expected_result, series_data)

    def test_upstream_genres(self):
        genres_data = kinoman_api.get_page("https://www.kinoman.uz/api/v1/genre/all")

        # expected
        # {"genreList": [{"id": 1, "title": "Драма", "code": "drama"}, ...]}

        expected_fields = [("id", int), ("title", str), ("code", str)]

        self.assertIn("genreList", genres_data)
        if not genres_data["genreList"]:
            self.fail("Upstream returned empty data for test")
        self.check_filed_types(genres_data["genreList"][0], expected_fields)

    def test_upstream_search(self):
        # 2 payloads - for name search and for filter search, result must be similar
        test_searches = [
            (
                "https://www.kinoman.uz/api/v1/movie/search_by_name",
                {"q": "Мастер и маргарита"},
                False,
            ),
            (
                "https://www.kinoman.uz/api/v1/movie/search_by_filter",
                {
                    "category": "movies",
                    "content_type_id": 1,
                    "genre_black_list": [12],
                    "genre_list": [],
                    "page": 1,
                    "sort_type": 0,
                },
                True,
            ),
        ]

        for search_url, search_payload, user_id_required in test_searches:
            search_data = kinoman_api.get_page(
                search_url, search_payload, user_id_required
            )

            # expected
            # {"movies": [{"id": 6208, "title": "Черная Пантера (3d-фильм)",
            # "type_id": 1, "release_date": "2018-02-12T05:00:00+05:00",
            # "poster_url": "img.kinoman.uz/p6208_27918", "release_year": 2018,
            # "has_update": false, "is_favorite": false, "countries": "США"}, ...],
            #  "total_page": 169 <- OPTIONAL, ONLY WHEN TOO MANY RESULTS
            #  }

            expected_fields = [
                ("id", int),
                ("title", str),
                ("type_id", int),
                ("release_date", re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T.*$")),
                ("poster_url", re.compile(r"^img\.kinoman\.uz/p[0-9]+_[0-9]+$")),
                ("release_year", int),
                ("has_update", bool),
                ("is_favorite", bool),
                ("countries", str),
            ]

            self.assertIn("movies", search_data)
            # Check paginator for big result
            if "category" in search_payload:
                self.assertIn("total_page", search_data)
            if not search_data["movies"]:
                self.fail("Upstream returned empty data for test")
            self.check_filed_types(search_data["movies"][0], expected_fields)

    def test_upstream_video_url(self):
        data = kinoman_api.get_page("https://www.kinoman.uz/api/v1/movie/details/166")

        test_video_types = (
            (
                "online_files",
                "https://www.kinoman.uz/api/v1/movie/online/{}",
                r"^https://online[0-9]+\.kinoman\.uz/dl/online/[0-9]+/o_.*\.mp4$",
            ),
            (
                "download_files",
                "https://www.kinoman.uz/api/v1/movie/download/{}",
                r"^https://dl[0-9]+\.kinoman\.uz/dl/movie/[0-9]+/.*\.\w+$",
            ),
        )

        for v_type, v_url, v_regex in test_video_types:
            url_data = kinoman_api.get_page(
                v_url.format(data["movie"][v_type][0]["secure_id"])
            )

            # expected
            # online
            # {'url': 'https://online04.kinoman.uz/dl/online/46170/o_the_master_and"
            # "_margarita_s01e01.mp4'}
            # download
            # {'url': 'https://dl04.kinoman.uz/dl/movie/46170/the_master_and"
            # "_margarita_s01e01.mp4'}

            self.assertIn("url", url_data)
            self.assertRegexpMatches(url_data["url"], v_regex)


if __name__ == "__main__":
    unittest.main()
