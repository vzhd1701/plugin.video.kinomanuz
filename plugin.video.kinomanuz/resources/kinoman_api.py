# coding=utf-8

import re
import time
import json
import random

from datetime import datetime
from collections import OrderedDict

import requests

from resources.internal import player


class LoginError(BaseException):
    """Exception for login errors"""


class MissingVideoError(BaseException):
    """Exception for missing video errors"""


class NetworkError(BaseException):
    """Exception for network related errors"""


SPOOF_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:70.0) Gecko/20100101 Firefox/70.0"
)


# https://stackoverflow.com/a/33571117
# Hack to get UTF-8 strings instead of \u crap
def _json_loads_byteified(json_text):
    return _byteify(json.loads(json_text, object_hook=_byteify), ignore_dicts=True)


def _byteify(data, ignore_dicts=False):
    # if this is a unicode string, return its string representation
    try:  # pragma: no cover
        # noinspection PyUnresolvedReferences
        if isinstance(data, unicode):
            return data.encode("utf-8")
    except NameError:  # pragma: no cover
        pass

    # if this is a list of values, return list of byteified values
    if isinstance(data, list):
        return [_byteify(item, ignore_dicts=True) for item in data]
    # if this is a dictionary, return dictionary of byteified keys and values
    # but only if we haven't already byteified it
    if isinstance(data, dict) and not ignore_dicts:
        return {
            _byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
            for key, value in data.items()
        }
    # if it's anything else, return it in its original form
    return data


def _cleanhtml(raw_html):
    clean_regex = re.compile("<.*?>")
    return re.sub(clean_regex, "", raw_html)


def _kinoman_login_check(page):
    # Логин или пароль неверны
    if page.status_code == 401:
        raise LoginError("Неправильный логин/пароль")
    # Слишком много попыток авторизации с вашего ip-адреса, подождите пару минут
    if page.status_code == 500:
        raise LoginError(
            "Слишком много попыток авторизации с вашего ip-адреса,"
            " подождите пару минут"
        )
    if page.status_code != 200:
        raise LoginError("Неизвестная ошибка при попытке авторизации")

    response = json.loads(page.text)

    if "user" not in response:
        raise LoginError("Изменения в схеме авторизации")

    if response["user"]["abon_time_is_active"] is not True:
        raise LoginError("Подписка просрочена")

    return response


def _kinoman_login_save_cookies(cookie_dict, user_id):
    player.set_setting("_cookie", json.dumps(cookie_dict))
    player.set_setting("_last_check", int(time.time()))
    player.set_setting("_user_id", int(user_id))


def _kinoman_login(session):
    cookie = player.get_setting("_cookie")
    last_check = player.get_setting("_last_check", "int")

    if cookie:
        session.cookies.update(json.loads(cookie))

        if not last_check or time.time() - last_check > 300:
            try:
                page = session.get(
                    "https://www.kinoman.uz/api/v1/user/profile", verify=False
                )
            except (requests.ConnectionError, requests.Timeout):
                raise NetworkError

            try:
                response = _kinoman_login_check(page)
            except LoginError:
                pass
            else:
                _kinoman_login_save_cookies(
                    session.cookies.get_dict(), response["user"]["user_id"]
                )
                return True
        else:
            return True

    login_data = {
        "login": player.get_setting("username"),
        "password": player.get_setting("password"),
    }

    if not all(login_data.values()):
        raise LoginError("Не введены логин/пароль")

    try:
        page = session.post(
            "https://www.kinoman.uz/api/v1/user/login", json=login_data, verify=False
        )
    except (requests.ConnectionError, requests.Timeout) as e:
        raise NetworkError from e

    response = _kinoman_login_check(page)

    _kinoman_login_save_cookies(session.cookies.get_dict(), response["user"]["user_id"])

    return True


def get_page(page_url, payload=None, user_id_required=False):
    session = requests.Session()
    session.headers.update({"User-Agent": SPOOF_USER_AGENT})

    _kinoman_login(session)

    try:
        if payload:
            if user_id_required:
                payload["user_id"] = player.get_setting("_user_id", "int")

            response = _json_loads_byteified(
                session.post(page_url, data=json.dumps(payload), verify=False).text
            )
        else:
            response = _json_loads_byteified(session.get(page_url, verify=False).text)
    except (requests.ConnectionError, requests.Timeout):
        raise NetworkError

    session.close()

    return response


