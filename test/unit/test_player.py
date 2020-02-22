# coding=utf-8
# pylint: disable=no-self-use

import unittest

try:
    import mock
except ImportError:
    from unittest import mock

STUB_ADDON_NAME = "test.plugin"
STUB_ARGV = [STUB_ADDON_NAME, "1", ""]

with mock.patch("sys.argv", STUB_ARGV):
    from resources.internal import player

    player.ADDON_NAME = STUB_ADDON_NAME


class TestMinorStuff(unittest.TestCase):
    @mock.patch("resources.internal.player.ADDON")
    def test_open_settings(self, mock_addon):
        player.open_settings()
        mock_addon.openSettings.assert_called_once()

    @mock.patch("xbmc.log")
    def test_log(self, mock_log):
        player.log("test")
        mock_log.assert_called_once_with("{}: test".format(STUB_ADDON_NAME), mock.ANY)

    def test_get_url(self):
        path_tests = [
            ["/", "plugin://{}/".format(STUB_ADDON_NAME)],
            ["", "plugin://{}/".format(STUB_ADDON_NAME)],
            ["/test", "plugin://{}/test".format(STUB_ADDON_NAME)],
        ]

        for good_path, good_url in path_tests:
            self.assertEqual(player.get_url(good_path), good_url)

    @mock.patch("sys.argv", [STUB_ADDON_NAME, "1", "?test=test"])
    def test_get_current_url(self):
        self.assertEqual(player.get_current_url(), "test.plugin?test=test")

    @mock.patch("xbmc.Keyboard")
    def test_dialog_keyboard(self, mock_keyboard):
        mock_keyboard().isConfirmed.return_value = False
        self.assertIsNone(player.dialog_keyboard())

        mock_keyboard().isConfirmed.return_value = True
        mock_keyboard().getText.return_value = "test query"
        self.assertEqual(player.dialog_keyboard(), "test query")

    @mock.patch("xbmcgui.Dialog")
    def test_dialog_ok(self, mock_dialog):
        player.dialog_ok("test title", "test text")
        mock_dialog().ok.assert_called_once_with("test title", "test text")

    @mock.patch("xbmcgui.Dialog")
    def test_dialog_yesno(self, mock_dialog):
        player.dialog_yesno(
            "test title", "test text", nolabel="test no", yeslabel="test yes"
        )
        mock_dialog().yesno.assert_called_once_with(
            "test title", "test text", nolabel="test no", yeslabel="test yes"
        )

    @mock.patch("xbmcgui.Dialog")
    def test_dialog_multiselect(self, mock_dialog):
        player.dialog_multiselect("test title", ["test item"])
        mock_dialog().multiselect.assert_called_once_with("test title", ["test item"])

    @mock.patch("xbmcplugin.endOfDirectory")
    @mock.patch("xbmc.executebuiltin")
    def test_redirect_in_place(self, mock_exec, mock_end):
        player.redirect_in_place("/test/path")

        mock_exec.assert_called_once_with(
            "Container.Update(plugin://{}/test/path, replace)".format(STUB_ADDON_NAME)
        )
        mock_end.assert_called_once_with(1, updateListing=True)

    @mock.patch("xbmcplugin.setResolvedUrl")
    @mock.patch("xbmcgui.ListItem")
    def test_play(self, mock_list, mock_resolve):
        mock_list.side_effect = ["test_url"]
        player.play("test_url")

        mock_list.assert_called_once_with(path="test_url")
        mock_resolve.assert_called_once_with(1, True, "test_url")


