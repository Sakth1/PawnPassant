"""Tests for release metadata extraction and version bump detection helpers."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.ci.release_metadata import (command_detect_version_bump,
                                         command_extract_release_metadata,
                                         compare_semver)


class Args:
    """Simple namespace helper for calling command functions in tests."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class TestSemverComparator(unittest.TestCase):
    """Validate semantic-version comparison edge cases."""

    def test_semver_ordering_cases(self):
        cases = [
            ("0.1.0", "0.1.0", 0),
            ("0.1.1", "0.1.0", 1),
            ("0.2.0", "0.1.9", 1),
            ("1.0.0-alpha.2", "1.0.0-alpha.1", 1),
            ("1.0.0", "1.0.0-rc.1", 1),
            ("1.0.0-alpha.1", "1.0.0", -1),
        ]

        for left, right, expected in cases:
            with self.subTest(left=left, right=right):
                self.assertEqual(compare_semver(left, right), expected)


class TestReleaseMetadataExtraction(unittest.TestCase):
    """Cover release metadata extraction for supported workflow events."""

    def test_extract_release_metadata_for_release_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            pyproject = Path(tmp) / "pyproject.toml"
            output = Path(tmp) / "out.txt"
            pyproject.write_text(
                """
[project]
name = "pawnpassant"
version = "1.2.3-alpha.1"

[tool.flet]
source_packages = ["chess"]

[tool.pawnpassant.release]
binary_name = "Pawn-Passant"
""".strip() + "\n",
                encoding="utf-8",
            )

            args = Args(
                pyproject=str(pyproject),
                event_name="release",
                release_tag="v1.2.3-alpha.1",
                github_output=str(output),
            )
            rc = command_extract_release_metadata(args)
            self.assertEqual(rc, 0)

            written = output.read_text(encoding="utf-8")
            self.assertIn("version=1.2.3-alpha.1", written)
            self.assertIn("release_tag=v1.2.3-alpha.1", written)
            self.assertIn("publish_enabled=true", written)
            self.assertIn("source_packages=chess", written)

    def test_extract_release_metadata_rejects_mismatched_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            pyproject = Path(tmp) / "pyproject.toml"
            pyproject.write_text(
                """
[project]
name = "pawnpassant"
version = "1.2.3"

[tool.flet]
source_packages = ["chess"]
""".strip() + "\n",
                encoding="utf-8",
            )

            args = Args(
                pyproject=str(pyproject),
                event_name="workflow_dispatch",
                release_tag="v1.2.4",
                github_output="",
            )

            with self.assertRaises(ValueError):
                command_extract_release_metadata(args)


