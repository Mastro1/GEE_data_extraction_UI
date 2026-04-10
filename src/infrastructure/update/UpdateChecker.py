import git
import sys
import os
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class UpdateInfo:
    update_available: bool
    current_version: str
    remote_version: str
    has_local_changes: bool
    error: Optional[str] = None


class UpdateChecker:
    def __init__(self):
        self.repo_root = Path(__file__).parent.parent.parent.parent
        self.version_file = self.repo_root / "VERSION"
        self._repo: Optional[git.Repo] = None

    def _get_repo(self) -> git.Repo:
        if self._repo is None:
            self._repo = git.Repo(self.repo_root)
        return self._repo

    def _read_local_version(self) -> str:
        try:
            return self.version_file.read_text().strip()
        except Exception:
            return "unknown"

    def check_for_updates(self) -> UpdateInfo:
        try:
            repo = self._get_repo()
        except git.InvalidGitRepositoryError:
            return UpdateInfo(
                update_available=False,
                current_version=self._read_local_version(),
                remote_version="unknown",
                has_local_changes=False,
                error="Not a git repository",
            )

        current_version = self._read_local_version()
        has_local_changes = repo.is_dirty(untracked_files=False)

        try:
            repo.remotes.origin.fetch()
        except Exception as e:
            return UpdateInfo(
                update_available=False,
                current_version=current_version,
                remote_version="unknown",
                has_local_changes=has_local_changes,
                error=f"Could not reach remote: {e}",
            )

        local_commit = repo.head.commit.hexsha
        try:
            remote_commit = repo.commit("origin/dev").hexsha
        except Exception:
            return UpdateInfo(
                update_available=False,
                current_version=current_version,
                remote_version="unknown",
                has_local_changes=has_local_changes,
                error="Could not resolve origin/dev",
            )

        if local_commit == remote_commit:
            return UpdateInfo(
                update_available=False,
                current_version=current_version,
                remote_version=current_version,
                has_local_changes=has_local_changes,
            )

        try:
            remote_version = repo.git.show("origin/dev:VERSION").strip()
        except Exception:
            remote_version = "unknown"

        return UpdateInfo(
            update_available=True,
            current_version=current_version,
            remote_version=remote_version,
            has_local_changes=has_local_changes,
        )

    def perform_update(self) -> tuple[bool, str]:
        try:
            repo = self._get_repo()
        except Exception as e:
            return False, f"Could not open repository: {e}"

        if repo.is_dirty(untracked_files=False):
            return (
                False,
                "You have uncommitted local changes. Run `git stash` in your terminal first, then retry.",
            )

        try:
            repo.remotes.origin.pull()
        except git.exc.GitCommandError as e:
            return False, f"git pull failed: {e}"
        except Exception as e:
            return False, f"Unexpected error during pull: {e}"

        requirements = self.repo_root / "requirements.txt"
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements), "--quiet"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False, f"pip install failed: {result.stderr[:300]}"

        return True, "Update complete. Restarting..."

    def restart_app(self):
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception:
            subprocess.Popen([sys.executable] + sys.argv)
            sys.exit(0)
