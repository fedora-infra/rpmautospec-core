from typing import Optional

# In RPM, the canonical format is epoch:name-version-release.
# In git tags, colon is invalid, so we use ! as the epoch separator.
# Full tag format: {namespace}/{epoch}!{name}-{version}-{release} (with epoch)
#              or: {namespace}/{name}-{version}-{release} (without epoch)
# RPM treats a missing epoch as 0, so epoch "0" and absent are equivalent
# and both omit the epoch prefix. Only non-zero epochs are encoded.
EPOCH_SEPARATOR = "!"


def parse_namespaced_nvr(tag_name: str, namespace: str) -> Optional[dict[str, str]]:
    """Parse N-V-R from a git tag name under the given namespace.

    Expected format: {namespace}/{epoch}!{name}-{version}-{release}

    :param tag_name: the tag name (without refs/tags/)
    :type tag_name: str
    :param namespace: the namespace path to strip (e.g. "fedora/f44")
    :type namespace: str
    :return: dict with "name", "epoch", "version", "release" keys, or None if unparseable
    :rtype: dict
    """
    if not tag_name.startswith(namespace + "/"):
        return None
    remainder = tag_name[len(namespace) + 1:]
    return parse_nvr(remainder)


def parse_nvr(nvr: str) -> Optional[dict[str, str]]:
    """Take a N-V-R string and split into Name, Version, and Release.

    If the name field is prefixed with {epoch}! (e.g. "2!pkg-1.0-1"),
    the epoch is extracted separately.

    :param nvr: an alleged N-V-R string
    :type nvr: str
    :return: dict with "name", "epoch", "version", and "release" keys,
        or None if unparseable
    :rtype: dict
    """
    split = nvr.rsplit("-", 2)
    if len(split) < 3 or not all(split):
        return None
    name = split[0]
    epoch = ""
    if EPOCH_SEPARATOR in name:
        epoch, name = name.split(EPOCH_SEPARATOR, 1)
        if not epoch.isdigit():
            return None
        if not name:
            return None
    return {"name": name, "epoch": epoch, "version": split[1], "release": split[2]}


def format_namespaced_nvr(namespace: str, name: str, version: str, release: str,
                          epoch: str = "") -> str:
    """Create a namespaced N-V-R tag name.

    :param namespace: namespace path (e.g. "fedora/f44")
    :type namespace: str
    :param name: package name
    :type name: str
    :param version: package version
    :type version: str
    :param release: release number (without dist suffix)
    :type release: str
    :param epoch: epoch number as string, or empty for no epoch
    :type epoch: str
    :return: formatted tag name (e.g. "fedora/f44/mesa-26.0.7-2")
    :rtype: str
    """
    nvr = format_nvr(name, version, release, epoch=epoch)
    return f"{namespace}/{nvr}"


def format_nvr(name: str, version: str, release: str, epoch: str = "") -> str:
    """Create a N-V-R string (with optional epoch prefix).

    :param name: package name
    :type name: str
    :param version: package version
    :type version: str
    :param release: package release number (raw number, no suffix/etc)
    :type release: str
    :param epoch: epoch number as string; empty or "0" yields no epoch prefix
    :type epoch: str
    :return: formatted package N-V-R
    :rtype: str
    """
    if epoch and epoch != "0":
        return f"{epoch}{EPOCH_SEPARATOR}{name}-{version}-{release}"
    return f"{name}-{version}-{release}"


def epoch_version(nvr: dict) -> str:
    """Reconstruct epoch-version string from a parsed NVR dict.

    :param nvr: dict with "epoch" and "version" keys
    :return: "epoch:version" if epoch is set and non-zero, otherwise just "version"
    """
    if nvr.get("epoch") and nvr["epoch"] != "0":
        return f"{nvr['epoch']}:{nvr['version']}"
    return nvr["version"]