class TestVersionBumpDetection(unittest.TestCase):
    """Exercise the auto-release decision logic against temporary git histories."""

    def _init_repo_with_versions(self, versions):
        """Create a temporary git repository with one commit per provided version."""

        temp_dir = tempfile.TemporaryDirectory()
        repo = Path(temp_dir.name)

        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "ci-tests@example.com"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "CI Tests"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        for version in versions:
            (repo / "pyproject.toml").write_text(
                (
                    "[project]\n"
                    'name = "pawnpassant"\n'
                    f'version = "{version}"\n\n'
                    "[tool.flet]\n"
                    'source_packages = ["chess"]\n'
                ),
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "add", "pyproject.toml"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "--allow-empty", "-m", f"version {version}"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

        return temp_dir, repo

    def test_detect_version_bump_true_when_version_increased(self):
        temp_dir, repo = self._init_repo_with_versions(
            ["1.0.0-alpha.1", "1.0.0-alpha.2"]
        )
        with temp_dir:
            before = subprocess.check_output(
                ["git", "rev-parse", "HEAD~1"], cwd=repo, text=True
            ).strip()
            output = repo / "out.txt"
            args = Args(
                pyproject="pyproject.toml", before=before, github_output=str(output)
            )

            prev_cwd = Path.cwd()
            try:
                os.chdir(repo)
                rc = command_detect_version_bump(args)
            finally:
                os.chdir(prev_cwd)

            self.assertEqual(rc, 0)
            written = output.read_text(encoding="utf-8")
            self.assertIn("should_release=true", written)
            self.assertIn("current_version=1.0.0-alpha.2", written)

    def test_detect_version_bump_false_when_unchanged(self):
        temp_dir, repo = self._init_repo_with_versions(["1.0.0", "1.0.0"])
        with temp_dir:
            before = subprocess.check_output(
                ["git", "rev-parse", "HEAD~1"], cwd=repo, text=True
            ).strip()
            output = repo / "out.txt"
            args = Args(
                pyproject="pyproject.toml", before=before, github_output=str(output)
            )

            prev_cwd = Path.cwd()
            try:
                os.chdir(repo)
                rc = command_detect_version_bump(args)
            finally:
                os.chdir(prev_cwd)

            self.assertEqual(rc, 0)
            written = output.read_text(encoding="utf-8")
            self.assertIn("should_release=false", written)
            self.assertIn("reason=version unchanged at 1.0.0", written)

    def test_detect_version_bump_skips_when_previous_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "ci-tests@example.com"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "CI Tests"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

            (repo / "README.md").write_text("seed\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "README.md"], cwd=repo, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", "seed"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            before = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()

            (repo / "pyproject.toml").write_text(
                (
                    "[project]\n"
                    'name = "pawnpassant"\n'
                    'version = "1.0.0"\n\n'
                    "[tool.flet]\n"
                    'source_packages = ["chess"]\n'
                ),
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "add", "pyproject.toml"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "add pyproject"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

            output = repo / "out.txt"
            args = Args(
                pyproject="pyproject.toml", before=before, github_output=str(output)
            )

            prev_cwd = Path.cwd()
            try:
                os.chdir(repo)
                rc = command_detect_version_bump(args)
            finally:
                os.chdir(prev_cwd)

            self.assertEqual(rc, 0)
            written = output.read_text(encoding="utf-8")
            self.assertIn("should_release=false", written)
            self.assertIn(
                "previous pyproject.toml not found; skipping auto-release", written
            )

    def test_detect_version_bump_skips_when_previous_version_key_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "ci-tests@example.com"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "CI Tests"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

            # Intentionally malformed: version key typo in previous revision.
            (repo / "pyproject.toml").write_text(
                (
                    "[project]\n"
                    'name = "pawnpassant"\n'
                    'veversion = "1.0.0"\n\n'
                    "[tool.flet]\n"
                    'source_packages = ["chess"]\n'
                ),
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "add", "pyproject.toml"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "bad metadata"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            before = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()

            (repo / "pyproject.toml").write_text(
                (
                    "[project]\n"
                    'name = "pawnpassant"\n'
                    'version = "1.0.1"\n\n'
                    "[tool.flet]\n"
                    'source_packages = ["chess"]\n'
                ),
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "add", "pyproject.toml"],
                cwd=repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "fix metadata and bump version"],
                cwd=repo,
                check=True,
                capture_output=True,
            )

            output = repo / "out.txt"
            args = Args(
                pyproject="pyproject.toml", before=before, github_output=str(output)
            )

            prev_cwd = Path.cwd()
            try:
                os.chdir(repo)
                rc = command_detect_version_bump(args)
            finally:
                os.chdir(prev_cwd)

            self.assertEqual(rc, 0)
            written = output.read_text(encoding="utf-8")
            self.assertIn("should_release=false", written)
            self.assertIn("previous pyproject.toml invalid", written)

    def test_detect_version_bump_raises_on_downgrade(self):
        temp_dir, repo = self._init_repo_with_versions(["1.0.0", "1.0.0-alpha.1"])
        with temp_dir:
            before = subprocess.check_output(
                ["git", "rev-parse", "HEAD~1"], cwd=repo, text=True
            ).strip()
            args = Args(pyproject="pyproject.toml", before=before, github_output="")

            prev_cwd = Path.cwd()
            try:
                os.chdir(repo)
                with self.assertRaises(ValueError):
                    command_detect_version_bump(args)
            finally:
                os.chdir(prev_cwd)


if __name__ == "__main__":
    unittest.main()