def get_movie_data(video_id):
    page_url = "https://www.kinoman.uz/api/v1/movie/details/{}".format(video_id)

    data = get_page(page_url)

    movie = data["movie"]

    season_n = None

    if re.search(r"\(Сезон [0-9]+", movie["title"]):
        season_n = re.search(r"\(Сезон ([0-9]+)", movie["title"]).group(1)
        season_n = season_n.zfill(2)
    # TV-Series, TV-Shows, Videoblogs
    elif movie["type_id"] in (2, 3, 4):
        season_n = "01"

    poster = "https://{}mp.jpg".format(movie["poster_url"])

    if "screenshots" in movie and movie["screenshots"]:
        screenshot = "https://{}b.jpg".format(
            random.choice(movie["screenshots"])["title"]  # nosec
        )
    else:
        screenshot = poster

    return {
        "movie_info": {
            "art": {
                "icon": poster,
                "thumb": poster,
                "poster": poster,
                "banner": poster,
                "fanart": screenshot,
            },
            "properties": {"Fanart_Image": screenshot},
            "info": {
                "cast": [item["title"] for item in movie["actors"]],
                "director": " / ".join([item["title"] for item in movie["directors"]]),
                "genre": " / ".join([item["title"] for item in movie["genres"]]),
                "country": " / ".join([item["title"] for item in movie["countries"]]),
                "title": movie["title"],
                "originaltitle": movie["original_title"],
                "year": movie["release_year"],
                "premiered": movie["release_date"][:10],
                "rating": movie["age_rating"],
                "plot": _cleanhtml(movie["description"]),
            },
        },
        "file_lists": _generate_movie_file_lists(movie, season_n),
        "series_season_n": season_n,
    }


def _generate_movie_file_lists(movie, season_n=None):
    # Ordered dict to show categories in strict order
    file_lists = OrderedDict([("online", []), ("sd", []), ("hd", []), ("full_hd", [])])

    for file_type in ("online_files", "download_files"):
        episodes_counter = 1
        for video_file in movie[file_type]:
            if file_type == "online_files":
                file_name = video_file["title"]
                file_info = None
                file_url = "https://www.kinoman.uz/api/v1/movie/online/{}".format(
                    video_file["secure_id"]
                )
                file_cat = "online"
            else:
                file_name = video_file["file_name"]
                file_info = "[CR]".join(
                    [
                        "Видео: {} ({}x{})".format(
                            video_file["name"],
                            video_file["width"],
                            video_file["height"],
                        ),
                        "Аудио: {}".format(video_file["title"]),
                    ]
                )
                file_url = "https://www.kinoman.uz/api/v1/movie/download/{}".format(
                    video_file["secure_id"]
                )

                # if file['name'] in ('HDTVRIP', 'BDRIP'):
                #     file_cat = 'hd'
                # else:
                #     file_cat = 'sd'

                # Video category according to site's original scripts
                if 1280 <= int(video_file["width"]) < 1800:
                    file_cat = "hd"
                elif int(video_file["width"]) >= 1800:
                    file_cat = "full_hd"
                else:
                    file_cat = "sd"

            if season_n is not None:
                if re.search(r"e[0-9]+\.", file_name):
                    episode_num = re.search(r"e([0-9]+)\.", file_name).group(1)
                else:
                    episode_num = episodes_counter
                    episodes_counter += 1

                episode_title = re.sub(r"\(.*[0-9]+\)", "", str(movie["title"])).strip()
                episode_title = "{} S{}E{}".format(episode_title, season_n, episode_num)

                file_episode_data = {
                    "season": int(season_n),
                    "episode": int(episode_num),
                    "title": episode_title,
                }
            else:
                file_episode_data = None

            file_lists[file_cat].append(
                [file_name, file_url, file_episode_data, file_info]
            )

    # Removing categories without files
    file_lists = OrderedDict([(k, v) for k, v in file_lists.items() if v])

    return file_lists


def _list_genres():
    data = get_page("https://www.kinoman.uz/api/v1/genre/all")

    genres_list = []

    for genre in data["genreList"]:
        genres_list.append((genre["title"], genre["id"]))

    return sorted(genres_list, key=lambda tup: tup[0])


def list_categories_video_menu():
    items = []

    for cat_label, cat_query in list(gen_categories_video())[1:]:
        for i in range(2):
            cat_query_n = cat_query.copy()
            if i == 1:
                cat_label += " (премьеры)"
                cat_query_n["sort_type"] = 1

            items.append((cat_label, cat_query_n))

    items.append(
        (
            "Избранное",
            {
                "category": "favorite",
                "content_type_id": 0,
                "favorite": 1,
                "title": "избранное",
            },
        )
    )

    return items


