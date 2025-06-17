import os
import json
import pytest
from app.resume_writer import ResumeWriter
from app.app_paths import AppPaths

@pytest.fixture
def sample_resume_json():
    # Load the sample resume.json from the mounted_files directory
    with open(os.path.join(os.path.dirname(__file__), "../../mounted_files/resume.json"), encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def dummy_paths(tmp_path):
    # Create a dummy AppPaths that returns the correct template paths
    class DummyAppPaths():
        def get_local_path(self, subdir, filename):
            # Point to the test templates directory
            return os.path.join(os.path.dirname(__file__), "test_templates", filename)
    return DummyAppPaths()

@pytest.fixture
def dummy_templates(tmp_path):
    # Create minimal template files for testing
    templates_dir = tmp_path / "test_templates"
    templates_dir.mkdir()
    (templates_dir / "resume2.html").write_text(
        "<html><body><<SummaryTextPlaceholder>><<ExperiencePlaceholder>><<ICExperiencePlaceholder>><<EducationPlaceholder>><<TrainingPlaceholder>><<ProjectsPlaceholder>></body></html>"
    )
    (templates_dir / "job2.html").write_text(
        "<div><<CompanyPlaceholder>> <<LocationPlaceholder>> <<TitlePlaceholder>> <<DatesPlaceholder>><<ResponsibilitiesPlaceholder>></div>"
    )
    (templates_dir / "job_responsibility2.html").write_text(
        "<li><<ResponsibilityPlaceholder>></li>"
    )
    (templates_dir / "education2.html").write_text(
        "<div><<DegreePlaceholder>> <<SchoolPlaceholder>> <<LocationPlaceholder>> <<DatesPlaceholder>></div>"
    )
    (templates_dir / "project2.html").write_text(
        "<div><<NamePlaceholder>> <<DetailPlaceholder>> <<DatesPlaceholder>></div>"
    )
    return templates_dir

def test_write_resume(sample_resume_json, dummy_paths, dummy_templates, monkeypatch):
    # Patch AppPaths.get_local_path to use dummy_templates
    def fake_get_local_path(self, subdir, filename):
        return os.path.join(dummy_templates, filename)
    monkeypatch.setattr(dummy_paths, "get_local_path", fake_get_local_path.__get__(dummy_paths, type(dummy_paths)))

    writer = ResumeWriter(dummy_paths, None)
    html = writer.write_resume(sample_resume_json)
    assert "<html>" in html
    assert sample_resume_json["summary"]["description"] in html
    for exp in sample_resume_json["experience"]:
        assert exp["company"] in html
        for resp in exp["responsibilities"].values():
            assert resp in html
    for ic_exp in sample_resume_json["individual_contributor_experience"]:
        assert ic_exp["company"] in html
    for edu in sample_resume_json["education"]:
        assert edu["degree"] in html
    for proj in sample_resume_json["side_projects"]:
        assert proj["project"] in html

def test_render_job_experience(sample_resume_json, dummy_paths, dummy_templates, monkeypatch):
    def fake_get_local_path(self, subdir, filename):
        return os.path.join(dummy_templates, filename)
    monkeypatch.setattr(dummy_paths, "get_local_path", fake_get_local_path.__get__(dummy_paths, type(dummy_paths)))

    writer = ResumeWriter(dummy_paths, None)
    templates = {
        "job": (dummy_templates / "job2.html").read_text(),
        "responsibility": (dummy_templates / "job_responsibility2.html").read_text(),
    }
    exp = sample_resume_json["experience"][0]
    html = writer._render_job_experience(exp, templates["job"], templates["responsibility"])
    assert exp["company"] in html
    for resp in exp["responsibilities"].values():
        assert resp in html

def test_render_education(sample_resume_json, dummy_paths, dummy_templates, monkeypatch):
    def fake_get_local_path(self, subdir, filename):
        return os.path.join(dummy_templates, filename)
    monkeypatch.setattr(dummy_paths, "get_local_path", fake_get_local_path.__get__(dummy_paths, type(dummy_paths)))

    writer = ResumeWriter(dummy_paths, None)
    template = (dummy_templates / "education2.html").read_text()
    edu = sample_resume_json["education"][0]
    html = writer._render_education(edu, template)
    assert edu["degree"] in html
    assert edu["institution"] in html

def test_render_project(sample_resume_json, dummy_paths, dummy_templates, monkeypatch):
    def fake_get_local_path(self, subdir, filename):
        return os.path.join(dummy_templates, filename)
    monkeypatch.setattr(dummy_paths, "get_local_path", fake_get_local_path.__get__(dummy_paths, type(dummy_paths)))

    writer = ResumeWriter(dummy_paths, None)
    template = (dummy_templates / "project2.html").read_text()
    proj = sample_resume_json["side_projects"][0]
    html = writer._render_project(proj, template)
    assert proj["project"] in html
    assert proj["description"] in html