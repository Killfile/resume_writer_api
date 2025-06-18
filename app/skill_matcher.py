import json
from typing import Tuple

from app.app_paths import AppPaths


class SkillMatcher:
    def __init__(self, app_paths: AppPaths):
        self._paths = app_paths

    def get_overlap(self, skills_sought_in_job)->Tuple[any, list]:
        working_copy_of_skills_library = self._get_skills_from_library()
        unique_skills_sought_in_job = self._get_unique_skills_sought_in_job(skills_sought_in_job)

        undifferentiated_list_of_intersecting_skills = set()

        for skills_from_company in working_copy_of_skills_library["highlighted experience"]:
            unique_skills_from_company_set = set(skills_from_company["keywords"])
            intersection_of_unique_skills_from_job_and_company = unique_skills_from_company_set.intersection(unique_skills_sought_in_job)
            undifferentiated_list_of_intersecting_skills = undifferentiated_list_of_intersecting_skills.union(intersection_of_unique_skills_from_job_and_company)
            skills_from_company["keywords"] = list(intersection_of_unique_skills_from_job_and_company)

        unmatched_skills = list(unique_skills_sought_in_job.difference(undifferentiated_list_of_intersecting_skills))    
        return working_copy_of_skills_library, unmatched_skills

    def _get_unique_skills_sought_in_job(self, skills_sought_in_job):
        lcase_array = [element.lower() for element in skills_sought_in_job if isinstance(element, str)]
        unique_skills_sought_in_job = set(lcase_array)
        return unique_skills_sought_in_job

    def _get_skills_from_library(self):
        with open(self._paths.get_local_path("../mounted_files/full_skills.json"), 'r') as f:
            json_str = f.read()
        skills_library = json.loads(json_str.lower())
        return skills_library