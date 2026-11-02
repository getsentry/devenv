from __future__ import annotations

import os
import re
import stat
import tempfile
from dataclasses import dataclass


class StorageMigrationBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class ColimaConfig:
    text: str
    lines: tuple[str, ...]
    docker_line: int | None
    docker_end: int | None
    docker_inline_empty: bool
    features_line: int | None
    features_end: int | None
    features_inline_empty: bool
    snapshotter: bool | None
    has_buildkit: bool
    root_disk_configured: bool
    disk_gib: int | None
    runtime: str | None


_MAPPING = re.compile(r"^(?P<indent> *)(?P<key>[A-Za-z0-9_-]+):(?P<rest>.*)$")


def _line_text(line: str) -> str:
    return line.rstrip("\r\n")


def _commentless(value: str) -> str:
    return value.split(" #", 1)[0].strip()


def _mapping(line: str, indent: int) -> tuple[str, str] | None:
    match = _MAPPING.match(_line_text(line))
    if match is None or len(match.group("indent")) != indent:
        return None
    key = match.group("key")
    value = match.group("rest")
    if not isinstance(key, str) or not isinstance(value, str):
        return None
    return key, _commentless(value)


def _quoted_key(line: str, indent: int) -> bool:
    text = _line_text(line)
    return (
        re.match(rf"^ {{{indent}}}[\"'][A-Za-z0-9_-]+[\"']:", text) is not None
    )


def _block_end(lines: tuple[str, ...], start: int, parent_indent: int) -> int:
    for index in range(start + 1, len(lines)):
        text = _line_text(lines[index])
        if not text.strip() or text.lstrip().startswith("#"):
            continue
        if "\t" in text[: len(text) - len(text.lstrip())]:
            raise StorageMigrationBlocked(
                "Colima's YAML uses tab indentation; edit the Docker features "
                "manually and set `containerd-snapshotter: false` for an "
                "overlay2 VM."
            )
        if not text.startswith(" "):
            return index
        if len(text) - len(text.lstrip()) <= parent_indent:
            return index
    return len(lines)


