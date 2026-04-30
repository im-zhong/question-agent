"""Chapter tree builder — converts flat heading list to nested tree."""

from __future__ import annotations

from typing import Any

from question_agent.chapters.models import ChapterHeading


class ChapterNode:
    """A node in the chapter tree."""

    def __init__(
        self,
        heading: ChapterHeading,
        start_line: int,
        end_line: int,
        page_range: str | None = None,
    ):
        self.id: str = f"ch_{heading.line_index}"
        self.level: int = heading.level
        self.title: str = heading.title
        self.start_line: int = start_line
        self.end_line: int = end_line
        self.page_range: str | None = page_range
        self.children: list[ChapterNode] = []
        self._heading = heading

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "level": self.level,
            "title": self.title,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "page_range": self.page_range,
            "children": [c.to_dict() for c in self.children],
        }


def build_chapter_tree(
    headings: list[ChapterHeading],
    total_lines: int,
    page_map: dict[int, int] | None = None,
) -> list[ChapterNode]:
    """Build a nested chapter tree from a flat list of chapter headings.

    Args:
        headings: Flat list sorted by line_index.
        total_lines: Total number of paragraphs in the document.
        page_map: Optional mapping from line_index to page_number.

    Returns:
        List of top-level ChapterNode with nested children.
    """
    if not headings:
        return []

    nodes: list[ChapterNode] = []
    for i, h in enumerate(headings):
        start_line = h.line_index
        # end_line is the start_line of the next heading, or end of document
        if i + 1 < len(headings):
            end_line = headings[i + 1].line_index
        else:
            end_line = total_lines

        page_range = None
        if page_map:
            start_page = page_map.get(start_line)
            end_page = page_map.get(end_line - 1)
            if start_page is not None and end_page is not None:
                page_range = (
                    f"{start_page}" if start_page == end_page else f"{start_page}-{end_page}"
                )

        nodes.append(ChapterNode(h, start_line, end_line, page_range))

    # Build nested structure using a stack
    root: list[ChapterNode] = []
    stack: list[ChapterNode] = []

    for node in nodes:
        # Pop from stack until we find a parent (lower level number = higher level)
        while stack and stack[-1].level >= node.level:
            stack.pop()

        if stack:
            stack[-1].children.append(node)
        else:
            root.append(node)

        stack.append(node)

    return root
