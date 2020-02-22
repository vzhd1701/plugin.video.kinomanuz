# coding=utf-8
# pylint: disable=protected-access, no-self-use

import unittest

try:
    import mock
except ImportError:
    from unittest import mock

from resources.internal import router


class TestPathSections(unittest.TestCase):
    def test_good_path(self):
        test_paths = (
            ("/", [""]),
            ("/some/path", ["some", "path"]),
            ("/some/path/", ["some", "path", ""]),
        )

        for good_path, good_sections in test_paths:
            path_sections = router._get_path_sections(good_path)

            self.assertEqual(path_sections, good_sections)

    def test_exception_start_with_slash(self):
        bad_path = "some/path"

        with self.assertRaisesRegexp(
            ValueError, r'^Path should start with "/" in path .*'
        ):
            router._get_path_sections(bad_path)

    def test_exception_empty_midsection(self):
        bad_path = "/some//path"

        with self.assertRaisesRegexp(ValueError, r"^Empty midsection in path .*"):
            router._get_path_sections(bad_path)


class TestRouteParse(unittest.TestCase):
    def test_good_routes(self):
        test_paths = [
            ("/some/path", ["some", "path"]),
            ("/some/<path>", ["some", ("string", "path")]),
        ]

        for path_type in router.PATH_TYPES:
            test_paths.append(
                ("/some/<{}:path>".format(path_type), ["some", (path_type, "path")])
            )

        for good_path, good_route in test_paths:
            path_sections = router._route_parse(good_path)

            self.assertEqual(path_sections, good_route)

    def test_exception_duplicate_variable_name(self):
        bad_path = "/some/<path>/<path>"

        with self.assertRaisesRegexp(ValueError, r"^Duplicate variable name .*"):
            router._route_parse(bad_path)

    def test_exception_unknown_variable_type(self):
        bad_path = "/some/<unknown_variable_type:path>"

        with self.assertRaisesRegexp(ValueError, r"^Unknown variable type .*"):
            router._route_parse(bad_path)

    def test_exception_bad_variable(self):
        bad_paths = (
            "/some/<:path>",
            "/some/<int:>",
            "/some/<:>",
            "/some/<>",
        )

        for bad_path in bad_paths:
            with self.assertRaisesRegexp(ValueError, r"^Bad variable .*"):
                router._route_parse(bad_path)


class TestRoute(unittest.TestCase):
    patcher = None

    @classmethod
    def setUpClass(cls):
        cls.patcher = mock.patch("resources.internal.router.REGISTERED_ROUTES", {})
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

    def setUp(self):
        router.REGISTERED_ROUTES = {}

    def test_good_route(self):
        @router.route("/")
        def test_function():
            pass

        self.assertEqual(router.REGISTERED_ROUTES, {("",): test_function})

    def test_exception_bad_parameters(self):
        # pylint: disable=unused-variable
        with self.assertRaisesRegexp(
            ValueError, r"^Function .* does not have parameters: .*"
        ):
            # noinspection PyUnresolvedReferences
            @router.route("/<missing_argument>")
            def test_function():
                pass

    def test_exception_duplicate_routes(self):
        # pylint: disable=unused-variable
        with self.assertRaisesRegexp(ValueError, r"^Route already defined for path .*"):

            @router.route("/")
            def test_function1():
                pass

            @router.route("/")
            def test_function2():
                pass


