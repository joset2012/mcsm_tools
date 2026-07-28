import time

import pytest

from mcsm_tools.backup_manager import _format_size, _get_name, _is_file, _parse_mtime


@pytest.mark.parametrize(
    "size, expected",
    [
        (0, "0.0 B"),
        (512, "512.0 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1024 ** 2, "1.0 MB"),
        (1024 ** 3, "1.0 GB"),
        (1024 ** 4, "1.0 TB"),
    ],
)
def test_format_size(size, expected):
    assert _format_size(size) == expected


def test_parse_mtime_handles_missing_value():
    assert _parse_mtime(None) == "-"
    assert _parse_mtime(0) == "-"


def test_parse_mtime_seconds_and_milliseconds():
    seconds = 1_700_000_000
    expected = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(seconds))

    assert _parse_mtime(seconds) == expected
    assert _parse_mtime(seconds * 1000) == expected


def test_parse_mtime_truncates_strings():
    assert _parse_mtime("2024-01-02T03:04:05.678Z") == "2024-01-02T03:04:05"


def test_get_name_defaults_to_placeholder():
    assert _get_name({"name": "world.zip"}) == "world.zip"
    assert _get_name({}) == "?"


@pytest.mark.parametrize(
    "item, expected",
    [
        ({"isFile": True}, True),
        ({"isFile": False}, False),
        ({"type": 1}, True),
        ({"type": 0}, False),
        ({"type": "file"}, True),
        ({"type": "directory"}, False),
        ({}, False),
    ],
)
def test_is_file(item, expected):
    assert _is_file(item) is expected
