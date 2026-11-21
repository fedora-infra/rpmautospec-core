import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TextIO

import pytest

import rpmautospec_core
from rpmautospec_core import main

__HERE__ = Path(__file__).parent


class TestMain:
    """Test the rpmautospec_core.main module"""

    @staticmethod
    def _generate_spec_with_features(
        specfile: TextIO,
        *,
        with_autorelease=True,
        with_autorelease_braces=False,
        autorelease_flags="",
        with_changelog=True,
        with_autochangelog=True,
        with_autorelease_definition=True,
    ):
        if autorelease_flags and not autorelease_flags.startswith(" "):
            autorelease_flags = " " + autorelease_flags

        base = 3
        if with_autorelease:
            if with_autorelease_braces:
                autorelease_blurb = f"%{{autorelease{autorelease_flags}}}"
            else:
                autorelease_blurb = f"%autorelease{autorelease_flags}"

            if with_autorelease == "macro":
                release_blurb = f"%global baserelease {autorelease_blurb}\nRelease: %baserelease"
                base = 4
            else:
                release_blurb = f"Release: {autorelease_blurb}"
        else:
            release_blurb = "Release: 1"

        contents = [
            "Line 1",
            "Line 2",
            release_blurb,
            f"Line {base + 1}",
            f"Line {base + 2}",
        ]

        if with_autorelease_definition:
            contents[1] = "%define autorelease()"
        if with_changelog:
            contents.append("%changelog")
        if with_autochangelog:
            contents.append("%autochangelog")
        else:
            contents.extend(
                [
                    "* Fri Jan 02 1970 Some Name <email@example.com>",
                    "- This %autorelease should be ignored.",
                    "",
                    "* Thu Jan 01 1970 Some Name <email@example.com>",
                    "- some entry",
                ]
            )

        print("\n".join(contents), file=specfile)
        specfile.flush()

    @pytest.mark.parametrize(
        "enable_caching", (True, False), ids=("enable-caching", "disable-caching")
    )
    @pytest.mark.parametrize(
        "with_autorelease, with_autorelease_braces, autorelease_flags, with_changelog,"
        + " with_autochangelog, with_autorelease_definition",
        (
            # various feature combinations
            pytest.param(True, False, "", True, True, False, id="all features"),
            pytest.param("macro", False, "", True, True, False, id="all features, macro"),
            pytest.param(
                True, False, "-b 200", True, True, False, id="with non standard base release number"
            ),
            pytest.param(True, True, "", True, True, False, id="all features, braces"),
            pytest.param("macro", True, "", True, True, False, id="all features, braces, macro"),
            pytest.param(
                True,
                True,
                "-b 200",
                True,
                True,
                False,
                id="with non standard base release number, braces",
            ),
            # processed spec file
            pytest.param(True, False, "", True, False, True, id="preprocessed"),
            pytest.param("macro", False, "", True, False, True, id="preprocessed, macro"),
            pytest.param(True, True, "", True, False, True, id="preprocessed, braces"),
            # no features used
            pytest.param(False, False, "", True, False, False, id="nothing"),
        ),
    )
    @pytest.mark.parametrize("specpath_type", (str, Path))
    def test_check_specfile_features(
        self,
        specpath_type,
        with_autorelease,
        with_autorelease_braces,
        autorelease_flags,
        with_changelog,
        with_autochangelog,
        with_autorelease_definition,
        enable_caching,
    ):
        main._check_specfile_features.cache_clear()

        with NamedTemporaryFile(mode="w+") as specfile:
            self._generate_spec_with_features(
                specfile,
                with_autorelease=with_autorelease,
                with_autorelease_braces=with_autorelease_braces,
                autorelease_flags=autorelease_flags,
                with_changelog=with_changelog,
                with_autochangelog=with_autochangelog,
                with_autorelease_definition=with_autorelease_definition,
            )

            features = main.check_specfile_features(
                specpath_type(specfile.name), enable_caching=enable_caching
            )

            assert features.has_autorelease == bool(with_autorelease)
            if with_changelog:
                assert features.changelog_lineno == 7 if with_autorelease == "macro" else 6
            else:
                assert features.changelog_lineno is None
            assert features.has_autochangelog == with_autochangelog
            if with_autochangelog:
                assert features.autochangelog_lineno == 8 if with_autorelease == "macro" else 7
            else:
                assert features.autochangelog_lineno is None
            assert features.has_autorelease_definition == with_autorelease_definition
            assert features.is_processed == with_autorelease_definition
            if with_autorelease_definition:
                assert features.autorelease_definition_lineno == 2
            else:
                assert features.autorelease_definition_lineno is None

            cache_info = main._check_specfile_features.cache_info()
            assert cache_info.hits == 0
            assert cache_info.misses == (1 if enable_caching else 0)

            features_repeated = main.check_specfile_features(
                specpath_type(specfile.name), enable_caching=enable_caching
            )
            assert features == features_repeated

            cache_info = main._check_specfile_features.cache_info()
            assert cache_info.hits == (1 if enable_caching else 0)
            assert cache_info.misses == (1 if enable_caching else 0)

    def test_specfile_uses_rpmautospec_no_macros(self, caplog):
        """Test no macros on specfile_uses_rpmautospec()"""
        caplog.set_level(logging.DEBUG)

        specfile_path = __HERE__ / "test-specfiles" / "no-macros.spec"

        result = main.specfile_uses_rpmautospec(specfile_path)

        assert result is False

    @pytest.mark.parametrize("processed", (False, True), ids=("unprocessed", "processed"))
    def test_specfile_uses_rpmautospec(self, processed, caplog):
        """Test both features on specfile_uses_rpmautospec()"""
        caplog.set_level(logging.DEBUG)

        if processed:
            specfile_path = __HERE__ / "test-specfiles" / "autorelease-processed.spec"
        else:
            specfile_path = __HERE__ / "test-specfiles" / "autorelease-autochangelog.spec"

        result = main.specfile_uses_rpmautospec(specfile_path)
        assert result is not processed

        # Check only if the %autochangelog macro is present & unprocessed.
        result_no_autorelease_processed = main.specfile_uses_rpmautospec(
            specfile_path, check_autorelease=False, check_is_processed=False
        )
        assert result_no_autorelease_processed is not processed

        # Check only that the %autorelease macro is present, ignore if it’s processed.
        result_no_autochangelog_processed = main.specfile_uses_rpmautospec(
            specfile_path, check_autochangelog=False, check_is_processed=False
        )
        assert result_no_autochangelog_processed is True

    def test_specfile_uses_rpmautospec_autorelease_only(self, caplog):
        """Test autorelease only on specfile_uses_rpmautospec()"""
        caplog.set_level(logging.DEBUG)

        specfile_path = __HERE__ / "test-specfiles" / "autorelease-only.spec"

        result = main.specfile_uses_rpmautospec(specfile_path)
        assert result is True

        result_no_autorelease = main.specfile_uses_rpmautospec(
            specfile_path, check_autorelease=False
        )
        assert result_no_autorelease is False

    def test_specfile_uses_rpmautospec_autochangelog_only(self, caplog):
        """Test autochangelog only on specfile_uses_rpmautospec()"""
        caplog.set_level(logging.DEBUG)

        specfile_path = __HERE__ / "test-specfiles" / "autochangelog-only.spec"

        result = main.specfile_uses_rpmautospec(specfile_path)
        assert result is True

        result_no_changelog = main.specfile_uses_rpmautospec(
            specfile_path, check_autochangelog=False
        )
        assert result_no_changelog is False

    def test_specfile_uses_rpmautospec_throws_error(self, caplog):
        """Test specfile_uses_rpmautospec() throws an error when all params are false"""
        caplog.set_level(logging.DEBUG)

        specfile_path = __HERE__ / "test-specfiles" / "autochangelog-only.spec"

        result = main.specfile_uses_rpmautospec(specfile_path)
        assert result is True

        with pytest.raises(ValueError):
            main.specfile_uses_rpmautospec(
                specfile_path,
                check_autochangelog=False,
                check_autorelease=False,
                check_is_processed=False,
            )

    def test_autochangelog_macro(self):
        """%autochangelog accepts the options its users set and the package exports the macro."""
        assert main.AUTOCHANGELOG_MACRO == "autochangelog(m:d:)"
        assert rpmautospec_core.AUTOCHANGELOG_MACRO is main.AUTOCHANGELOG_MACRO

    @pytest.mark.parametrize(
        "line",
        (
            "%autochangelog",
            "%autochangelog -m tagged-only -d highest",
            "  %autochangelog",
            "\t%autochangelog",
            "%{autochangelog}",
            "%{?autochangelog}",
            "%{autochangelog -m tagged-only}",
            "%{?autochangelog -m tagged-only -d highest}",
            "%{autochangelog }",
            # What follows the macro name is no part of the name.
            "%autochangelog%{nil}",
            "%autochangelog,-m x",
            "%autochangelog-x",
            "%{autochangelog -m x}tail",
        ),
    )
    def test_autochangelog_re_match(self, line):
        assert main.autochangelog_re.match(line)

    @pytest.mark.parametrize(
        "line",
        (
            "%autochangelogx",
            "%autochangelogx -m tagged-only",
            "%{autochangelogx}",
            "%{autochangelog_x -m tagged-only}",
            "%%autochangelog",
            "%{autochangelog -m tagged-only",
            "%{autochangelog%{nil} -m x}",
            "%?autochangelog",
            "%{!?autochangelog}",
            "# %autochangelog",
            "x %autochangelog",
            "",
        ),
    )
    def test_autochangelog_re_no_match(self, line):
        assert main.autochangelog_re.match(line) is None

    def test_autochangelog_re_export(self):
        assert rpmautospec_core.autochangelog_re is main.autochangelog_re

    @pytest.mark.parametrize(
        "line, expected_lineno",
        (
            ("%autochangelog", 4),
            ("%autochangelog -m tagged-only", 4),
            ("%{autochangelog}", 4),
            ("%{?autochangelog}", 4),
            ("%{autochangelog -m tagged-only -d highest}", 4),
            ("%{?autochangelog -m tagged-only}", 4),
            ("%autochangelogx", None),
            ("%{autochangelogx -m tagged-only}", None),
        ),
    )
    def test_check_specfile_features_braced_autochangelog(self, tmp_path, line, expected_lineno):
        specfile = tmp_path / "pkg.spec"
        specfile.write_text(f"Name: pkg\nRelease: %autorelease\n%changelog\n{line}\n")

        features = main.check_specfile_features(specfile, enable_caching=False)

        assert features.has_autochangelog == (expected_lineno is not None)
        assert features.autochangelog_lineno == expected_lineno
