import yaml from "js-yaml"
import fs from "node:fs/promises"

export type Metadata = {
  intro?: string
  sections: string[]
  title?: string
}

export async function readMetadata(configPath: string) {
  const metadata = await fs.readFile(configPath, "utf8")

  return yaml.load(metadata) as Metadata
}
