from dataclasses import dataclass

from github import Github

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
    github: Github
    repo: RepoContext
    logger: Logger | None = None
