class SkillMatcher:
    def __init__(self, app_paths: AppPaths):
        self._paths = app_paths

    def get_overlap(self, supplied_skills)->Tuple[any, list]:
        lcase_array = [element.lower() for element in supplied_skills if isinstance(element, str)]
        
        
        with open(self._paths.get_local_path("../mounted_files/full_skills.json"), 'r') as f:
            json_str = f.read()
        matched_skills = json.loads(json_str.lower())

        all_overlapping_skills = set()

        provided_keywords_lcase_set = set(lcase_array)
        print(f"To match: {provided_keywords_lcase_set}", flush=True)
        for company in matched_skills["highlighted experience"]:
            company_keywords_set = set(company["keywords"])
            
            company_intersection = company_keywords_set.intersection(provided_keywords_lcase_set)
            print(f"Company: {company["company"]}\n\nCompany Keywords:{company_keywords_set}\n\nIntersection: {company_intersection}")
            all_overlapping_skills = all_overlapping_skills.union(company_intersection)
            company["keywords"] = list(company_intersection)

        unmatched_skills = list(set(lcase_array).difference(all_overlapping_skills))    
        return matched_skills,unmatched_skills