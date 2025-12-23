from dataclasses import dataclass, field

import yaml


@dataclass
class Metadata:
    sections: list[str] = field(default_factory=list)
    intro: str | None = None
    title: str | None = None


async def read_metadata(config_path: str) -> Metadata:
    with open(config_path) as f:
        data = yaml.safe_load(f)

    return Metadata(
        sections=data.get("sections", []),
        intro=data.get("intro"),
        title=data.get("title"),
    )
