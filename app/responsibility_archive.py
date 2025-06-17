from pydantic import BaseModel
from app.app_paths import AppPaths
import json

MOUNTED_FILES_DIRECTORY = "../mounted_files/"

class Responsibility(BaseModel):
    id: str
    variants: list[str]

    def add_variant(self, variant: str):
        if variant not in self.variants:
            self.variants.append(variant)

class CompanyArchive(BaseModel):
    name: str
    responsibilities: list[Responsibility]

    def get_responsibility_by_id(self, resp_id: str):
        for resp in self.responsibilities:
            if resp.id == resp_id:
                return resp
        raise ValueError(f"Responsibility with id {resp_id} not found.")

    def get_responsibility_variants_by_id(self, resp_id: str):
        resp = self.get_responsibility_by_id(resp_id)
        return resp.variants

    def add_or_update_responsibility(self, resp_id: str, variant: str):
        try:
            resp = self.get_responsibility_by_id(resp_id)
            resp.add_variant(variant)
        except ValueError:
            self.responsibilities.append(Responsibility(id=resp_id, variants=[variant]))

class ResponsibilityArchive:
    def __init__(self, pathfinder: AppPaths):
        self._pathfinder = pathfinder
        self._responsibilities = {}

    def load(self):
        """
        Load the responsibility archive from the mounted files directory.
        """
        file_path = self._pathfinder.get_local_path(MOUNTED_FILES_DIRECTORY, "responsibility_archive.json")
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
                for company in data["companies"]:
                    responsibilities = [Responsibility(**resp) for resp in company["responsibilities"]]
                    self._responsibilities[company["name"]] = CompanyArchive(name=company["name"], responsibilities=responsibilities)
        except FileNotFoundError:
            # If the file does not exist, initialize an empty archive
            self._responsibilities = {}

    def get_responsibility_variants_by_id(self, company_name: str, resp_id: str)-> list[str]:
        if company_name not in self._responsibilities:
            raise ValueError(f"Company {company_name} not found.")
        return self._responsibilities[company_name].get_responsibility_variants_by_id(resp_id)
    
    def get_responsibility_variants_by_company(self, company_name: str)-> dict:
        if company_name not in self._responsibilities:
            raise ValueError(f"Company {company_name} not found.")
        
        return self._responsibilities[company_name].model_dump()["responsibilities"]

    def archive_responsibilities_from_resume(self, resume_json)->None:
        for exp in resume_json.get("experience", []):
            company_name = exp["company"]
            if company_name not in self._responsibilities:
                self._responsibilities[company_name] = CompanyArchive(name=company_name, responsibilities=[])
            company = self._responsibilities[company_name]
            for resp_id, variant in exp.get("responsibilities", {}).items():
                company.add_or_update_responsibility(resp_id, variant)
        return self._responsibilities

    def write(self)-> None:
        """
        Write the responsibility archive to the mounted files directory.
        """
        file_path = self._pathfinder.get_local_path(MOUNTED_FILES_DIRECTORY, "responsibility_archive.json")
        data = {
            "companies": [
                {
                    "name": company.name,
                    "responsibilities": [
                        {"id": resp.id, "variants": resp.variants}
                        for resp in company.responsibilities
                    ]
                }
                for company in self._responsibilities.values()
            ]
        }
        with open(file_path, "w", encoding="utf-8") as file:
            json_str = json.dumps(data, indent=2)
            file.write(json_str)





