from collections import namedtuple

# Utilities for parsing and formatting namespaced N-V-R strings stored as
# git tags. An external system creates tags in the format:
#
#     {namespace}/[E!]N-V-R
#
# [E!]N-V-R is the package's Name-Version-Release with an optional epoch
# prefix. rpmautospec can read these tags to determine release history.

# In RPM, epochs are normally separated by a colon (e.g. "2:httpd-2.4.57-1"),
# but colons are not permitted in git ref names. We use "!" as the epoch
# separator instead (e.g. "2!httpd-2.4.57-1"). RPM treats epoch 0 as the
# implicit default, so only non-zero epochs are encoded in the tag.
GIT_TAG_EPOCH_SEPARATOR = "!"

NVR = namedtuple("NVR", ["name", "epoch", "version", "release"])


def parse_namespaced_nvr(tag_name: str, namespace: str) -> NVR:
    """Parse [E!]N-V-R from a git tag name under the given namespace.

    Expected format: {namespace}/[E!]N-V-R

    :param tag_name: the tag name (without refs/tags/)
    :param namespace: the namespace path to strip (e.g. "fedora/f44")
    :return: NVR namedtuple with name, epoch, version, release fields
    :raises ValueError: if tag_name doesn't belong to namespace or is unparseable
    """
    tagged_ns, remainder = tag_name.rsplit("/", 1)
    if tagged_ns != namespace:
        raise ValueError(f"Unexpected namespace: {tagged_ns!r} != {namespace!r}")
    return parse_nvr(remainder)


def parse_nvr(nvr: str) -> NVR:
    """Parse an [E!]N-V-R string into its components.

    Format: [E!]N-V-R where E is a numeric epoch (optional),
    N is the package name, V is version, R is release.

    :param nvr: an [E!]N-V-R string
    :return: NVR namedtuple with name, epoch, version, release fields
    :raises ValueError: if nvr cannot be parsed
    """
    try:
        epoch_name, version, release = nvr.rsplit("-", 2)
    except ValueError:
        raise ValueError(f"Cannot parse NVR: {nvr!r}")
    if not all((epoch_name, version, release)):
        raise ValueError(f"Cannot parse NVR: {nvr!r}")
    try:
        epoch, name = epoch_name.split(GIT_TAG_EPOCH_SEPARATOR, 1)
    except ValueError:
        epoch = ""
        name = epoch_name
    else:
        if not epoch.isdigit():
            raise ValueError(f"Epoch must be all digits, is {epoch!r}")
        if not name:
            raise ValueError(f"Empty name after epoch in NVR: {nvr!r}")
    return NVR(name=name, epoch=epoch, version=version, release=release)


def format_namespaced_nvr(namespace: str, name: str, epoch: str, version: str, release: str) -> str:
    """Create a namespaced [E!]N-V-R tag name.

    :param namespace: namespace path (e.g. "fedora/f44")
    :param name: package name
    :param epoch: epoch number as string, or empty for no epoch
    :param version: package version
    :param release: release number (without dist suffix)
    :return: formatted tag name (e.g. "fedora/f44/mesa-26.0.7-2")
    """
    nvr = format_nvr(name, epoch, version, release)
    return f"{namespace}/{nvr}"


def format_nvr(name: str, epoch: str, version: str, release: str) -> str:
    """Create an [E!]N-V-R string (with optional epoch prefix).

    :param name: package name
    :param epoch: epoch number as string; empty or "0" yields no epoch prefix
    :param version: package version
    :param release: package release number (raw number, no suffix/etc)
    :return: formatted package [E!]N-V-R
    """
    if epoch and epoch != "0":
        return f"{epoch}{GIT_TAG_EPOCH_SEPARATOR}{name}-{version}-{release}"
    return f"{name}-{version}-{release}"


def epoch_version(nvr: NVR) -> str:
    """Reconstruct epoch-version string from a parsed NVR.

    :param nvr: NVR namedtuple with epoch and version fields
    :return: "epoch:version" if epoch is set and non-zero, otherwise just "version"
    """
    if nvr.epoch and nvr.epoch != "0":
        return f"{nvr.epoch}:{nvr.version}"
    return nvr.version
