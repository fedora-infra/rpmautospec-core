import pytest

from rpmautospec_core.nvr_util import (
    epoch_version,
    format_namespaced_nvr,
    format_nvr,
    parse_namespaced_nvr,
    parse_nvr,
)


class TestParseNvr:
    """Tests for parse_nvr — the core NVR parsing logic."""

    @pytest.mark.parametrize(
        "nvr",
        [
            "pkg",
            "pkg-1.0",
            "-1.0-1",
            "pkg--1",
            "pkg-1.0-",
            # Non-numeric epoch
            "foo!pkg-1.0-1",
            # Empty name after epoch
            "2!-1.0-1",
        ],
    )
    def test_invalid(self, nvr):
        assert parse_nvr(nvr) is None

    @pytest.mark.parametrize(
        "nvr, expected",
        [
            ("mesa-26.0.7-2", {"name": "mesa", "epoch": "", "version": "26.0.7", "release": "2"}),
            ("python-requests-2.28.1-1", {"name": "python-requests", "epoch": "", "version": "2.28.1", "release": "1"}),
            ("kernel-6.8.0-0.rc6.47.fc40", {"name": "kernel", "epoch": "", "version": "6.8.0", "release": "0.rc6.47.fc40"}),
            # Underscore in version preserved (legal in RPM)
            ("pkg-1.0_rc1-2", {"name": "pkg", "epoch": "", "version": "1.0_rc1", "release": "2"}),
            # Epoch encoded with !
            ("2!httpd-2.4.57-1", {"name": "httpd", "epoch": "2", "version": "2.4.57", "release": "1"}),
            ("0!pkg-1.0-3", {"name": "pkg", "epoch": "0", "version": "1.0", "release": "3"}),
            ("10!pkg-2.0-1", {"name": "pkg", "epoch": "10", "version": "2.0", "release": "1"}),
        ],
    )
    def test_valid(self, nvr, expected):
        assert parse_nvr(nvr) == expected


class TestFormatNvr:
    """Tests for format_nvr."""

    def test_simple(self):
        assert format_nvr("mesa", "26.0.7", "2") == "mesa-26.0.7-2"

    def test_with_epoch(self):
        assert format_nvr("httpd", "2.4.57", "1", epoch="2") == "2!httpd-2.4.57-1"

    def test_epoch_zero(self):
        # Epoch 0 is RPM's default and equivalent to absent; no prefix emitted.
        assert format_nvr("pkg", "1.0", "3", epoch="0") == "pkg-1.0-3"

    def test_no_epoch(self):
        assert format_nvr("pkg", "1.0", "1") == "pkg-1.0-1"

    def test_roundtrip(self):
        nvr = format_nvr("python-requests", "2.28.1", "1")
        assert parse_nvr(nvr) == {"name": "python-requests", "epoch": "", "version": "2.28.1", "release": "1"}

    def test_roundtrip_with_epoch(self):
        nvr = format_nvr("httpd", "2.4.57", "1", epoch="2")
        assert parse_nvr(nvr) == {"name": "httpd", "epoch": "2", "version": "2.4.57", "release": "1"}


class TestParseNamespacedNvr:
    """Tests for parse_namespaced_nvr — namespace stripping."""

    def test_wrong_namespace(self):
        assert parse_namespaced_nvr("other/ns/pkg-1.0-1", "fedora/f44") is None

    def test_basic(self):
        result = parse_namespaced_nvr("fedora/f44/mesa-26.0.7-2", "fedora/f44")
        assert result == {"name": "mesa", "epoch": "", "version": "26.0.7", "release": "2"}

    def test_with_epoch(self):
        result = parse_namespaced_nvr("fedora/f44/2!httpd-2.4.57-1", "fedora/f44")
        assert result == {"name": "httpd", "epoch": "2", "version": "2.4.57", "release": "1"}

    def test_invalid_nvr_after_namespace(self):
        assert parse_namespaced_nvr("fedora/f44/pkg", "fedora/f44") is None

    def test_alternate_namespace(self):
        result = parse_namespaced_nvr("fedora/f43/mesa-1.0-1", "fedora/f43")
        assert result == {"name": "mesa", "epoch": "", "version": "1.0", "release": "1"}


class TestFormatNamespacedNvr:
    """Tests for format_namespaced_nvr."""

    def test_basic(self):
        assert format_namespaced_nvr("fedora/f44", "mesa", "26.0.7", "2") == "fedora/f44/mesa-26.0.7-2"

    def test_with_epoch(self):
        assert format_namespaced_nvr("fedora/f44", "httpd", "2.4.57", "1", epoch="2") == (
            "fedora/f44/2!httpd-2.4.57-1"
        )

    def test_epoch_zero_omitted(self):
        assert format_namespaced_nvr("fedora/f44", "pkg", "1.0", "1", epoch="0") == (
            "fedora/f44/pkg-1.0-1"
        )

    def test_roundtrip(self):
        tag = format_namespaced_nvr("fedora/f44", "python-requests", "2.28.1", "1")
        parsed = parse_namespaced_nvr(tag, "fedora/f44")
        assert parsed == {"name": "python-requests", "epoch": "", "version": "2.28.1", "release": "1"}


class TestEpochVersion:
    """Tests for epoch_version helper."""

    def test_with_epoch(self):
        assert epoch_version({"epoch": "2", "version": "1.0"}) == "2:1.0"

    def test_epoch_zero(self):
        # Epoch 0 is equivalent to absent; RPM omits it.
        assert epoch_version({"epoch": "0", "version": "1.0"}) == "1.0"

    def test_without_epoch(self):
        assert epoch_version({"epoch": "", "version": "1.0"}) == "1.0"

    def test_no_epoch_key(self):
        assert epoch_version({"version": "1.0"}) == "1.0"
