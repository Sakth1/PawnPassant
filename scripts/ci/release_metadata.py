#!/usr/bin/env python3
"""Shared CI helpers for release metadata and version bump detection."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


@dataclass(frozen=True)
class ParsedSemver:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...]


def parse_semver(version: str) -> ParsedSemver:
    match = SEMVER_PATTERN.fullmatch(version)
    if not match:
        raise ValueError(f"project.version '{version}' is not valid SemVer 2.0.0")

    prerelease = tuple(match.group(4).split(".")) if match.group(4) else ()
    return ParsedSemver(
        major=int(match.group(1)),
        minor=int(match.group(2)),
        patch=int(match.group(3)),
        prerelease=prerelease,
    )


def compare_identifier(left: str, right: str) -> int:
    left_is_num = left.isdigit()
    right_is_num = right.isdigit()

    if left_is_num and right_is_num:
        return (int(left) > int(right)) - (int(left) < int(right))
    if left_is_num and not right_is_num:
        return -1
    if not left_is_num and right_is_num:
        return 1
    return (left > right) - (left < right)


def compare_semver(left: str, right: str) -> int:
    left_version = parse_semver(left)
    right_version = parse_semver(right)

    left_core = (left_version.major, left_version.minor, left_version.patch)
    right_core = (right_version.major, right_version.minor, right_version.patch)

    if left_core != right_core:
        return (left_core > right_core) - (left_core < right_core)

    left_pre = left_version.prerelease
    right_pre = right_version.prerelease

    if not left_pre and not right_pre:
        return 0
    if not left_pre:
        return 1
    if not right_pre:
        return -1

    for left_ident, right_ident in zip(left_pre, right_pre):
        comp = compare_identifier(left_ident, right_ident)
        if comp != 0:
            return comp

    return (len(left_pre) > len(right_pre)) - (len(left_pre) < len(right_pre))


def read_pyproject(pyproject_path: Path) -> dict:
    with pyproject_path.open("rb") as file:
        return tomllib.load(file)


def read_version_from_pyproject(pyproject_path: Path) -> str:
    data = read_pyproject(pyproject_path)
    return data["project"]["version"]


def read_version_from_git_revision(revision: str, pyproject_relpath: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{revision}:{pyproject_relpath}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise FileNotFoundError(
            f"Could not load {pyproject_relpath!r} from git revision {revision!r}"
        )
    data = tomllib.loads(result.stdout)
    return data["project"]["version"]


def normalize_tag(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def append_outputs(path: Path, outputs: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8") as file:
        for key, value in outputs.items():
            file.write(f"{key}={value}\n")


def command_extract_release_metadata(args: argparse.Namespace) -> int:
    pyproject_path = Path(args.pyproject)
    data = read_pyproject(pyproject_path)

    version = data["project"]["version"]
    parse_semver(version)

    binary_name = (
        data.get("tool", {})
        .get("pawnpassant", {})
        .get("release", {})
        .get("binary_name", "Pawn-Passant")
    )
    artifact_stem = f"{binary_name}{version}"

    source_packages = data.get("tool", {}).get("flet", {}).get("source_packages", [])
    if not isinstance(source_packages, list):
        raise ValueError("tool.flet.source_packages must be a list")
    if "chess" not in source_packages:
        raise ValueError("tool.flet.source_packages must include 'chess'")

    release_tag = ""
    publish_enabled = "false"
    event_name = args.event_name

    if event_name == "release":
        release_tag = args.release_tag or ""
        publish_enabled = "true"
    elif event_name == "workflow_dispatch":
        release_tag = args.release_tag or ""
        publish_enabled = "true" if release_tag else "false"

    if publish_enabled == "true":
        if not release_tag:
            raise ValueError("release_tag is required when publish_enabled is true")
        if normalize_tag(release_tag) != version:
            raise ValueError(
                f"Release tag '{release_tag}' must match pyproject version '{version}' "
                f"(or 'v{version}')."
            )

    outputs = {
        "version": version,
        "artifact_stem": artifact_stem,
        "source_packages": ",".join(source_packages),
        "release_tag": release_tag,
        "publish_enabled": publish_enabled,
    }

    if args.github_output:
        append_outputs(Path(args.github_output), outputs)
    else:
        for key, value in outputs.items():
            print(f"{key}={value}")

    return 0


def command_detect_version_bump(args: argparse.Namespace) -> int:
    pyproject_path = Path(args.pyproject)
    current_version = read_version_from_pyproject(pyproject_path)
    parse_semver(current_version)

    before = args.before or ""
    all_zero = "0" * 40

    previous_version = ""
    should_release = "false"
    reason = ""

    if before and before != all_zero:
        try:
            previous_version = read_version_from_git_revision(before, args.pyproject)
            parse_semver(previous_version)
        except FileNotFoundError:
            reason = "previous pyproject.toml not found; skipping auto-release"
        else:
            comparison = compare_semver(current_version, previous_version)
            if comparison > 0:
                should_release = "true"
                reason = (
                    f"version increased from {previous_version} to {current_version}"
                )
            elif comparison == 0:
                reason = f"version unchanged at {current_version}"
            else:
                raise ValueError(
                    "project.version must increase on main/master. "
                    f"previous={previous_version}, current={current_version}"
                )
    else:
        reason = "no previous commit in push event; skipping auto-release"

    outputs = {
        "current_version": current_version,
        "previous_version": previous_version,
        "should_release": should_release,
        "tag": f"v{current_version}",
        "reason": reason,
    }

    if args.github_output:
        append_outputs(Path(args.github_output), outputs)
    else:
        for key, value in outputs.items():
            print(f"{key}={value}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CI helper utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser(
        "extract-release-metadata",
        help="Extract metadata required by release-build workflow",
    )
    extract_parser.add_argument("--pyproject", default="pyproject.toml")
    extract_parser.add_argument(
        "--event-name", default=os.getenv("GITHUB_EVENT_NAME", "")
    )
    extract_parser.add_argument("--release-tag", default="")
    extract_parser.add_argument(
        "--github-output", default=os.getenv("GITHUB_OUTPUT", "")
    )
    extract_parser.set_defaults(func=command_extract_release_metadata)

    detect_parser = subparsers.add_parser(
        "detect-version-bump",
        help="Detect whether pyproject version increased from previous commit",
    )
    detect_parser.add_argument("--pyproject", default="pyproject.toml")
    detect_parser.add_argument("--before", default=os.getenv("GITHUB_EVENT_BEFORE", ""))
    detect_parser.add_argument(
        "--github-output", default=os.getenv("GITHUB_OUTPUT", "")
    )
    detect_parser.set_defaults(func=command_detect_version_bump)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (KeyError, ValueError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    raise SystemExit(main())
