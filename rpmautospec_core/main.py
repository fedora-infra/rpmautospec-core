import re
from collections import namedtuple
from functools import lru_cache
from pathlib import Path
from typing import Union


# the %autorelease macro including parameters
AUTORELEASE_MACRO = "autorelease(e:s:pb:n)"

autorelease_re = re.compile(r"%(?:autorelease(?:\s|$)|\{\??autorelease(?:\s+[^\}]*)?\})")
changelog_re = re.compile(r"^%changelog(?:\s.*)?$", re.IGNORECASE)
autochangelog_re = re.compile(r"\s*%(?:autochangelog|\{\??autochangelog\})\s*")
autorelease_definition_re = re.compile(r"^\s*%define\s+autorelease\s*\(")


SpecfileFeatures = namedtuple(
    "SpecfileFeatures",
    (
        "has_autorelease",
        "has_autochangelog",
        "changelog_lineno",
        "autochangelog_lineno",
        "has_autorelease_definition",
        "autorelease_definition_lineno",
        "is_processed",
    ),
)


@lru_cache(maxsize=1024)
def _check_specfile_features(specpath: Path, mtime: float, size: int) -> SpecfileFeatures:
    has_autorelease = False
    changelog_lineno = None
    autochangelog_lineno = None
    autorelease_definition_lineno = None

    with specpath.open("r", encoding="utf-8", errors="replace") as specfile:
        for lineno, line in enumerate(iter(specfile), start=1):
            line = line.rstrip("\n")

            if changelog_lineno is None:
                if not has_autorelease and autorelease_re.search(line):
                    has_autorelease = True

                if changelog_re.match(line):
                    changelog_lineno = lineno

            if autochangelog_lineno is None and autochangelog_re.match(line):
                autochangelog_lineno = lineno

            if autorelease_definition_lineno is None and autorelease_definition_re.match(line):
                autorelease_definition_lineno = lineno

    is_processed = bool(autorelease_definition_lineno)

    return SpecfileFeatures(
        has_autorelease=has_autorelease,
        has_autochangelog=bool(autochangelog_lineno),
        changelog_lineno=changelog_lineno,
        autochangelog_lineno=autochangelog_lineno,
        has_autorelease_definition=bool(autorelease_definition_lineno),
        autorelease_definition_lineno=autorelease_definition_lineno,
        is_processed=is_processed,
    )


def check_specfile_features(specpath: Union[Path, str], *, enable_caching=True) -> SpecfileFeatures:
    if not isinstance(specpath, Path):
        specpath = Path(specpath).resolve()

    stat_result = specpath.stat()

    if enable_caching:
        return _check_specfile_features(specpath, stat_result.st_mtime, stat_result.st_size)
    else:
        return _check_specfile_features.__wrapped__(
            specpath, stat_result.st_mtime, stat_result.st_size
        )


def specfile_uses_rpmautospec(
    specpath: Union[Path, str],
    check_autorelease: bool = True,
    check_autochangelog: bool = True,
    check_is_processed: bool = True,
) -> bool:
    """Check whether or not an RPM spec file uses rpmautospec features.

    :param specpath: Path to the RPM spec file
    :param check_autorelease: Whether to check for use of %autorelease,
        defaults to True
    :param check_autochangelog: Whether to check for use of
        %autochangelog, defaults to True
    :param check_is_processed: Whether to report features if file is
        already processed, defaults to True
    :return: Whether the spec file uses the specified features
    """
    if not check_autorelease and not check_autochangelog:
        raise ValueError(
            "One of check_autorelease and check_autochangelog must be set"
        )

    features = check_specfile_features(specpath)

    retval = False

    if check_autorelease:
        retval = retval or features.has_autorelease

    if check_autochangelog:
        retval = retval or features.has_autochangelog

    if check_is_processed:
        retval = retval and not features.is_processed

    return retval