class TestSettings(unittest.TestCase):
    @mock.patch("resources.internal.player.ADDON")
    def test_get_setting_str(self, mock_addon):
        mock_addon.getSetting.side_effect = (
            lambda key: "test" if key == "test_key" else None
        )
        self.assertEqual(player.get_setting("test_key"), "test")

    @mock.patch("resources.internal.player.ADDON")
    def test_get_setting_int(self, mock_addon):
        mock_addon.getSettingInt.side_effect = (
            lambda key: 100 if key == "test_key" else None
        )
        self.assertEqual(player.get_setting("test_key", "int"), 100)

    @mock.patch("resources.internal.player.ADDON")
    def test_get_setting_float(self, mock_addon):
        mock_addon.getSetting.side_effect = (
            lambda key: "100.10" if key == "test_key" else None
        )
        self.assertEqual(player.get_setting("test_key", "float"), 100.10)

    @mock.patch("resources.internal.player.ADDON")
    def test_get_setting_bool(self, mock_addon):
        mock_addon.getSettingBool.side_effect = (
            lambda key: True if key == "test_key" else None
        )
        self.assertTrue(player.get_setting("test_key", "bool"))

    @mock.patch("resources.internal.player.ADDON")
    def test_get_setting_list(self, mock_addon):
        mock_addon.getSetting.side_effect = (
            lambda key: "item1|item2" if key == "test_key" else None
        )
        self.assertEqual(player.get_setting("test_key", "list"), ["item1", "item2"])

    def test_exception_wrong_type(self):
        with self.assertRaisesRegexp(ValueError, r"Unknown setting type"):
            player.get_setting("test_key", "bad_type")

    @mock.patch("resources.internal.player.ADDON")
    def test_set_setting_str(self, mock_addon):
        player.set_setting("test_key", "test_value")
        mock_addon.setSetting.assert_called_once_with(id="test_key", value="test_value")
        mock_addon.setSetting.reset_mock()

    @mock.patch("resources.internal.player.ADDON")
    def test_set_setting_int(self, mock_addon):
        player.set_setting("test_key", 100)
        mock_addon.setSettingInt.assert_called_once_with("test_key", 100)

    @mock.patch("resources.internal.player.ADDON")
    def test_set_setting_float(self, mock_addon):
        player.set_setting("test_key", 100.10)
        mock_addon.setSettingNumber.assert_called_once_with("test_key", 100.10)

    @mock.patch("resources.internal.player.ADDON")
    def test_set_setting_bool(self, mock_addon):
        player.set_setting("test_key", True)
        mock_addon.setSettingBool.assert_called_once_with("test_key", True)

    @mock.patch("resources.internal.player.ADDON")
    def test_set_setting_list(self, mock_addon):
        player.set_setting("test_key", ["item1", "item2"])
        mock_addon.setSetting.assert_called_once_with(
            id="test_key", value="item1|item2"
        )
        mock_addon.setSetting.reset_mock()


class TestAddItems(unittest.TestCase):
    @mock.patch("xbmcplugin.addDirectoryItem")
    @mock.patch("xbmcgui.ListItem")
    def test_add_item(self, mock_li, mock_add):
        player.add_item("test", "/test/path")
        mock_add.assert_called_once_with(
            handle=1,
            isFolder=False,
            listitem=mock_li(),
            url="plugin://test.plugin/test/path",
        )

    @mock.patch("xbmcplugin.addDirectoryItem")
    @mock.patch("xbmcgui.ListItem")
    def test_add_item_folder(self, mock_li, mock_add):
        player.add_item("test", "/test/path", is_folder=True)
        mock_add.assert_called_once_with(
            handle=1,
            isFolder=True,
            listitem=mock_li(),
            url="plugin://test.plugin/test/path",
        )

    @mock.patch("xbmcplugin.addDirectoryItem", mock.MagicMock())
    @mock.patch("xbmcgui.ListItem")
    def test_add_item_properties(self, mock_li):
        video_data = {"properties": {"test_key": "test_value"}}

        player.add_item("test", "/test/path", video_data)

        mock_li().setProperty.assert_any_call("test_key", "test_value")

    @mock.patch("xbmcplugin.addDirectoryItem", mock.MagicMock())
    @mock.patch("xbmcgui.ListItem")
    def test_add_item_info(self, mock_li):
        video_data = {"info": {"test_key": "test_value"}}

        player.add_item("test", "/test/path", video_data)

        mock_li().setInfo.assert_called_once_with(
            "video", infoLabels={"test_key": "test_value"}
        )

    @mock.patch("xbmcplugin.setContent", mock.MagicMock())
    @mock.patch("resources.internal.player.add_item")
    @mock.patch("xbmcplugin.endOfDirectory")
    def test_print_items(self, mock_end, mock_add):
        test_items = [
            {"label": "test label", "path": "/test/path"},
        ]

        player.print_items(test_items)

        mock_add.assert_called_once_with(
            "test label", "/test/path", None, is_folder=None, is_playable=None
        )
        mock_end.assert_called_once_with(1, cacheToDisc=True, updateListing=False)


if __name__ == "__main__":
    unittest.main()
