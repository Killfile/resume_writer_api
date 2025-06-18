import pytest
from unittest.mock import mock_open, patch, MagicMock
import json
from app.skill_matcher import SkillMatcher

# tests/test_skill_matcher.py



@pytest.fixture
def mock_app_paths():
    mock = MagicMock()
    mock.get_local_path.return_value = "../mounted_files/full_skills.json"
    return mock

@pytest.fixture
def sample_skills_library():
    return {
        "highlighted experience": [
            {"company": "A", "keywords": ["python", "sql", "aws"]},
            {"company": "B", "keywords": ["excel", "tableau", "sql"]}
        ]
    }

@pytest.mark.parametrize(
    "skills_sought, expected_overlap, expected_unmatched",
    [
        pytest.param(
            ["Python", "SQL", "Java"],  
            [
                {"company": "a", "keywords": ["python", "sql"]},
                {"company": "b", "keywords": ["sql"]}
            ],
            ["java"],
            id="intersecting_case"
        ),
        pytest.param(
            ["Ruby", "Go"],  
            [
                {"company": "a", "keywords": []},
                {"company": "b", "keywords": []}
            ],
            ["ruby", "go"],
            id="non_intersecting_case"
        ),
        pytest.param(
            ["EXCEL", "AWS"],  
            [
                {"company": "a", "keywords": ["aws"]},
                {"company": "b", "keywords": ["excel"]}
            ],
            [],
            id="case_insensitivity"
        ),
    ]
)
def test_get_overlap(mock_app_paths, sample_skills_library, skills_sought, expected_overlap, expected_unmatched):
    mocked_open = mock_open(read_data=json.dumps(sample_skills_library))
    with patch("builtins.open", mocked_open):
        matcher = SkillMatcher(mock_app_paths)
        overlap, unmatched = matcher.get_overlap(skills_sought)
        # Only compare the relevant fields for overlap
        

        
        actual_overlap = [
            {"company": d["company"], "keywords": sorted(d["keywords"])}
            for d in overlap["highlighted experience"]
        ]

        expected_overlap = [
            {"company": d["company"], "keywords": sorted(d["keywords"])}
            for d in expected_overlap
        ]

        assert actual_overlap == expected_overlap
        assert sorted(unmatched) == sorted(expected_unmatched)