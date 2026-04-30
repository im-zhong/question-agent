"""Tests for chapter tree builder."""

from question_agent.chapters import ChapterHeading, build_chapter_tree


class TestBuildChapterTree:
    def test_flat_to_nested(self):
        """[L1 A, L2 B, L2 C, L1 D] → A.children=[B,C]; D."""
        headings = [
            ChapterHeading(line_index=0, level=1, title="A", confidence=0.9, method="pattern"),
            ChapterHeading(line_index=2, level=2, title="B", confidence=0.9, method="pattern"),
            ChapterHeading(line_index=4, level=2, title="C", confidence=0.9, method="pattern"),
            ChapterHeading(line_index=6, level=1, title="D", confidence=0.9, method="pattern"),
        ]
        tree = build_chapter_tree(headings, total_lines=8)
        assert len(tree) == 2
        assert tree[0].title == "A"
        assert tree[1].title == "D"
        assert len(tree[0].children) == 2
        assert tree[0].children[0].title == "B"
        assert tree[0].children[1].title == "C"

    def test_end_lines(self):
        """Each node's end_line is the start_line of the next heading."""
        headings = [
            ChapterHeading(line_index=0, level=1, title="Ch1", confidence=0.9, method="pattern"),
            ChapterHeading(line_index=5, level=1, title="Ch2", confidence=0.9, method="pattern"),
        ]
        tree = build_chapter_tree(headings, total_lines=10)
        assert tree[0].end_line == 5
        assert tree[1].end_line == 10

    def test_node_has_required_fields(self):
        """Each node has id, level, title, start_line, end_line, children."""
        headings = [
            ChapterHeading(line_index=0, level=1, title="Test", confidence=0.9, method="pattern"),
        ]
        tree = build_chapter_tree(headings, total_lines=3)
        d = tree[0].to_dict()
        assert "id" in d
        assert "level" in d
        assert "title" in d
        assert "start_line" in d
        assert "end_line" in d
        assert "children" in d
        assert "page_range" in d

    def test_empty_headings(self):
        assert build_chapter_tree([], total_lines=0) == []

    def test_three_level_nesting(self):
        """L1, L2, L3, L2 → correct nesting."""
        headings = [
            ChapterHeading(line_index=0, level=1, title="Ch1", confidence=0.9, method="pattern"),
            ChapterHeading(line_index=1, level=2, title="S1", confidence=0.9, method="pattern"),
            ChapterHeading(line_index=2, level=3, title="SS1", confidence=0.9, method="pattern"),
            ChapterHeading(line_index=3, level=2, title="S2", confidence=0.9, method="pattern"),
        ]
        tree = build_chapter_tree(headings, total_lines=5)
        assert len(tree) == 1
        assert tree[0].title == "Ch1"
        assert len(tree[0].children) == 2
        assert tree[0].children[0].title == "S1"
        assert len(tree[0].children[0].children) == 1
        assert tree[0].children[0].children[0].title == "SS1"
        assert tree[0].children[1].title == "S2"

    def test_page_range(self):
        """Page range is computed from page_map."""
        headings = [
            ChapterHeading(line_index=0, level=1, title="A", confidence=0.9, method="pattern"),
            ChapterHeading(line_index=5, level=1, title="B", confidence=0.9, method="pattern"),
        ]
        page_map = {0: 1, 4: 1, 5: 2, 9: 2}
        tree = build_chapter_tree(headings, total_lines=10, page_map=page_map)
        assert tree[0].page_range == "1"
        assert tree[1].page_range == "2"
