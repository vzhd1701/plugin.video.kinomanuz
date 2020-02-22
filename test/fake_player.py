# coding=utf-8


class FakePlayer(object):
    def __init__(self):
        self.storage = {}

    def get_setting(self, key, var_type="str"):
        if var_type not in ("str", "int", "float", "bool", "list"):
            raise ValueError("Unknown setting type")

        if var_type == "int":
            value = int(self.storage.get(key))
        elif var_type == "float":
            value = float(self.storage.get(key))
        elif var_type == "bool":
            value = bool(self.storage.get(key))
        elif var_type == "list":
            value = self.storage.get(key)
            value = value.split("|") if value else []
        else:
            value = self.storage.get(key)

        return value

    def set_setting(self, key, value):
        if isinstance(value, (list, tuple)):
            value = "|".join(value)

        self.storage[key] = value