def read(path: str) -> ColimaConfig:
    try:
        mode = os.lstat(path).st_mode
    except OSError as error:
        raise StorageMigrationBlocked(
            f"Unable to inspect Colima config {path}: {error}. Inspect the "
            "config and set `docker.features.containerd-snapshotter` "
            "explicitly before starting Colima."
        ) from error
    if stat.S_ISLNK(mode):
        raise StorageMigrationBlocked(
            f"Colima config {path} is a symlink; devenv will not rewrite it. "
            "Inspect it and set `docker.features.containerd-snapshotter` "
            "explicitly before starting Colima."
        )
    if not stat.S_ISREG(mode):
        raise StorageMigrationBlocked(
            f"Colima config {path} is not a regular file; devenv will not "
            "rewrite it. Inspect it and set "
            "`docker.features.containerd-snapshotter` explicitly before "
            "starting Colima."
        )
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(
            descriptor, "r", encoding="utf-8", newline=""
        ) as config_file:
            text = config_file.read()
    except (OSError, UnicodeError) as error:
        raise StorageMigrationBlocked(
            f"Unable to read Colima config {path}: {error}. Inspect the "
            "config and set `docker.features.containerd-snapshotter` "
            "explicitly before starting Colima."
        ) from error

    lines = tuple(text.splitlines(keepends=True))
    if text and not lines:
        lines = (text,)
    if text.startswith("\ufeff"):
        raise StorageMigrationBlocked(
            f"Colima config {path} has a UTF-8 byte-order mark; devenv will "
            "not rewrite it. Set `docker.features.containerd-snapshotter` "
            "explicitly by hand."
        )

    top: dict[str, tuple[int, str]] = {}
    for index, line in enumerate(lines):
        content = _line_text(line)
        if not content.strip() or content.lstrip().startswith("#"):
            continue
        if content.startswith("\t"):
            raise StorageMigrationBlocked(
                f"Colima config {path} uses tab indentation; set "
                "`docker.features.containerd-snapshotter` manually."
            )
        entry = _mapping(line, 0)
        if entry is None and re.match(
            r'^["\'](?:docker|rootDisk|runtime|disk)["\']:', content
        ):
            raise StorageMigrationBlocked(
                f"Colima config {path} uses a quoted storage key; devenv "
                "will not rewrite it. Set `docker.features.containerd-"
                "snapshotter` explicitly."
            )
        if entry is None and not content.startswith(" "):
            quoted_mapping = re.match(r"^(?:'[^']+'|\"[^\"]+\")\s*:", content)
            if content.startswith(("{", "[")) or quoted_mapping is None:
                raise StorageMigrationBlocked(
                    f"Colima config {path} uses unsupported root YAML; "
                    "devenv will not rewrite it. Set "
                    "`docker.features.containerd-snapshotter` explicitly."
                )
        if entry is None and re.match(
            r"^(?:docker|rootDisk|runtime|disk)(?:\s|$)", content
        ):
            raise StorageMigrationBlocked(
                f"Colima config {path} has a malformed storage key; devenv "
                "will not rewrite it. Set `docker.features.containerd-"
                "snapshotter` explicitly."
            )
        if entry is None:
            continue
        key, value = entry
        if key in {"docker", "rootDisk", "runtime", "disk"}:
            if key in top:
                raise StorageMigrationBlocked(
                    f"Colima config {path} has duplicate `{key}` keys; "
                    "devenv will not rewrite it. Resolve the duplicate and "
                    "set `docker.features.containerd-snapshotter` explicitly."
                )
            top[key] = (index, value)

    docker = top.get("docker")
    docker_line = docker[0] if docker else None
    docker_value = docker[1] if docker else ""
    docker_inline_empty = docker_value == "{}"
    docker_end = (
        _block_end(lines, docker_line, 0)
        if docker_line is not None and not docker_inline_empty
        else docker_line + 1
        if docker_line is not None
        else None
    )
    if docker is not None and docker_value not in {"", "{}"}:
        raise StorageMigrationBlocked(
            f"Colima config {path} has a nonstandard inline `docker` value; "
            "devenv will not rewrite it. Set `docker.features.containerd-"
            "snapshotter` explicitly in a block mapping."
        )

    features_line: int | None = None
    features_end: int | None = None
    features_inline_empty = False
    snapshotter: bool | None = None
    has_buildkit = False
    if docker_line is not None and not docker_inline_empty:
        direct: dict[str, tuple[int, str]] = {}
        for index in range(docker_line + 1, docker_end or docker_line + 1):
            content = _line_text(lines[index])
            if not content.strip() or content.lstrip().startswith("#"):
                continue
            entry = _mapping(lines[index], 2)
            if entry is None:
                if _quoted_key(lines[index], 2):
                    raise StorageMigrationBlocked(
                        f"Colima config {path} uses a quoted Docker key; "
                        "devenv will not rewrite it. Set "
                        "`docker.features.containerd-snapshotter` explicitly."
                    )
                if len(content) - len(content.lstrip()) == 2:
                    raise StorageMigrationBlocked(
                        f"Colima config {path} has unsupported Docker YAML; "
                        "devenv will not rewrite it. Set "
                        "`docker.features.containerd-snapshotter` explicitly."
                    )
                continue
            key, value = entry
            if key in direct:
                raise StorageMigrationBlocked(
                    f"Colima config {path} has duplicate Docker `{key}` keys; "
                    "devenv will not rewrite it. Resolve the duplicate and "
                    "set `docker.features.containerd-snapshotter` explicitly."
                )
            direct[key] = (index, value)

        features = direct.get("features")
        if features is not None:
            features_line, features_value = features
            features_inline_empty = features_value == "{}"
            if features_value not in {"", "{}"}:
                raise StorageMigrationBlocked(
                    f"Colima config {path} has an unsupported inline "
                    "`docker.features` mapping; set "
                    "`docker.features.containerd-snapshotter` manually."
                )
            features_end = (
                _block_end(lines, features_line, 2)
                if not features_inline_empty
                else features_line + 1
            )
            nested: dict[str, tuple[int, str]] = {}
            if not features_inline_empty:
                for index in range(features_line + 1, features_end):
                    content = _line_text(lines[index])
                    if not content.strip() or content.lstrip().startswith("#"):
                        continue
                    entry = _mapping(lines[index], 4)
                    if entry is None:
                        raise StorageMigrationBlocked(
                            f"Colima config {path} has unsupported Docker "
                            "feature YAML; set "
                            "`docker.features.containerd-snapshotter` "
                            "explicitly."
                        )
                    key, value = entry
                    if key in nested:
                        raise StorageMigrationBlocked(
                            f"Colima config {path} has duplicate Docker "
                            f"feature `{key}` keys; devenv will not rewrite it."
                        )
                    nested[key] = (index, value)

            has_buildkit = "buildkit" in nested
            configured = nested.get("containerd-snapshotter")
            if configured is not None:
                value = configured[1]
                if value not in {"true", "false"}:
                    raise StorageMigrationBlocked(
                        f"Colima config {path} has a non-boolean "
                        "`containerd-snapshotter` value; choose `true` or "
                        "`false` explicitly."
                    )
                snapshotter = value == "true"

    runtime = top.get("runtime")
    runtime_value = runtime[1] if runtime else None
    if runtime is not None and (
        not runtime_value or not re.fullmatch(r"[A-Za-z0-9_-]+", runtime_value)
    ):
        raise StorageMigrationBlocked(
            f"Colima config {path} has a nonstandard runtime value; inspect "
            "it and configure Docker storage explicitly."
        )

    disk = top.get("disk")
    disk_value = disk[1] if disk else ""
    disk_gib: int | None = None
    if disk_value:
        try:
            disk_gib = int(disk_value)
        except ValueError:
            raise StorageMigrationBlocked(
                f"Colima config {path} has a nonstandard disk size; inspect "
                "it and configure Docker storage explicitly."
            ) from None

    return ColimaConfig(
        text=text,
        lines=lines,
        docker_line=docker_line,
        docker_end=docker_end,
        docker_inline_empty=docker_inline_empty,
        features_line=features_line,
        features_end=features_end,
        features_inline_empty=features_inline_empty,
        snapshotter=snapshotter,
        has_buildkit=has_buildkit,
        root_disk_configured="rootDisk" in top,
        disk_gib=disk_gib,
        runtime=runtime_value,
    )


