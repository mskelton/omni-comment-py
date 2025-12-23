from dataclasses import dataclass

import httpx

from .logger import Logger


@dataclass
class RepoContext:
    owner: str
    repo: str


def parse_repo(repo: str) -> RepoContext:
    cleaned = repo.removesuffix(".git")
    chunks = cleaned.split("/")
    if len(chunks) < 2:
        raise ValueError("Invalid repo format")

    return RepoContext(owner=chunks[-2], repo=chunks[-1])


@dataclass
class Context:
    client: httpx.Client
    repo: RepoContext
    logger: Logger | None = None


def create_client(token: str) -> httpx.Client:
    return httpx.Client(
        base_url="https://api.github.com",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
