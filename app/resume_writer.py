import json
from app.app_paths import AppPaths

class ResumeWriter:
    def __init__(self, pathfinder: AppPaths, responsibilites: list):
        self._pathfinder = pathfinder
        self._revised_experience = responsibilites

    def _read_template(self, filename:str):
        with open(self._pathfinder.get_local_path("resume_templates", filename)) as f:
            contents = f.read()
        return contents
    
    def write_resume(self, resume_json):
        templates = {}
        templates["resume"] = self._read_template("resume2.html")
        templates["job"] = self._read_template("job2.html")
        templates["responsibility"] = self._read_template("job_responsibility2.html")
        templates["education"] = self._read_template("education2.html")
        templates["project"] = self._read_template("project2.html")

        html = {}

        html["summary_text"] = resume_json["summary"]["description"]

        html["experience"] = ""
        for experience in resume_json["experience"]:
            job_experience = self._render_job_experience(experience, templates["job"], templates["responsibility"])
            html["experience"] += job_experience
        
        html["ic_experience_html"] = ""
        for experience in resume_json["individual_contributor_experience"]:
            job_experience = self._render_job_experience(experience, templates["job"], templates["responsibility"])
            html["ic_experience_html"] += job_experience

        
        html["education"] = ""
        for degree in resume_json["education"]:
            degree_html = self._render_education(degree,templates["education"])
            html["education"] += degree_html

        html["training"] = ""
        for learning in resume_json["training"]:
            learning_html = self._render_training(learning, templates["education"])
            html["training"] += learning_html

        html["projects"] = ""
        for project in resume_json["side_projects"]:
            project_html = self._render_project(project, templates["project"])
            html["projects"] += project_html
        
        resume_html = templates["resume"]
        resume_html = resume_html.replace("<<SummaryTextPlaceholder>>", html["summary_text"])
        resume_html = resume_html.replace("<<ExperiencePlaceholder>>",html["experience"])
        resume_html = resume_html.replace("<<ICExperiencePlaceholder>>", html["ic_experience_html"])
        resume_html = resume_html.replace("<<EducationPlaceholder>>", html["education"])
        resume_html = resume_html.replace("<<TrainingPlaceholder>>", html["training"])
        resume_html = resume_html.replace("<<ProjectsPlaceholder>>", html["projects"])

        return resume_html


    def _render_job_experience(self, experience, job_html_template, job_responsibility_html_template):
        job_experience = str(job_html_template)
        job_experience = job_experience.replace("<<CompanyPlaceholder>>", experience["company"])
        job_experience = job_experience.replace("<<LocationPlaceholder>>", experience["location"])
        job_experience = job_experience.replace("<<TitlePlaceholder>>", experience["position"])
        job_experience = job_experience.replace("<<DatesPlaceholder>>", experience["dates"])

        if(self._revised_experience is not None):
            revised_experience = list(filter(lambda x: x["company"] == experience["company"], self._revised_experience)).pop()
            print(f"*****\n\n{revised_experience}\n\n*******",flush=True)
        else:
            revised_experience = experience

        job_responsibilities_html = ""
        for responsibility in revised_experience["responsibilities"]:
            job_responsibility_html = str(job_responsibility_html_template)
            job_responsibility_html = job_responsibility_html.replace("<<ResponsibilityPlaceholder>>", responsibility)
            job_responsibilities_html += job_responsibility_html

        job_experience = job_experience.replace("<<ResponsibilitiesPlaceholder>>", job_responsibilities_html)
        return job_experience
    
    def _render_education(self, education, education_html_template):
        education_html = str(education_html_template)
        education_html = education_html.replace("<<DegreePlaceholder>>", f"{education['degree']} - {education['field']}")
        education_html = education_html.replace("<<SchoolPlaceholder>>", education["institution"])
        education_html = education_html.replace("<<LocationPlaceholder>>", education["location"])
        education_html = education_html.replace("<<DatesPlaceholder>>", str(education["dates"]))
        return education_html

    def _render_training(self, education, education_html_template):
        training_html = str(education_html_template)
        training_html = training_html.replace("<<DegreePlaceholder>>", education['course'])
        training_html = training_html.replace("<<SchoolPlaceholder>>", education["provider"])
        training_html = training_html.replace("<<LocationPlaceholder>>", education["location"])
        training_html = training_html.replace("<<DatesPlaceholder>>", str(education["year"]))
        return training_html
    
    def _render_project(self, project, project_html_template):
        project_html = str(project_html_template)
        project_html = project_html.replace("<<NamePlaceholder>>", project["project"])
        project_html = project_html.replace("<<DetailPlaceholder>>", project["description"])
        project_html = project_html.replace("<<DatesPlaceholder>>", str(project["years"]))
        return project_html

