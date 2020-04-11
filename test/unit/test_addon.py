# coding=utf-8
# pylint: disable=no-self-use

import unittest

from test.fake_player import FakePlayer

try:
    import mock
except ImportError:
    from unittest import mock


def fake_path_for(endpoint, query=None, path_vars=None):
    return endpoint, query, path_vars


with mock.patch("sys.argv", ["plugin://test.plugin", "1", "/"]):
    import addon


@mock.patch("addon.path_for", fake_path_for)
class TestAddonMenus(unittest.TestCase):
    @mock.patch("addon.player", new_callable=FakePlayer)
    @mock.patch("addon.kinoman_api")
    def test_root(self, mock_kinoman_api, mock_player):
        test_categories = [
            ("All categories", {"test_cat_id": 0}),
            ("Category 1", {"test_cat_id": 1}),
            ("Category 2", {"test_cat_id": 2}),
        ]

        mock_kinoman_api.list_categories_video_menu.return_value = test_categories
        mock_player.print_items = mock.MagicMock()

        addon.root()

        expected_result = [
            {
                "path": ("list_movies", {"test_cat_id": 0}, None),
                "is_folder": True,
                "label": "All categories",
            },
            {
                "path": ("list_movies", {"test_cat_id": 1}, None),
                "is_folder": True,
                "label": "Category 1",
            },
            {
                "path": ("list_movies", {"test_cat_id": 2}, None),
                "is_folder": True,
                "label": "Category 2",
            },
            {
                "path": ("search_filter", None, None),
                "is_folder": True,
                "video_data": {"art": {"icon": "DefaultAddonsSearch.png"}},
                "label": "Поиск по фильтру",
            },
            {
                "path": ("search", None, None),
                "is_folder": True,
                "video_data": {"art": {"icon": "DefaultAddonsSearch.png"}},
                "label": "Поиск",
            },
        ]

        mock_player.print_items.assert_called_once_with(expected_result, cache=False)

    @mock.patch("addon.player", new_callable=FakePlayer)
    @mock.patch("addon.kinoman_api")
    def test_root_history(self, mock_kinoman_api, mock_player):
        mock_kinoman_api.list_categories_video_menu.return_value = []
        mock_player.print_items = mock.MagicMock()

        mock_player.set_setting("search_history_status", True)
        mock_player.set_setting("_search_history", ["test"])

        addon.root()

        expected_result = [
            {
                "path": ("search_filter", None, None),
                "is_folder": True,
                "video_data": {"art": {"icon": "DefaultAddonsSearch.png"}},
                "label": "Поиск по фильтру",
            },
            {
                "path": ("search_history", None, None),
                "is_folder": True,
                "video_data": {"art": {"icon": "DefaultAddonsSearch.png"}},
                "label": "Поиск",
            },
        ]

        mock_player.print_items.assert_called_once_with(expected_result, cache=False)

    @mock.patch("addon.player", new_callable=FakePlayer)
    @mock.patch("addon.kinoman_api")
    def test_list_movies(self, mock_kinoman_api, mock_player):
        test_movie_list = [
            ["Test Movie 1 (2019)", 10001, {}],
            ["--> (2 / 10)", None, None],
        ]

        mock_kinoman_api.get_movies.return_value = test_movie_list
        mock_player.print_items = mock.MagicMock()

        addon.list_movies({"test_param": "test"})

        expected_result = [
            {
                "path": ("open_movie", None, {"video_id": 10001}),
                "is_folder": True,
                "video_data": {},
                "label": "Test Movie 1 (2019)",
            },
            {
                "path": ("list_movies", {"test_param": "test", "page": 2}, None),
                "is_folder": True,
                "video_data": None,
                "label": "--> (2 / 10)",
            },
        ]

        mock_kinoman_api.get_movies.assert_called_once_with(
            {"test_param": "test", "page": 1}
        )
        mock_player.print_items.assert_called_once_with(
            expected_result, content_type="movies"
        )

    @mock.patch("addon.player", new_callable=FakePlayer)
    @mock.patch("addon.kinoman_api")
    def test_search_filter(self, mock_kinoman_api, mock_player):
        test_movie_list = [
            ("Category 1", {"test_cat_id": 1}),
            ("Category 2", {"test_cat_id": 2}),
        ]

        mock_kinoman_api.gen_categories_video.return_value = test_movie_list
        mock_kinoman_api.gen_categories_year.return_value = test_movie_list

        mock_player.print_items = mock.MagicMock()

        # First and middle menus
        addon.search_filter()

        expected_result = [
            {
                "path": ("search_filter", {"test_cat_id": 2}, {"step": 1}),
                "is_folder": True,
                "label": "Category 1",
            },
            {
                "path": ("search_filter", {"test_cat_id": 2}, {"step": 1}),
                "is_folder": True,
                "label": "Category 2",
            },
        ]

        mock_player.print_items.assert_called_once_with(expected_result)

        # Final menu, leading to actual movies list
        mock_player.print_items.reset_mock()
        addon.search_filter({"test_param": "test"}, 3)

        expected_result = [
            {
                "path": ("list_movies", {"test_param": "test", "test_cat_id": 2}, None),
                "is_folder": True,
                "label": "Category 1",
            },
            {
                "path": ("list_movies", {"test_param": "test", "test_cat_id": 2}, None),
                "is_folder": True,
                "label": "Category 2",
            },
        ]

        mock_player.print_items.assert_called_once_with(expected_result)

    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_search_noinput(self, mock_player):
        mock_player.dialog_keyboard = mock.MagicMock()
        mock_player.dialog_keyboard.return_value = None

        addon.search()

        mock_player.dialog_keyboard.assert_called_once()

    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_search_empty(self, mock_player):
        mock_player.dialog_keyboard = mock.MagicMock()
        mock_player.dialog_keyboard.return_value = ""
        mock_player.dialog_ok = mock.MagicMock()

        addon.search()

        mock_player.dialog_keyboard.assert_called_once()
        mock_player.dialog_ok.assert_called_once()

    @mock.patch("addon.list_movies")
    @mock.patch("addon.player", FakePlayer())
    def test_search_query(self, mock_list):
        addon.search("test query")
        mock_list.assert_called_once_with(query={"q": "test query"})

    @mock.patch("addon.list_movies", mock.MagicMock())
    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_search_query_history_add(self, mock_player):
        test_history = ["test1", "test2", "test3", "test4", "test5", "test6", "test7"]

        mock_player.set_setting("search_history_status", True)
        mock_player.set_setting("_search_history", test_history)

        addon.search("test3")

        expected_result = ["test2", "test4", "test5", "test6", "test7", "test3"]
        self.assertListEqual(
            mock_player.get_setting("_search_history", "list"), expected_result
        )

    @mock.patch("addon.search_clear")
    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_search_history_disabled(self, mock_player, mock_clear):
        mock_player.set_setting("search_history_status", False)
        mock_player.print_items = mock.MagicMock()

        addon.search_history()

        mock_clear.assert_called_once()

    @mock.patch("addon.search_clear", mock.MagicMock())
    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_search_menu(self, mock_player):
        mock_player.set_setting("search_history_status", True)
        mock_player.set_setting("_search_history", ["test1", "test2", "test3"])

        mock_player.print_items = mock.MagicMock()

        addon.search_history()

        expected_result = [
            {
                "path": ("search", None, None),
                "is_folder": True,
                "video_data": {"art": {"icon": "DefaultAddonsSearch.png"}},
                "label": "Новый поиск",
            },
            {
                "path": ("search_clear", None, None),
                "is_folder": True,
                "video_data": {"art": {"icon": "DefaultAddonNone.png"}},
                "label": "Очистить",
            },
            {
                "path": ("search", None, {"s_query": "test3"}),
                "is_folder": True,
                "label": "test3",
            },
            {
                "path": ("search", None, {"s_query": "test2"}),
                "is_folder": True,
                "label": "test2",
            },
            {
                "path": ("search", None, {"s_query": "test1"}),
                "is_folder": True,
                "label": "test1",
            },
        ]

        mock_player.print_items.assert_called_once_with(expected_result)

    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_search_clear(self, mock_player):
        mock_player.set_setting("_search_history", ["test1", "test2", "test3"])

        mock_player.redirect_in_place = mock.MagicMock()

        addon.search_clear()

        self.assertListEqual(mock_player.get_setting("_search_history", "list"), [])
        mock_player.redirect_in_place.assert_called_once_with(("root", None, None))

    @mock.patch("addon.kinoman_api")
    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_play(self, mock_player, mock_kinoman):
        url_actual_video = "https://test.com/actual_video.mp4"

        test_args = [100, "online", "video.mp4"]

        mock_player.play = mock.MagicMock()
        mock_kinoman.get_video_url.return_value = url_actual_video

        addon.play(*test_args)

        mock_kinoman.get_video_url.assert_called_once_with(*test_args)
        mock_player.play.assert_called_once_with(url_actual_video)

    @mock.patch("addon.resolve")
    @mock.patch("addon.kinoman_api")
    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_main_error_login_error(self, mock_player, mock_kinoman, mock_resolve):
        mock_kinoman.LoginError = Exception
        mock_resolve.side_effect = mock_kinoman.LoginError("test login error")
        mock_player.get_current_url = mock.MagicMock()
        mock_player.dialog_ok = mock.MagicMock()

        addon.main()

        mock_player.dialog_ok.assert_called_once_with(
            "Kinoman.Uz", "Ошибка авторизации: test login error"
        )

    @mock.patch("addon.resolve")
    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_main_error_missing_video(self, mock_player, mock_resolve):
        mock_resolve.side_effect = addon.kinoman_api.MissingVideoError
        mock_player.get_current_url = mock.MagicMock()
        mock_player.dialog_ok = mock.MagicMock()

        addon.main()

        mock_player.dialog_ok.assert_called_once_with("Kinoman.Uz", "Видео отсутствует")

    @mock.patch("addon.resolve")
    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_main_error_network(self, mock_player, mock_resolve):
        mock_resolve.side_effect = addon.kinoman_api.NetworkError
        mock_player.get_current_url = mock.MagicMock()
        mock_player.dialog_ok = mock.MagicMock()

        addon.main()

        mock_player.dialog_ok.assert_called_once_with(
            "Kinoman.Uz", "Проблема сети, попробуйте позже"
        )

    @mock.patch("addon.resolve", mock.MagicMock())
    @mock.patch("addon.kinoman_api", mock.MagicMock())
    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_main_no_errors(self, mock_player):
        mock_player.get_current_url = mock.MagicMock()
        mock_player.dialog_ok = mock.MagicMock()

        addon.main()

        mock_player.dialog_ok.assert_not_called()


