import { readMetadata } from "./metadata"
import { Context } from "./utils"

export async function findComment(prNumber: number, { logger, octokit, repo }: Context) {
  logger?.debug("Searching for existing comment...")

  const commentTagPattern = createIdentifier("id", "main")

  for await (const { data: comments } of octokit.paginate.iterator(octokit.issues.listComments, {
    ...repo,
    issue_number: prNumber,
  })) {
    const comment = comments.find(({ body }) => body?.includes(commentTagPattern))

    if (comment) {
      return comment
    }
  }
}

export async function createComment(
  issueNumber: number,
  title: string,
  section: string,
  content: string,
  collapsed: boolean,
  configPath: string,
  { logger, octokit, repo }: Context,
) {
  logger?.debug("Creating comment...")

  const { data: comment } = await octokit.issues.createComment({
    ...repo,
    body: editCommentBody({
      body: await createBlankComment(configPath),
      collapsed,
      content,
      section,
      title,
    }),
    issue_number: issueNumber,
  })

  return comment
}

export async function updateComment(
  commentId: number,
  title: string,
  section: string,
  content: string,
  collapsed: boolean,
  { logger, octokit, repo }: Context,
) {
  logger?.debug("Updating comment...")

  const { data: comment } = await octokit.issues.getComment({
    ...repo,
    comment_id: commentId,
  })

  if (!comment?.body) {
    throw new Error("Comment body is empty")
  }

  await octokit.issues.updateComment({
    ...repo,
    body: editCommentBody({
      body: comment.body,
      collapsed,
      content,
      section,
      title,
    }),
    comment_id: commentId,
  })

  return comment
}

function createIdentifier(key: string, value: string) {
  return `<!-- mskelton/omni-comment ${key}="${value}" -->`
}

export async function createBlankComment(configPath: string) {
  const { intro, sections, title } = await readMetadata(configPath)

  return [
    createIdentifier("id", "main"),
    title ? `# ${title}` : undefined,
    intro,
    ...sections.flatMap((section) => [
      createIdentifier("start", section),
      createIdentifier("end", section),
    ]),
  ]
    .filter(Boolean)
    .join("\n\n")
}

export function editCommentBody({
  body,
  collapsed,
  content,
  section,
  title,
}: {
  body: string
  collapsed?: boolean
  content: string
  section: string
  title?: string
}) {
  const lines = body.split("\n")
  const startIndex = lines.findIndex((line) => line.includes(createIdentifier("start", section)))
  const endIndex = lines.findIndex((line) => line.includes(createIdentifier("end", section)))

  if (title) {
    content = [
      `<details${collapsed ? "" : " open"}>`,
      `<summary><h2>${title}</h2></summary>`,
      "",
      content,
      "",
      "</details>",
    ].join("\n")
  }

  // If the section is not found, append the content to the end of the comment
  // This is necessary as you add new comment sections
  if (startIndex === -1 || endIndex === -1) {
    return [
      ...lines,
      "",
      createIdentifier("start", section),
      content,
      createIdentifier("end", section),
    ].join("\n")
  }

  return [...lines.slice(0, startIndex + 1), content, ...lines.slice(endIndex)].join("\n")
}
