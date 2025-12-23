import { Octokit } from "@octokit/rest"
import { Logger } from "./logger"

export interface RepoContext {
  owner: string
  repo: string
}

export function parseRepo(repo: string): RepoContext {
  const chunks = repo.replace(/\.git$/, "").split("/")
  if (chunks.length < 2) {
    throw new Error("Invalid repo format")
  }

  return {
    owner: chunks.at(-2)!,
    repo: chunks.at(-1)!,
  }
}

export interface Context {
  logger?: Logger
  octokit: Octokit
  repo: RepoContext
}
