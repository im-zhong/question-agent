"""Tests for rule-based knowledge point detection."""

from question_agent.knowledge.detector import detect_knowledge_points_rule


class TestConceptMarker:
    def test_shi_zhi_detects_concept(self) -> None:
        paragraphs = [
            {"text": "加速度是指速度变化量与发生这一变化所用时间的比值。"},
        ]
        result = detect_knowledge_points_rule(paragraphs)
        assert len(result) == 1
        assert result[0].tags[0].category == "concept"
        assert result[0].method == "rule"
        assert result[0].confidence == 0.7
        assert result[0].source_line_start == 0

    def test_ding_yi_detects_concept(self) -> None:
        paragraphs = [{"text": "力的定义为物体对物体的作用。"}]
        result = detect_knowledge_points_rule(paragraphs)
        assert len(result) == 1
        assert result[0].tags[0].category == "concept"

    def test_cheng_wei_detects_concept(self) -> None:
        paragraphs = [{"text": "这种运动称为匀速直线运动。"}]
        result = detect_knowledge_points_rule(paragraphs)
        assert len(result) == 1
        assert result[0].tags[0].category == "concept"


class TestFormulaMarker:
    def test_gong_shi_detects_formula(self) -> None:
        paragraphs = [{"text": "公式：v = v₀ + at"}]
        result = detect_knowledge_points_rule(paragraphs)
        assert len(result) == 1
        assert result[0].tags[0].category == "formula"

    def test_ding_li_detects_formula(self) -> None:
        paragraphs = [{"text": "定理：勾股定理 a² + b² = c²"}]
        result = detect_knowledge_points_rule(paragraphs)
        assert len(result) == 1
        assert result[0].tags[0].category == "formula"


class TestProcedureMarker:
    def test_step_numbering_detects_procedure(self) -> None:
        paragraphs = [
            {"text": "第一步：将物体放在天平上。第二步：读取质量数值。第三步：记录数据。"},
        ]
        result = detect_knowledge_points_rule(paragraphs)
        assert len(result) == 1
        assert result[0].tags[0].category == "procedure"


class TestDeduplication:
    def test_same_paragraph_multiple_markers_deduped(self) -> None:
        # "是指" (concept) and "公式：" (formula) in same paragraph
        paragraphs = [
            {"text": "加速度是指速度变化量与时间的比值。公式：a = Δv/Δt"},
        ]
        result = detect_knowledge_points_rule(paragraphs)
        assert len(result) == 2
        categories = {kp.tags[0].category for kp in result}
        assert "concept" in categories
        assert "formula" in categories

    def test_same_category_not_duplicated(self) -> None:
        # Two concept markers in same paragraph -> only one concept KP
        paragraphs = [
            {"text": "加速度是指速度变化量与时间的比值，也称为速度变化率。"},
        ]
        result = detect_knowledge_points_rule(paragraphs)
        concept_count = sum(1 for kp in result if kp.tags[0].category == "concept")
        assert concept_count == 1


class TestNoMarkerText:
    def test_pure_narrative_returns_empty(self) -> None:
        paragraphs = [{"text": "今天天气很好，阳光明媚。"}]
        result = detect_knowledge_points_rule(paragraphs)
        assert result == []

    def test_no_text_key_returns_empty(self) -> None:
        paragraphs = [{"other": "data"}]
        result = detect_knowledge_points_rule(paragraphs)
        assert result == []


class TestEmptyInput:
    def test_empty_list_returns_empty(self) -> None:
        result = detect_knowledge_points_rule([])
        assert result == []

    def test_empty_text_paragraphs_skipped(self) -> None:
        paragraphs = [{"text": ""}, {"text": "   "}]
        result = detect_knowledge_points_rule(paragraphs)
        assert result == []


class TestFactMarker:
    def test_shi_shi_detects_fact(self) -> None:
        paragraphs = [{"text": "事实：光速约为3×10⁸ m/s。"}]
        result = detect_knowledge_points_rule(paragraphs)
        assert len(result) == 1
        assert result[0].tags[0].category == "fact"


class TestPrincipleMarker:
    def test_yuan_li_detects_principle(self) -> None:
        paragraphs = [{"text": "原理：杠杆原理通过力臂的长度来平衡力的大小。"}]
        result = detect_knowledge_points_rule(paragraphs)
        assert len(result) == 1
        assert result[0].tags[0].category == "principle"
