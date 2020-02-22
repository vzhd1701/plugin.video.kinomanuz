# coding=utf-8
# flake8: noqa
# pylint: disable=invalid-name,redefined-builtin,unused-argument

from typing import Union

try:
    # noinspection PyUnresolvedReferences
    STR_TYPE = Union[str, unicode]
except NameError:
    STR_TYPE = Union[str, str]


# noinspection PyPep8Naming,PyMethodMayBeStatic,PyShadowingBuiltins,PyUnusedLocal
class Addon(object):
    """
    Kodi's addon class
    Offers classes and functions that manipulate the add-on settings, information
    and localization.
    Creates a new AddOn class.
    :param id: [opt] string - id of the addon as specified in addon.xml
    Specifying the addon id is not needed. Important however is that the addon
    folder has the same name as the AddOn id provided in addon.xml.
    You can optionally specify the addon id from another installed addon
    to retrieve settings from it.**id** is optional as it will be auto detected
    for this add-on instance.
    Example::
        self.Addon = xbmcaddon.Addon()
        self.Addon = xbmcaddon.Addon('script.foo.bar')
    """

    def __init__(self, id=None):
        # type: (str) -> None
        self.settings = {}

    @staticmethod
    def getLocalizedString(id):
        # type: (int) -> str
        """
        Returns an addon's localized 'unicode string'.
        :param id: integer - id# for string you want to localize.
        :return: Localized 'unicode string'
        **id** is optional as it will be auto detected for this add-on instance.
        Example::
            locstr = self.Addon.getLocalizedString(32000)
        """
        return ""

    def getSetting(self, id):
        # type: (str) -> str
        """
        Returns the value of a setting as a unicode string.
        :param id: string - id of the setting that the module needs to access.
        :return: Setting as a unicode string
        **id** is optional as it will be auto detected for this add-on instance.
        Example::
            apikey = self.Addon.getSetting('apikey')
        """
        return self.settings.get(id, "")

    def getSettingBool(self, id):
        # type: (str) -> bool
        """
        Returns the value of a setting as a boolean.
        :param id: string - id of the setting that the module needs to access.
        :return: Setting as a boolean
        New function added.
        Example::
            enabled = self.Addon.getSettingBool('enabled')
        """
        value = self.getSetting(id)

        if value == "true":
            return True
        if value == "false":
            return False

        raise ValueError("Invalid setting type")

    def getSettingInt(self, id):
        # type: (str) -> int
        """
        Returns the value of a setting as an integer.
        :param id: string - id of the setting that the module needs to access.
        :return: Setting as an integer
        New function added.
        Example::
            max = self.Addon.getSettingInt('max')
        """
        return int(self.getSetting(id) or 0)

    def getSettingNumber(self, id):
        # type: (str) -> float
        """
        Returns the value of a setting as a floating point number.
        :param id: string - id of the setting that the module needs to access.
        :return: Setting as a floating point number
        New function added.
        Example::
            max = self.Addon.getSettingNumber('max')
        """
        return float(self.getSetting(id) or 0)

    def getSettingString(self, id):
        # type: (str) -> str
        """
        Returns the value of a setting as a unicode string.
        :param id: string - id of the setting that the module needs to access.
        :return: Setting as a unicode string
        New function added.
        Example::
            apikey = self.Addon.getSettingString('apikey')
        """
        return self.getSetting(id)

    def setSetting(self, id, value):
        # type: (str, STR_TYPE) -> None
        """
        Sets a script setting.
        :param id: string - id of the setting that the module needs to access.
        :param value: string or unicode - value of the setting.
        You can use the above as keywords for arguments.**id** is optional
        as it will be auto detected for this add-on instance.
        Example::
            self.Addon.setSetting(id='username', value='teamkodi')
        """
        self.settings[id] = value

    def setSettingBool(self, id, value):
        # type: (str, bool) -> bool
        """
        Sets a script setting.
        :param id: string - id of the setting that the module needs to access.
        :param value: boolean - value of the setting.
        :return: True if the value of the setting was set, false otherwise
        You can use the above as keywords for arguments.
        New function added.
        Example::
            self.Addon.setSettingBool(id='enabled', value=True)
        """
        if not isinstance(value, bool):
            raise ValueError("Value must be bool")

        if value:
            self.settings[id] = "true"
        else:
            self.settings[id] = "false"

        return True

    def setSettingInt(self, id, value):
        # type: (str, int) -> bool
        """
        Sets a script setting.
        :param id: string - id of the setting that the module needs to access.
        :param value: integer - value of the setting.
        :return: True if the value of the setting was set, false otherwise
        You can use the above as keywords for arguments.
        New function added.
        Example::
            self.Addon.setSettingInt(id='max', value=5)
        """
        if not isinstance(value, int):
            raise ValueError("Value must be int")

        self.settings[id] = str(value)

        return True

    def setSettingNumber(self, id, value):
        # type: (str, float) -> bool
        """
        Sets a script setting.
        :param id: string - id of the setting that the module needs to access.
        :param value: float - value of the setting.
        :return: True if the value of the setting was set, false otherwise
        You can use the above as keywords for arguments.
        New function added.
        Example::
            self.Addon.setSettingNumber(id='max', value=5.5)
        """
        if not isinstance(value, float):
            raise ValueError("Value must be float")

        self.settings[id] = str(value)

        return True

    def setSettingString(self, id, value):
        # type: (str, STR_TYPE) -> bool
        """
        Sets a script setting.
        :param id: string - id of the setting that the module needs to access.
        :param value: string or unicode - value of the setting.
        :return: True if the value of the setting was set, false otherwise
        You can use the above as keywords for arguments.
        New function added.
        Example::
            self.Addon.setSettingString(id='username', value='teamkodi')
        """
        self.setSetting(id, value)

        return True

    @staticmethod
    def openSettings():
        # type: () -> None
        """
        Opens this scripts settings dialog.
        Example::
            self.Addon.openSettings()
        """
        return

    @staticmethod
    def getAddonInfo(id):
        # type: (str) -> str
        """
        Returns the value of an addon property as a string.
        :param id: string - id of the property that the module needs to access.
            Choices for the property are:
        ======= ========== ============ ===========
        author  changelog  description  disclaimer
        fanart  icon       id           name
        path    profile    stars        summary
        type    version
        ======= ========== ============ ===========
        :return: AddOn property as a string
        Example::
            version = self.Addon.getAddonInfo('version')
        """
        return ""
