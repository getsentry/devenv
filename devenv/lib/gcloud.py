from __future__ import annotations

import os
import platform
import tempfile
from shutil import which

from devenv.constants import bin_root
from devenv.constants import MACHINE
from devenv.constants import root
from devenv.constants import user_path
from devenv.lib import archive
from devenv.lib import fs

_sha256 = {
    "google-cloud-sdk-461.0.0-linux-x86_64.tar.gz": "066d84a50e8d3e83f8f32096f0aa88b947fe747280dd3b16991540ab79895ae5",
    "google-cloud-sdk-461.0.0-darwin-arm.tar.gz": "5d01298b5a9811be9d08d037a6785d58e910a947841d3ea38418fd46799211b0",
    "google-cloud-sdk-461.0.0-darwin-x86_64.tar.gz": "4d85319f89d7b90b661bf083e7ef8cfa167b7e05a152ba26f8fe7b7b3c98234b",
}


class UnexpectedPlatformError(Exception):
    pass


def build_name(version: str) -> str | None:
    system = platform.system()
    if system == "Linux":
        if MACHINE == "x86_64":
            return f"google-cloud-sdk-{version}-linux-x86_64.tar.gz"
        raise UnexpectedPlatformError(f"linux {MACHINE} not supported")
    elif system == "Darwin":
        if MACHINE == "x86_64":
            return f"google-cloud-sdk-{version}-darwin-x86_64.tar.gz"
        return f"google-cloud-sdk-{version}-darwin-arm.tar.gz"
    else:
        raise UnexpectedPlatformError(f"Unexpected OS: {platform.platform()}")


def download_and_unpack_archive(name: str, into: str) -> None:
    url = f"https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/{name}"

    archive_file = archive.download(url, _sha256[name], dest=f"{into}/{name}")
    archive.unpack(archive_file, into)


def _install(version: str, into: str) -> None:
    name = build_name(version)
    if name is None:
        return

    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        download_and_unpack_archive(name, tmpd)

        # the archive was atomically placed into tmpd so
        # these are on the same fs and can be atomically moved too
        os.replace(f"{tmpd}/google-cloud-sdk", f"{into}/google-cloud-sdk")

    # I think gcloud will support 3.11 for quite some time, but this could
    # change to be more flexible in the future.
    # We run gcloud on 3.11 in gocd prod and it's been great,
    # and we may as well reuse devenv's internal python.
    fs.write_script(
        f"{into}/gcloud",
        f"""#!/bin/sh
exec /usr/bin/env CLOUDSDK_PYTHON={root}/python PATH={into}/google-cloud-sdk/bin:{user_path} gcloud "$@"
""",
    )
    fs.write_script(
        f"{into}/gsutil",
        f"""#!/bin/sh
exec /usr/bin/env CLOUDSDK_PYTHON={root}/python PATH={into}/google-cloud-sdk/bin:{user_path} gsutil "$@"
""",
    )


def install(version: str) -> None:
    if (
        which("gcloud", path=bin_root) == f"{bin_root}/gcloud"
        and which("gsutil", path=bin_root) == f"{bin_root}/gsutil"
    ):
        return

    _install(version, bin_root)

    # we should actually run gcloud
    if not os.path.exists(f"{bin_root}/gcloud"):
        raise SystemExit("Failed to install gcloud!")
