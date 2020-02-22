# coding=utf-8

import re
from collections import OrderedDict

try:  # pragma: no cover
    # noinspection PyCompatibility
    from urlparse import urlparse, parse_qs
    from urllib import quote, unquote, urlencode
except ImportError:  # pragma: no cover
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib.parse import urlparse, parse_qs, quote, unquote, urlencode

REGISTERED_ROUTES = {}
PATH_TYPES = OrderedDict(
    (
        ("int", {"re_checks": (r"^\d+$",), "convert": int}),
        ("float", {"re_checks": (r"^\d+\.\d+$",), "convert": float}),
        (
            "url",
            {
                "re_checks": (
                    r"^http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|"
                    r"[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+$",
                ),
                "convert": str,
            },
        ),
        ("string", {"re_checks": (r"^[^\/]+$",), "convert": str}),
    )
)


def _check_parameters(endpoint, function_vars, path_vars):
    wrong_parameters = set(path_vars).difference(function_vars)
    if wrong_parameters:
        raise ValueError(
            'Function "{}" does not have parameters: "{}"'.format(
                endpoint, ", ".join(wrong_parameters)
            )
        )


def _get_path_sections(path):
    if not path.startswith("/"):
        raise ValueError('Path should start with "/" in path "{}"'.format(path))

    path_sections = [unquote(x) for x in path[1:].split("/")]

    for section_n, section in enumerate(path_sections):
        if not section.strip() and section_n != len(path_sections) - 1:
            raise ValueError('Empty midsection in path "{}"'.format(path))

    return path_sections


def _route_parse(path):
    var_names = set()
    var_regex = re.compile(r"^<(?P<type>(?:[\w]+):)?(?P<name>[\w]+)>$")

    path_sections = _get_path_sections(path)

    route_enc = []

    for section in path_sections:
        section_match = var_regex.match(section)

        if section_match:
            var_type, var_name = (
                section_match.group("type"),
                section_match.group("name"),
            )

            if var_name in var_names:
                raise ValueError(
                    'Duplicate variable name "{}" in path "{}"'.format(var_name, path)
                )

            if var_type is None:
                var_type = "string"
            else:
                var_type = var_type[:-1]

            if var_type not in PATH_TYPES:
                raise ValueError(
                    'Unknown variable type "{}" in path "{}"'.format(var_type, path)
                )

            route_enc.append((var_type, var_name))
            var_names.add(var_name)
        elif re.match(r"^.*<.*>.*$", section):
            raise ValueError('Bad variable "{}" in path "{}"'.format(section, path))
        else:
            route_enc.append(section)

    return route_enc


def route(path):
    def sub(function):
        route_enc = _route_parse(path)

        path_vars = [x[1] for x in route_enc if isinstance(x, tuple)]
        function_vars = function.__code__.co_varnames

        _check_parameters(function.__name__, function_vars, path_vars)

        if tuple(route_enc) in REGISTERED_ROUTES:
            raise ValueError('Route already defined for path "{}"'.format(path))

        REGISTERED_ROUTES[tuple(route_enc)] = function

        return function

    return sub


def resolve(url):
    # Rules
    #   If a rule ends with a slash and is requested without a slash by the user,
    #   the user is automatically redirected to the same page with a trailing slash
    #   attached.

    #   If a rule does not end with a trailing slash and the user requests the page
    #   with a trailing slash, a 404 not found is raised.

    url_parsed = urlparse(url)

    query = {
        k: (v[0] if len(v) == 1 else v) for k, v in parse_qs(url_parsed.query).items()
    }

    paths = [_get_path_sections(url_parsed.path)]

    if not url_parsed.path.endswith("/"):
        paths.append(_get_path_sections(url_parsed.path + "/"))

    for path_sections in paths:
        endpoint, endpoint_vars = _path_to_endpoint(path_sections)

        if endpoint is not None:
            if query:
                return endpoint(query=query, **endpoint_vars)

            return endpoint(**endpoint_vars)

    raise ValueError('Failed to resolve the url "{}"'.format(url))


def _path_to_endpoint(path_sections):
    for r_route, r_route_f in REGISTERED_ROUTES.items():
        if len(r_route) != len(path_sections):
            continue

        r_vars = {}

        for section, r_section in zip(path_sections, r_route):
            if isinstance(r_section, str):
                if r_section == section:
                    continue
                break

            if isinstance(r_section, tuple):
                type_param = PATH_TYPES[r_section[0]]

                if all(
                    re.match(re_check, section) for re_check in type_param["re_checks"]
                ):
                    r_vars[r_section[1]] = type_param["convert"](section)
                else:
                    break
        else:
            return r_route_f, r_vars

    return None, None


def path_for(endpoint, path_vars=None, query=None):
    if path_vars is None:
        path_vars = {}

    if query is None:
        query = {}

    if not isinstance(path_vars, dict):
        raise ValueError("path_vars must be a dictionary")

    if not isinstance(query, dict):
        raise ValueError("query must be a dictionary")

    endpoint_route = _get_endpoint_route(endpoint, path_vars)

    path = _endpoint_route_to_path(endpoint, path_vars, endpoint_route, query)

    return path


def _get_endpoint_route(endpoint, path_vars):
    function_vars = next(
        (
            f.__code__.co_varnames
            for f in REGISTERED_ROUTES.values()
            if f.__name__ == endpoint
        ),
        None,
    )

    if function_vars is None:
        raise ValueError('No functions registered for endpoint "{}"'.format(endpoint))

    _check_parameters(endpoint, function_vars, path_vars)

    endpoint_routes = (
        r for r, f in REGISTERED_ROUTES.items() if f.__name__ == endpoint
    )

    matching_route = None

    for e_route in endpoint_routes:
        route_path_vars = [x[1] for x in e_route if isinstance(x, tuple)]

        if sorted(route_path_vars) == sorted(path_vars.keys()):
            if matching_route is not None:
                raise ValueError(
                    'Ambiguous paths for "{}" with this set of variables'.format(
                        endpoint
                    )
                )

            matching_route = e_route

    return matching_route


def _endpoint_route_to_path(endpoint, path_vars, endpoint_route, query):
    path = ""

    for section in endpoint_route:
        path += "/"

        if isinstance(section, str):
            path += section
        elif isinstance(section, tuple):
            var_type, var_name = section

            if not isinstance(path_vars[var_name], PATH_TYPES[var_type]["convert"]):
                raise ValueError(
                    'Variable "{}" has wrong variable type for function "{}"'.format(
                        var_name, endpoint
                    )
                )

            path += quote(str(path_vars[var_name]), safe="")

    if query:
        path += "?" + urlencode(sorted(list(query.items())), doseq=True)

    return path
