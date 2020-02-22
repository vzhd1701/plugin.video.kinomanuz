# coding=utf-8

import sys

import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon


ADDON = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo("id")
ADDON_HANDLE = int(sys.argv[1])


def open_settings():
    ADDON.openSettings()


def get_setting(key, var_type="str"):
    if var_type not in ("str", "int", "float", "bool", "list"):
        raise ValueError("Unknown setting type")

    if var_type == "int":
        value = ADDON.getSettingInt(key)
    elif var_type == "float":
        # getSettingNumber doesn't work for some reason
        value = ADDON.getSetting(key)
        value = float(value or 0)
    elif var_type == "bool":
        value = ADDON.getSettingBool(key)
    elif var_type == "list":
        value = ADDON.getSetting(key)
        value = value.split("|") if value else []
    else:
        value = ADDON.getSetting(key)

    return value


def set_setting(key, value):
    if isinstance(value, bool):
        return ADDON.setSettingBool(key, value)
    if isinstance(value, int):
        return ADDON.setSettingInt(key, value)
    if isinstance(value, float):
        return ADDON.setSettingNumber(key, value)
    if isinstance(value, (list, tuple)):
        value = "|".join(value)
        return ADDON.setSetting(id=key, value=str(value))

    return ADDON.setSetting(id=key, value=str(value))


def log(message):
    xbmc.log("{}: {}".format(ADDON_NAME, message), xbmc.LOGERROR)


def get_url(path):
    if not path.startswith("/"):
        path = "/" + path

    return "plugin://{}{}".format(ADDON_NAME, path)


def get_current_url():
    return sys.argv[0] + sys.argv[2]


def dialog_keyboard(default=None, heading=None, hidden=False):
    if heading is None:
        heading = "Введите запрос"
    if default is None:
        default = ""

    keyboard = xbmc.Keyboard(default, heading, hidden)
    keyboard.doModal()

    if keyboard.isConfirmed():
        return keyboard.getText()

    return None


def dialog_ok(title, text):
    return xbmcgui.Dialog().ok(title, text)


def dialog_yesno(title, text, nolabel=None, yeslabel=None):
    return xbmcgui.Dialog().yesno(title, text, nolabel=nolabel, yeslabel=yeslabel)


def dialog_multiselect(title, items):
    return xbmcgui.Dialog().multiselect(title, items)


def redirect_in_place(path):
    url = get_url(path)

    xbmc.executebuiltin("Container.Update({}, replace)".format(url))
    xbmcplugin.endOfDirectory(ADDON_HANDLE, updateListing=True)


def play(url):
    l_item = xbmcgui.ListItem(path=url)
    xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, l_item)


def add_item(name, path, video_data=None, is_folder=False, is_playable=False):
    url = get_url(path)

    if video_data is None:
        video_data = {}

    if is_folder:
        icon = "DefaultFolder.png"
    else:
        icon = "DefaultVideo.png"

    l_item = xbmcgui.ListItem(name)

    video_data.setdefault("art", {})
    video_data["art"].setdefault("icon", icon)

    l_item.setArt(video_data["art"])

    if video_data.get("properties"):
        for key, value in video_data["properties"].items():
            l_item.setProperty(key, value)

    if video_data.get("info"):
        l_item.setInfo("video", infoLabels=video_data["info"])

    l_item.setProperty("Video", "true")
    l_item.setProperty("IsPlayable", str(is_playable).lower())

    xbmcplugin.addDirectoryItem(
        handle=ADDON_HANDLE, url=url, listitem=l_item, isFolder=is_folder
    )


def print_items(items, content_type="tvshows", update=False, cache=True):
    for item in items:
        add_item(
            item["label"],
            item["path"],
            item.get("video_data"),
            is_folder=item.get("is_folder"),
            is_playable=item.get("is_playable"),
        )

    xbmcplugin.setContent(ADDON_HANDLE, content_type)
    xbmcplugin.endOfDirectory(ADDON_HANDLE, updateListing=update, cacheToDisc=cache)

    # if viewType:
    #    xbmc.executebuiltin('Container.SetViewMode({})')
