# coding=utf-8

from copy import deepcopy

from resources.internal.router import route, path_for, resolve
from resources.internal import player
from resources import kinoman_api


@route("/")
def root():
    menu_items = []

    for label, query in kinoman_api.list_categories_video_menu():
        menu_items.append(
            {
                "label": label,
                "path": path_for("list_movies", query=query),
                "is_folder": True,
            }
        )

    search_icon = {"art": {"icon": "DefaultAddonsSearch.png"}}

    menu_items.append(
        {
            "label": "Поиск по фильтру",
            "path": path_for("search_filter"),
            "video_data": search_icon,
            "is_folder": True,
        }
    )

    if player.get_setting("search_history_status", "bool") and player.get_setting(
        "_search_history", "list"
    ):
        search_endpoint = "search_history"
    else:
        search_endpoint = "search"

    menu_items.append(
        {
            "label": "Поиск",
            "path": path_for(search_endpoint),
            "video_data": search_icon,
            "is_folder": True,
        }
    )

    player.print_items(menu_items, cache=False)


@route("/list_movies/")
def list_movies(query):
    if "q" not in query:
        query["page"] = int(query.get("page", 1))

    items = []

    for title, video_id, video_data in kinoman_api.get_movies(query.copy()):
        if title.startswith("-->"):
            query["page"] += 1
            item_path = path_for("list_movies", query=query)
        else:
            item_path = path_for("open_movie", path_vars={"video_id": video_id})

        items.append(
            {
                "label": title,
                "path": item_path,
                "video_data": video_data,
                "is_folder": True,
            }
        )

    player.print_items(items, content_type="movies")


@route("/search_filter/")
@route("/search_filter/<int:step>/")
def search_filter(query=None, step=0):
    if query is None:
        query = {}

    step_menu_generators = [
        kinoman_api.gen_categories_video,
        kinoman_api.gen_categories_age,
        kinoman_api.gen_categories_genre,
        kinoman_api.gen_categories_year,
    ]

    menu_items = []
    for item_label, item_query in step_menu_generators[step]():
        query.update(item_query)

        if step == len(step_menu_generators) - 1:
            menu_items.append(
                {
                    "label": item_label,
                    "path": path_for("list_movies", query=query),
                    "is_folder": True,
                }
            )
        else:
            menu_items.append(
                {
                    "label": item_label,
                    "path": path_for(
                        "search_filter", path_vars={"step": step + 1}, query=query
                    ),
                    "is_folder": True,
                }
            )

    player.print_items(menu_items)


@route("/search/")
@route("/search/<s_query>/")
def search(s_query=None):
    if s_query is None:
        s_query = player.dialog_keyboard(heading="Поиск")

        if s_query is None:
            return

        if not s_query or s_query.strip() == "":
            player.dialog_ok("Kinoman.Uz", "Для поиска нужно ввести запрос")
            return

    if player.get_setting("search_history_status", "bool"):
        history = player.get_setting("_search_history", "list")

        if s_query in history:
            history.remove(s_query)

        history.append(s_query)

        if len(history) > 6:
            history = history[-6:]

        player.set_setting("_search_history", history)

    list_movies(query={"q": s_query})


@route("/search_history/")
def search_history():
    if not player.get_setting("search_history_status", "bool"):
        search_clear()

    search_icon = {"art": {"icon": "DefaultAddonsSearch.png"}}
    clear_icon = {"art": {"icon": "DefaultAddonNone.png"}}

    menu_items = [
        {
            "label": "Новый поиск",
            "path": path_for("search"),
            "video_data": search_icon,
            "is_folder": True,
        },
        {
            "label": "Очистить",
            "path": path_for("search_clear"),
            "video_data": clear_icon,
            "is_folder": True,
        },
    ]

    history = player.get_setting("_search_history", "list")

    for search_term in reversed(history):
        menu_items.append(
            {
                "label": search_term,
                "path": path_for("search", path_vars={"s_query": search_term}),
                "is_folder": True,
            }
        )

    player.print_items(menu_items)


@route("/search_clear")
def search_clear():
    player.set_setting("_search_history", "")
    player.redirect_in_place(path_for("root"))


@route("/movie/<int:video_id>/")
@route("/movie/<int:video_id>/<video_dir>/")
def open_movie(video_id, video_dir=None):
    movie_data = kinoman_api.get_movie_data(video_id)

    if movie_data["series_season_n"] is not None and video_dir is not None:
        content_type = "episodes"
    else:
        content_type = "movies"

    items = []

    for title, url, series, file_info in kinoman_api.get_movie_files_list(
        movie_data["file_lists"], video_dir, movie_data["series_season_n"]
    ):
        if url.startswith("http"):
            url_play = path_for("play", path_vars={"url": url})
            is_playable = True
        else:
            url_play = path_for(
                "open_movie", path_vars={"video_id": video_id, "video_dir": url}
            )
            is_playable = False

        # Gather all unique data into update dictionary
        data_update = {}
        if series:
            data_update = series.copy()
        if file_info:
            data_update["plot"] = (
                "[B]"
                + file_info
                + "[/B][CR][CR]"
                + movie_data["movie_info"]["info"]["plot"]
            )

        # Check if there is unique data and create deep copy of movie info to update,
        # so that every entry could have unique data
        if data_update:
            movie_data_alt = deepcopy(movie_data["movie_info"])
            movie_data_alt["info"].update(data_update)
        else:
            movie_data_alt = movie_data["movie_info"]

        items.append(
            {
                "label": title,
                "path": url_play,
                "is_playable": is_playable,
                "is_folder": not is_playable,
                "video_data": movie_data_alt,
            }
        )

    return player.print_items(items, content_type=content_type)


@route("/play/<url:url>")
def play(url):
    player.play(kinoman_api.get_video_url(url))


def main():
    try:
        resolve(player.get_current_url())
    except kinoman_api.LoginError as error:
        player.dialog_ok("Kinoman.Uz", "Ошибка авторизации: {}".format(error))
    except kinoman_api.MissingVideoError:
        player.dialog_ok("Kinoman.Uz", "Видео отсутствует")
    except kinoman_api.NetworkError:
        player.dialog_ok("Kinoman.Uz", "Проблема сети, попробуйте позже")


if __name__ == "__main__":  # pragma: no cover
    main()