@mock.patch("addon.path_for", fake_path_for)
class TestOpenMovie(unittest.TestCase):
    @mock.patch("addon.kinoman_api")
    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_open_movie(self, mock_player, mock_kinoman):
        test_movie_data = {
            "movie_info": {"info": {"plot": "Test description"}},
            "file_lists": [],
            "series_season_n": None,
        }

        test_files_list = [
            [
                "online",
                "video1_online.mp4",
                "Воспроизвести (стрим)",
                "https://test.com/video1",
                None,
                None,
            ],
            [
                "sd",
                "video1.mkv",
                "Воспроизвести (SD)",
                "https://test.com/video2",
                None,
                "Video type info",
            ],
        ]

        mock_player.print_items = mock.MagicMock()
        mock_kinoman.get_movie_data.return_value = test_movie_data
        mock_kinoman.get_movie_files_list.return_value = test_files_list

        addon.open_movie(1000)

        expected_result = [
            {
                "path": (
                    "play",
                    None,
                    {
                        "video_id": 1000,
                        "video_type": "online",
                        "video_name": "video1_online.mp4",
                    },
                ),
                "video_data": {"info": {"plot": "Test description"}},
                "is_folder": False,
                "is_playable": True,
                "label": "Воспроизвести (стрим)",
            },
            {
                "path": (
                    "play",
                    None,
                    {"video_id": 1000, "video_type": "sd", "video_name": "video1.mkv"},
                ),
                "video_data": {
                    "info": {"plot": "[B]Video type info[/B][CR][CR]Test description"}
                },
                "is_folder": False,
                "is_playable": True,
                "label": "Воспроизвести (SD)",
            },
        ]

        mock_kinoman.get_movie_data.assert_called_once_with(1000)
        mock_kinoman.get_movie_files_list.assert_called_once_with(
            test_movie_data["file_lists"], None, test_movie_data["series_season_n"]
        )

        mock_player.print_items.assert_called_once_with(
            expected_result, content_type="movies"
        )

    @mock.patch("addon.kinoman_api")
    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_open_series_dir(self, mock_player, mock_kinoman):
        test_movie_data = {
            "movie_info": {"info": {"plot": "Test description"}},
            "file_lists": [],
            "series_season_n": "01",
        }

        test_files_list = [
            ["dir", None, "Смотреть серии (стрим)", "online", None, None],
            ["dir", None, "Смотреть серии (SD)", "sd", None, None],
        ]

        mock_player.print_items = mock.MagicMock()
        mock_kinoman.get_movie_data.return_value = test_movie_data
        mock_kinoman.get_movie_files_list.return_value = test_files_list

        addon.open_movie(1000)

        expected_result = [
            {
                "path": ("open_movie", None, {"video_dir": "online", "video_id": 1000}),
                "video_data": {"info": {"plot": "Test description"}},
                "is_folder": True,
                "is_playable": False,
                "label": "Смотреть серии (стрим)",
            },
            {
                "path": ("open_movie", None, {"video_dir": "sd", "video_id": 1000}),
                "video_data": {"info": {"plot": "Test description"}},
                "is_folder": True,
                "is_playable": False,
                "label": "Смотреть серии (SD)",
            },
        ]

        mock_kinoman.get_movie_data.assert_called_once_with(1000)
        mock_kinoman.get_movie_files_list.assert_called_once_with(
            test_movie_data["file_lists"], None, test_movie_data["series_season_n"]
        )

        mock_player.print_items.assert_called_once_with(
            expected_result, content_type="movies"
        )

    @mock.patch("addon.kinoman_api")
    @mock.patch("addon.player", new_callable=FakePlayer)
    def test_open_series_files(self, mock_player, mock_kinoman):
        test_movie_data = {
            "movie_info": {"info": {"plot": "Test description"}},
            "file_lists": [],
            "series_season_n": "01",
        }

        test_files_list = [
            [
                "online",
                "o_test_series_s01e01.mp4",
                "o_test_series_s01e01.mp4",
                "https://www.kinoman.uz/api/v1/movie/online/secure_id1_base64",
                {"season": 1, "episode": 1, "title": "Test Series S01E01"},
                None,
            ],
            [
                "online",
                "o_test_series_s01e02.mp4",
                "o_test_series_s01e02.mp4",
                "https://www.kinoman.uz/api/v1/movie/online/secure_id2_base64",
                {"season": 1, "episode": 2, "title": "Test Series S01E02"},
                None,
            ],
            [
                "online",
                "o_test_series_s01e03.mp4",
                "o_test_series_s01e03.mp4",
                "https://www.kinoman.uz/api/v1/movie/online/secure_id3_base64",
                {"season": 1, "episode": 3, "title": "Test Series S01E03"},
                None,
            ],
        ]

        mock_player.print_items = mock.MagicMock()
        mock_kinoman.get_movie_data.return_value = test_movie_data
        mock_kinoman.get_movie_files_list.return_value = test_files_list

        addon.open_movie(1000, "online")

        expected_result = [
            {
                "path": (
                    "play",
                    None,
                    {
                        "video_id": 1000,
                        "video_type": "online",
                        "video_name": "o_test_series_s01e01.mp4",
                    },
                ),
                "video_data": {
                    "info": {
                        "plot": "Test description",
                        "title": "Test Series S01E01",
                        "episode": 1,
                        "season": 1,
                    }
                },
                "is_folder": False,
                "is_playable": True,
                "label": "o_test_series_s01e01.mp4",
            },
            {
                "path": (
                    "play",
                    None,
                    {
                        "video_id": 1000,
                        "video_type": "online",
                        "video_name": "o_test_series_s01e02.mp4",
                    },
                ),
                "video_data": {
                    "info": {
                        "plot": "Test description",
                        "title": "Test Series S01E02",
                        "episode": 2,
                        "season": 1,
                    }
                },
                "is_folder": False,
                "is_playable": True,
                "label": "o_test_series_s01e02.mp4",
            },
            {
                "path": (
                    "play",
                    None,
                    {
                        "video_id": 1000,
                        "video_type": "online",
                        "video_name": "o_test_series_s01e03.mp4",
                    },
                ),
                "video_data": {
                    "info": {
                        "plot": "Test description",
                        "title": "Test Series S01E03",
                        "episode": 3,
                        "season": 1,
                    }
                },
                "is_folder": False,
                "is_playable": True,
                "label": "o_test_series_s01e03.mp4",
            },
        ]

        mock_kinoman.get_movie_data.assert_called_once_with(1000)
        mock_kinoman.get_movie_files_list.assert_called_once_with(
            test_movie_data["file_lists"], "online", test_movie_data["series_season_n"]
        )

        mock_player.print_items.assert_called_once_with(
            expected_result, content_type="episodes"
        )


if __name__ == "__main__":
    unittest.main()