def _newline(config: ColimaConfig) -> str:
    for line in config.lines:
        if line.endswith("\r\n"):
            return "\r\n"
        if line.endswith("\n"):
            return "\n"
    return "\n"


def _insert_lines(
    lines: list[str], insertion: int, entries: list[str], newline: str
) -> None:
    if insertion and not lines[insertion - 1].endswith(("\n", "\r")):
        lines[insertion - 1] = f"{lines[insertion - 1]}{newline}"
    lines[insertion:insertion] = [f"{entry}{newline}" for entry in entries]


def _replacement(config: ColimaConfig, snapshotter: bool) -> str:
    if config.snapshotter is not None:
        return config.text

    newline = _newline(config)
    lines = list(config.lines)
    features = config.features_line
    if features is not None and config.features_inline_empty:
        original = _line_text(lines[features])
        prefix, separator, comment = original.partition(" #")
        lines[features] = f"  features:{separator}{comment}{newline}"
        insertion = features + 1
        entries = []
        if not config.has_buildkit:
            entries.append("    buildkit: true")
        entries.append(
            f"    containerd-snapshotter: {str(snapshotter).lower()}"
        )
        _insert_lines(lines, insertion, entries, newline)
        return "".join(lines)

    if features is not None:
        insertion = config.features_end or features + 1
        entries = []
        if not config.has_buildkit:
            entries.append("    buildkit: true")
        entries.append(
            f"    containerd-snapshotter: {str(snapshotter).lower()}"
        )
        _insert_lines(lines, insertion, entries, newline)
        return "".join(lines)

    entries = [
        "  features:",
        "    buildkit: true",
        f"    containerd-snapshotter: {str(snapshotter).lower()}",
    ]
    if config.docker_line is None:
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] = f"{lines[-1]}{newline}"
        if lines and _line_text(lines[-1]).strip():
            lines.append(newline)
        lines.extend(f"{entry}{newline}" for entry in ("docker:", *entries))
        return "".join(lines)

    if config.docker_inline_empty:
        original = _line_text(lines[config.docker_line])
        prefix, separator, comment = original.partition(" #")
        lines[config.docker_line] = f"docker:{separator}{comment}{newline}"
        insertion = config.docker_line + 1
    else:
        insertion = config.docker_end or config.docker_line + 1
    _insert_lines(lines, insertion, entries, newline)
    return "".join(lines)


def set_snapshotter(path: str, snapshotter: bool) -> bool:
    config = read(path)
    replacement = _replacement(config, snapshotter)
    if replacement == config.text:
        return False

    try:
        metadata = os.stat(path, follow_symlinks=False)
    except OSError as error:
        raise StorageMigrationBlocked(
            f"Unable to inspect Colima config {path}: {error}. Set "
            "`docker.features.containerd-snapshotter` manually before "
            "starting Colima."
        ) from error

    temporary_path: str | None = None
    try:
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=".colima.yaml.", dir=os.path.dirname(path)
        )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as file:
            os.fchmod(file.fileno(), stat.S_IMODE(metadata.st_mode))
            file.write(replacement)
            file.flush()
            os.fsync(file.fileno())
        assert temporary_path is not None
        os.replace(temporary_path, path)
        temporary_path = None
    except OSError as error:
        raise StorageMigrationBlocked(
            f"Unable to update Colima config {path}: {error}. The original "
            "file was left in place; set "
            "`docker.features.containerd-snapshotter` manually before "
            "starting Colima."
        ) from error
    finally:
        if temporary_path is not None:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass

    return True
