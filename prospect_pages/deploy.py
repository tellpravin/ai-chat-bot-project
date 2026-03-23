"""
deploy.py — Push HTML files to GitHub Pages via PyGithub.
"""

import base64
import logging
from pathlib import Path

from github import Github, GithubException

from config import GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_REPO

logger = logging.getLogger(__name__)

_gh   = None
_repo = None


def _get_repo():
    global _gh, _repo
    if _repo is None:
        _gh   = Github(GITHUB_TOKEN)
        _repo = _gh.get_user(GITHUB_USERNAME).get_repo(GITHUB_REPO)
    return _repo


def push_page(local_path: str, slug: str) -> str:
    """
    Push a single HTML file to /pages/<slug>.html in the GitHub repo.
    Returns the public GitHub Pages URL on success.
    Raises GithubException on failure.
    """
    repo        = _get_repo()
    remote_path = f"pages/{slug}.html"
    content     = Path(local_path).read_bytes()
    encoded     = base64.b64encode(content).decode("utf-8")
    commit_msg  = f"Add prospect page: {slug}"

    # Check if the file already exists (needed for update vs create)
    try:
        existing = repo.get_contents(remote_path)
        repo.update_file(
            path    = remote_path,
            message = commit_msg,
            content = content,
            sha     = existing.sha,
        )
        logger.info("Updated %s", remote_path)
    except GithubException as exc:
        if exc.status == 404:
            # File does not exist yet — create it
            repo.create_file(
                path    = remote_path,
                message = commit_msg,
                content = content,
            )
            logger.info("Created %s", remote_path)
        else:
            raise

    url = (
        f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO}/pages/{slug}.html"
    )
    return url