def gen_categories_video():
    items = (
        ("Все категории", 0, "all"),
        ("Фильмы", 1, "movies"),
        ("Сериалы", 2, "tv-series"),
        ("Мультфильмы", 0, "cartoons"),
        ("ТВ-программы", 3, "tv-shows"),
        ("Видеоблоги", 4, "vlogs"),
    )

    for cat_title, cat_id, cat_name in items:
        cat_query = {"category": cat_name, "content_type_id": cat_id}

        # Need this exception because that's how things work at that site
        if cat_name != "cartoons":
            cat_query["genre_black_list"] = 12
        else:
            cat_query["genre_list"] = 12

        yield (cat_title, cat_query)


def gen_categories_age():
    items = (
        ("Без ограничений", -1),
        ("Все возраста", 0),
        ("0", 1),
        ("0-12", 2),
        ("12-18", 3),
        ("18+", 4),
    )

    for age_title, age_id in items:
        age_query = {}

        if age_id >= 0:
            age_query["age_rating_type"] = age_id

        yield (age_title, age_query)


def gen_categories_genre():
    items = [("Все жанры", -1)] + _list_genres()

    for genre_title, genre_id in items:
        genre_query = {}

        if genre_id != -1:
            genre_query["genre_list"] = genre_id

        yield (genre_title, genre_query)


def gen_categories_year():
    for year in [0] + list(range(datetime.now().year, 1924, -1)):
        year_query = {}

        if year > 0:
            year_title = str(year)
            year_query["year"] = year
        else:
            year_title = "Все года"

        yield (year_title, year_query)


def get_movies(query):
    if "q" in query:
        page_url = "https://www.kinoman.uz/api/v1/movie/search_by_name"
        user_id_required = False
    else:
        page_url = "https://www.kinoman.uz/api/v1/movie/search_by_filter"
        user_id_required = True

        query["sort_type"] = int(query.get("sort_type", 0))

        query["genre_list"] = [
            int(x) for x in query.get("genre_list", "").split(",") if x
        ]
        query["genre_black_list"] = [
            int(x) for x in query.get("genre_black_list", "").split(",") if x
        ]
        query["content_type_id"] = int(query["content_type_id"])

        if "year" in query:
            query["year"] = int(query["year"])

        if "age_rating_type" in query:
            query["age_rating_type"] = int(query["age_rating_type"])

        if "favorite" in query:
            query["favorite"] = bool(int(query["favorite"]))

    data = get_page(page_url, query, user_id_required)

    res_list = []

    for movie in data["movies"]:
        movie_id = movie["id"]
        movie_title = "{} ({})".format(movie["title"], movie["release_year"])
        poster = "https://{}mm.jpg".format(movie["poster_url"])

        movie_data = {
            "art": {
                "icon": poster,
                "thumb": poster,
                "poster": poster,
                "banner": poster,
                "fanart": poster,
            },
            "properties": {"Fanart_Image": poster},
            "info": {
                "title": movie_title,
                "year": movie["release_year"],
                "premiered": movie["release_date"],
                "plot": "",
            },
        }

        res_list.append([movie_title, movie_id, movie_data])

    if int(data.get("total_page") or 0) > 1 and query["page"] < data["total_page"]:
        res_list.append(
            ["--> ({} / {})".format(query["page"] + 1, data["total_page"]), None, None]
        )

    return res_list


def get_movie_files_list(file_lists, video_category=None, season_n=None):
    category_names = {
        "online": "стрим",
        "sd": "SD",
        "hd": "HD",
        "full_hd": "Full HD",
    }

    files = []

    if not file_lists:
        raise MissingVideoError()

    # Movie or series root
    if video_category is None:
        # List video format categories for series
        if season_n is not None:
            for f_video_category in file_lists:
                files.append(
                    [
                        "dir",
                        None,
                        "Смотреть серии ({})".format(category_names[f_video_category]),
                        f_video_category,
                        None,
                        None,
                    ]
                )
        # List all available files for movies
        else:
            for f_video_category in file_lists:
                # If it's only a single file, then replace the filename with
                # tooltip according to format
                file_name = None
                if len(file_lists[f_video_category]) == 1:
                    file_name = file_lists[f_video_category][0][0]
                    file_lists[f_video_category][0][0] = "Воспроизвести ({})".format(
                        category_names[f_video_category]
                    )
                for video_file in file_lists[f_video_category]:
                    files.append(
                        [f_video_category, file_name if file_name else video_file[0]]
                        + video_file
                    )

    # Video format category listing
    else:
        if video_category not in file_lists:
            raise MissingVideoError()

        for video_file in file_lists[video_category]:
            files.append([video_category, video_file[0]] + video_file)

    return files


def get_video_url(video_id, video_type, video_name):
    movie = get_movie_data(video_id)

    # TODO make this look good
    try:
        video_url = next(
            v[1] for v in movie["file_lists"][video_type] if v[0] == video_name
        )
    except (StopIteration, IndexError):
        raise MissingVideoError

    data = get_page(video_url)

    return data["url"]
