import shutil
import subprocess

import pytest

from rpmautospec_core.nvr_util import (
    NVR,
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
        with pytest.raises(ValueError):
            parse_nvr(nvr)

    @pytest.mark.parametrize(
        "nvr, expected",
        [
            ("mesa-26.0.7-2", NVR(name="mesa", epoch="", version="26.0.7", release="2")),
            (
                "python-requests-2.28.1-1",
                NVR(name="python-requests", epoch="", version="2.28.1", release="1"),
            ),
            (
                "kernel-6.8.0-0.rc6.47.fc40",
                NVR(name="kernel", epoch="", version="6.8.0", release="0.rc6.47.fc40"),
            ),
            # Underscore in version preserved (legal in RPM)
            ("pkg-1.0_rc1-2", NVR(name="pkg", epoch="", version="1.0_rc1", release="2")),
            # Epoch encoded with !
            (
                "2!httpd-2.4.57-1",
                NVR(name="httpd", epoch="2", version="2.4.57", release="1"),
            ),
            ("0!pkg-1.0-3", NVR(name="pkg", epoch="0", version="1.0", release="3")),
            ("10!pkg-2.0-1", NVR(name="pkg", epoch="10", version="2.0", release="1")),
        ],
    )
    def test_valid(self, nvr, expected):
        assert parse_nvr(nvr) == expected


class TestFormatNvr:
    """Tests for format_nvr."""

    def test_simple(self):
        assert format_nvr("mesa", "", "26.0.7", "2") == "mesa-26.0.7-2"

    def test_with_epoch(self):
        assert format_nvr("httpd", "2", "2.4.57", "1") == "2!httpd-2.4.57-1"

    def test_epoch_zero(self):
        # Epoch 0 is RPM's default and equivalent to absent; no prefix emitted.
        assert format_nvr("pkg", "0", "1.0", "3") == "pkg-1.0-3"

    def test_no_epoch(self):
        assert format_nvr("pkg", "", "1.0", "1") == "pkg-1.0-1"

    def test_roundtrip(self):
        nvr = format_nvr("python-requests", "", "2.28.1", "1")
        assert parse_nvr(nvr) == NVR(
            name="python-requests",
            epoch="",
            version="2.28.1",
            release="1",
        )

    def test_roundtrip_with_epoch(self):
        nvr = format_nvr("httpd", "2", "2.4.57", "1")
        assert parse_nvr(nvr) == NVR(
            name="httpd",
            epoch="2",
            version="2.4.57",
            release="1",
        )


class TestParseNamespacedNvr:
    """Tests for parse_namespaced_nvr — namespace stripping."""

    def test_wrong_namespace(self):
        with pytest.raises(ValueError):
            parse_namespaced_nvr("other/ns/pkg-1.0-1", "fedora/f44")

    def test_basic(self):
        result = parse_namespaced_nvr("fedora/f44/mesa-26.0.7-2", "fedora/f44")
        assert result == NVR(name="mesa", epoch="", version="26.0.7", release="2")

    def test_with_epoch(self):
        result = parse_namespaced_nvr("fedora/f44/2!httpd-2.4.57-1", "fedora/f44")
        assert result == NVR(name="httpd", epoch="2", version="2.4.57", release="1")

    def test_invalid_nvr_after_namespace(self):
        with pytest.raises(ValueError):
            parse_namespaced_nvr("fedora/f44/pkg", "fedora/f44")

    def test_alternate_namespace(self):
        result = parse_namespaced_nvr("fedora/f43/mesa-1.0-1", "fedora/f43")
        assert result == NVR(name="mesa", epoch="", version="1.0", release="1")


class TestFormatNamespacedNvr:
    """Tests for format_namespaced_nvr."""

    def test_basic(self):
        assert (
            format_namespaced_nvr("fedora/f44", "mesa", "", "26.0.7", "2")
            == "fedora/f44/mesa-26.0.7-2"
        )

    def test_with_epoch(self):
        assert format_namespaced_nvr("fedora/f44", "httpd", "2", "2.4.57", "1") == (
            "fedora/f44/2!httpd-2.4.57-1"
        )

    def test_epoch_zero_omitted(self):
        assert format_namespaced_nvr("fedora/f44", "pkg", "0", "1.0", "1") == (
            "fedora/f44/pkg-1.0-1"
        )

    def test_roundtrip(self):
        tag = format_namespaced_nvr("fedora/f44", "python-requests", "", "2.28.1", "1")
        parsed = parse_namespaced_nvr(tag, "fedora/f44")
        assert parsed == NVR(
            name="python-requests",
            epoch="",
            version="2.28.1",
            release="1",
        )


class TestEpochVersion:
    """Tests for epoch_version helper."""

    def test_with_epoch(self):
        assert epoch_version(NVR(name="x", epoch="2", version="1.0", release="1")) == "2:1.0"

    def test_epoch_zero(self):
        # Epoch 0 is equivalent to absent; RPM omits it.
        assert epoch_version(NVR(name="x", epoch="0", version="1.0", release="1")) == "1.0"

    def test_without_epoch(self):
        assert epoch_version(NVR(name="x", epoch="", version="1.0", release="1")) == "1.0"

    def test_no_epoch_key(self):
        assert epoch_version(NVR(name="x", epoch="", version="1.0", release="1")) == "1.0"


class TestGitUnsafeCharacters:
    """~ and ^ are valid in RPM versions but not in git ref names, so tags write = and ,."""

    CASES = (
        pytest.param("pkg", "", "1.0~rc1", "3", "pkg-1.0=rc1-3", id="tilde"),
        pytest.param("pkg", "", "1.0^20240101git", "3", "pkg-1.0,20240101git-3", id="caret"),
        pytest.param("pkg", "", "1.0~rc1^snap", "3", "pkg-1.0=rc1,snap-3", id="both"),
        pytest.param("pkg", "2", "1.0~~rc1", "3", "2!pkg-1.0==rc1-3", id="epoch-and-repeated"),
        pytest.param("pkg", "", "1.0_1+2", "3", "pkg-1.0_1+2-3", id="underscore-and-plus-kept"),
        pytest.param("pkg", "", "1.0", "3", "pkg-1.0-3", id="plain-unchanged"),
    )

    @pytest.mark.parametrize("name, epoch, version, release, expected", CASES)
    def test_format(self, name, epoch, version, release, expected):
        assert format_nvr(name, epoch, version, release) == expected
        assert format_namespaced_nvr("ns/x", name, epoch, version, release) == f"ns/x/{expected}"

    @pytest.mark.parametrize("name, epoch, version, release, expected", CASES)
    def test_parse_restores_the_version(self, name, epoch, version, release, expected):
        assert parse_nvr(expected) == NVR(name, epoch, version, release)
        assert parse_namespaced_nvr(f"ns/x/{expected}", "ns/x") == NVR(
            name, epoch, version, release
        )

    @pytest.mark.parametrize("name, epoch, version, release, expected", CASES)
    def test_epoch_version_of_the_parsed_tag_is_the_spec_version(
        self, name, epoch, version, release, expected
    ):
        parsed = parse_nvr(expected)
        assert epoch_version(parsed) == (f"{epoch}:{version}" if epoch else version)

    def test_underscore_is_not_a_tilde(self):
        """DEP-14 writes ~ as _, which would turn the version 1.0_1 into 1.0~1."""
        assert parse_nvr("pkg-1.0_1-3").version == "1.0_1"

    @pytest.mark.parametrize("name, epoch, version, release, expected", CASES)
    def test_git_accepts_the_tag(self, tmp_path, name, epoch, version, release, expected):
        git = shutil.which("git")
        if not git:
            pytest.skip("git is not available")
        tag = format_namespaced_nvr("fedora/f44", name, epoch, version, release)
        result = subprocess.run([git, "check-ref-format", f"refs/tags/{tag}"], check=False)
        assert result.returncode == 0, tag

    def test_git_rejects_the_unencoded_names(self):
        """The reason for the swap: git refuses a ~ or ^ in the name."""
        git = shutil.which("git")
        if not git:
            pytest.skip("git is not available")
        for version in ("1.0~rc1", "1.0^snap"):
            result = subprocess.run(
                [git, "check-ref-format", f"refs/tags/ns/pkg-{version}-1"], check=False
            )
            assert result.returncode != 0
