import pytest
from unittest.mock import mock_open, patch, MagicMock
import json

from app.responsibility_archive import CompanyArchive, ResponsibilityArchive

@pytest.fixture
def mock_pathfinder():
    mock = MagicMock()
    mock.get_local_path.return_value = "../mounted_files/responsibility_archive.json"
    return mock

@pytest.fixture
def simple_archive_json():
    return {
        "companies": [
            {
                "name": "TechCorp",
                "responsibilities": [
                    {
                        "id": "1", 
                        "variants": [
                            "TechCorp.responsibilities.1.A", 
                            "TechCorp.responsibilities.1.B", 
                            "TechCorp.responsibilities.1.C"
                            ]
                    },
                    {"id": "2", "variants": ["TechCorp.responsibilities.2.A", "TechCorp.responsibilities.2.B"]}
                ]
            }
        ]
    }

def test_responsibility_archive_load(mock_pathfinder, simple_archive_json):
    mocked_open = mock_open(read_data=json.dumps(simple_archive_json))

    with patch("builtins.open", mocked_open):
        archive = ResponsibilityArchive(mock_pathfinder)
        archive.load()

        assert "TechCorp" in archive._responsibilities
        company = archive._responsibilities["TechCorp"]
        assert isinstance(company, CompanyArchive)
        assert company.name == "TechCorp"
        assert {resp.id for resp in company.responsibilities} == {"1", "2"}
        responsibility_variants = [r for r in company.responsibilities if r.id == "1"]
        assert len(responsibility_variants) == 1
        assert len(responsibility_variants[0].variants) == 3
        assert responsibility_variants[0].variants == [
            "TechCorp.responsibilities.1.A",
            "TechCorp.responsibilities.1.B",
            "TechCorp.responsibilities.1.C"
        ]

def test_get_responsibility_variants_by_id(mock_pathfinder, simple_archive_json):
    mocked_open = mock_open(read_data=json.dumps(simple_archive_json))

    with patch("builtins.open", mocked_open):
        archive = ResponsibilityArchive(mock_pathfinder)
        archive.load()

        variants = archive.get_responsibility_variants_by_id("TechCorp", "1")
        assert variants == [
            "TechCorp.responsibilities.1.A",
            "TechCorp.responsibilities.1.B",
            "TechCorp.responsibilities.1.C"
        ]

        variants = archive.get_responsibility_variants_by_id("TechCorp", "2")
        assert variants == [
            "TechCorp.responsibilities.2.A",
            "TechCorp.responsibilities.2.B"
        ]

        with pytest.raises(ValueError):
            archive.get_responsibility_variants_by_id("NonExistentCompany", "1")

        with pytest.raises(ValueError):
            archive.get_responsibility_variants_by_id("TechCorp", "NonExistentId")

def test_archive_responsibilities_from_resume(mock_pathfinder, simple_archive_json):
    mocked_open = mock_open(read_data=json.dumps(simple_archive_json))

    with patch("builtins.open", mocked_open):
        archive = ResponsibilityArchive(mock_pathfinder)
        archive.load()

        resume_json = {
            "experience": [
                {
                    "company": "TechCorp",
                    "responsibilities": {
                        "1": "TechCorp.responsibilities.1.D",
                        "2": "TechCorp.responsibilities.2.B",
                        "3": "TechCorp.responsibilities.3.A"}
                }
            ]
        }

        responsibilities = archive.archive_responsibilities_from_resume(resume_json)

        appended_responsibility_list = archive.get_responsibility_variants_by_id("TechCorp", "1")
        assert appended_responsibility_list == [
            "TechCorp.responsibilities.1.A",
            "TechCorp.responsibilities.1.B",
            "TechCorp.responsibilities.1.C",
            "TechCorp.responsibilities.1.D"
        ]

        duplicated_responsibility_list = archive.get_responsibility_variants_by_id("TechCorp", "2")
        assert duplicated_responsibility_list == [
            "TechCorp.responsibilities.2.A",
            "TechCorp.responsibilities.2.B"
        ]

        newly_created_responsibility_list = archive.get_responsibility_variants_by_id("TechCorp", "3")
        assert newly_created_responsibility_list == ["TechCorp.responsibilities.3.A"]

def test_responsibility_archive_write_calls_file_write(mock_pathfinder, simple_archive_json):
    mocked_open = mock_open(read_data=json.dumps(simple_archive_json))

    with patch("builtins.open", mocked_open):
        archive = ResponsibilityArchive(mock_pathfinder)
        archive.load()

        resume_json = {
            "experience": [
                {
                    "company": "TechCorp",
                    "responsibilities": {
                        "1": "TechCorp.responsibilities.1.D",
                        "2": "TechCorp.responsibilities.2.B",
                        "3": "TechCorp.responsibilities.3.A"}
                }
            ]
        }

        archive.archive_responsibilities_from_resume(resume_json)
        archive.write()

        # Verify that the file was written
        mocked_open.assert_called_with(mock_pathfinder.get_local_path("../mounted_files/", "responsibility_archive.json"), "w", encoding="utf-8")
        handle = mocked_open()
        handle.write.assert_called_once()  # Ensure write was called

def test_get_responsibility_variants_by_company_name(mock_pathfinder, simple_archive_json):
    mocked_open = mock_open(read_data=json.dumps(simple_archive_json))

    with patch("builtins.open", mocked_open):
        archive = ResponsibilityArchive(mock_pathfinder)
        archive.load()

        responsibliities = archive.get_responsibility_variants_by_company("TechCorp")
        assert responsibliities == [
                    {
                        "id": "1", 
                        "variants": [
                            "TechCorp.responsibilities.1.A", 
                            "TechCorp.responsibilities.1.B", 
                            "TechCorp.responsibilities.1.C"
                            ]
                    },
                    {"id": "2", "variants": ["TechCorp.responsibilities.2.A", "TechCorp.responsibilities.2.B"]}
                ]

        with pytest.raises(ValueError):
            archive.get_responsibility_variants_by_id("NonExistentCompany", "1")
       