class TestResolve(unittest.TestCase):
    patcher = None

    @classmethod
    def setUpClass(cls):
        cls.patcher = mock.patch("resources.internal.router.REGISTERED_ROUTES", {})
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

    def setUp(self):
        router.REGISTERED_ROUTES = {}

    def test_good_resolve_no_args(self):
        def test_function():
            pass

        test_function = mock.MagicMock(spec=test_function)

        router.route("/other/path1")(test_function)
        router.route("/other/path2")(test_function)
        router.route("/")(test_function)
        router.resolve("plugin://test_plugin/")
        router.resolve("plugin://test_plugin/other/path1")

        test_function.assert_has_calls([mock.call(), mock.call()])

    def test_good_resolve_with_args(self):
        # pylint: disable=unused-argument
        # noinspection PyUnusedLocal
        def test_function(search_query):
            pass

        test_function = mock.MagicMock(spec=test_function)
        test_function.__code__.co_varnames = ["search_query"]

        router.route("/search/<search_query>")(test_function)
        router.resolve("plugin://test_plugin/search/something")

        test_function.assert_called_once_with(search_query="something")

    def test_good_resolve_with_args_multiple_types(self):
        # pylint: disable=unused-argument
        # noinspection PyUnusedLocal
        def test_function(test_parameter):
            pass

        test_function = mock.MagicMock(spec=test_function)
        test_function.__code__.co_varnames = ["test_parameter"]

        router.route("/page/<int:test_parameter>")(test_function)
        router.route("/page/<float:test_parameter>")(test_function)
        router.resolve("plugin://test_plugin/page/10")

        test_function.assert_called_once_with(test_parameter=10)

    def test_good_resolve_with_args_and_query(self):
        # pylint: disable=unused-argument
        # noinspection PyUnusedLocal
        def test_function(query, search_query):
            pass

        test_function = mock.MagicMock(spec=test_function)
        test_function.__code__.co_varnames = ["search_query"]

        router.route("/search/<search_query>")(test_function)
        router.resolve("plugin://test_plugin/search/something?testing=123")

        test_function.assert_called_once_with(
            search_query="something", query={"testing": "123"}
        )

    def test_exception_bad_url(self):
        with self.assertRaisesRegexp(ValueError, r"^Failed to resolve the url .*"):
            router.resolve("plugin://test_plugin/search/something?testing=123")


class TestPathFor(unittest.TestCase):
    patcher = None

    @classmethod
    def setUpClass(cls):
        cls.patcher = mock.patch("resources.internal.router.REGISTERED_ROUTES", {})
        cls.patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.patcher.stop()

    def setUp(self):
        # pylint: disable=unused-variable,unused-argument

        router.REGISTERED_ROUTES = {}

        @router.route("/")
        def test_function_root():
            pass

        # noinspection PyUnusedLocal
        @router.route("/movies")
        @router.route("/movies/page/<int:page>")
        def test_function_args(page):
            pass

        @router.route("/ambiguous1")
        @router.route("/ambiguous2")
        def test_function_ambiguous():
            pass

    def test_good_paths_for(self):
        good_path = router.path_for("test_function_root")
        self.assertEqual(good_path, "/")

    def test_good_paths_for_query(self):
        good_path = router.path_for("test_function_root", query={"test": "test"})
        self.assertEqual(good_path, "/?test=test")

    def test_good_paths_for_args(self):
        good_path = router.path_for("test_function_args", path_vars={"page": 10})
        self.assertEqual(good_path, "/movies/page/10")

    def test_exception_bad_vars(self):
        with self.assertRaisesRegexp(ValueError, r"path_vars must be a dictionary"):
            router.path_for("test_function_root", path_vars=[])

    def test_exception_bad_query(self):
        with self.assertRaisesRegexp(ValueError, r"query must be a dictionary"):
            router.path_for("test_function_root", query=[])

    def test_exception_bad_function_params(self):
        with self.assertRaisesRegexp(
            ValueError, r"^Function .* does not have parameters: .*"
        ):
            router.path_for(
                "test_function_root", path_vars={"non_existing_param": None}
            )

    def test_exception_ambiguous_function_params(self):
        with self.assertRaisesRegexp(
            ValueError, r"^Ambiguous paths for .* with this set of variables"
        ):
            router.path_for("test_function_ambiguous")

    def test_exception_no_functions(self):
        with self.assertRaisesRegexp(
            ValueError, r"^No functions registered for endpoint .*"
        ):
            router.path_for("test_function_nonexistent")

    def test_exception_bad_args_type(self):
        with self.assertRaisesRegexp(
            ValueError, r"^Variable .* has wrong variable type for function .*"
        ):
            router.path_for("test_function_args", path_vars={"page": None})


if __name__ == "__main__":
    unittest.main()
