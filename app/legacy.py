import os
import re
from typing import Tuple
from app import openai_lib
from app.array_lib import _find_element_in_list_matching_criteria, get_array_from_arguments
from flask import Flask, request, current_app, send_from_directory, render_template, redirect, url_for, jsonify
import json
from openai import OpenAI
from pprintpp import pformat as pp
import shutil
from pydantic import BaseModel
from flask_cors import CORS

from app.app_paths import AppPaths
from app.resume_writer import ResumeWriter

from weasyprint import HTML, CSS

@app.route('/compute_intersection/<company>/<title>', methods=['GET', 'POST'])
def compute_intersection(company:str, title:str):
    skills = get_array_from_arguments(request,"skills")

    overlap, unmatched_skills = _get_skills_overlap(skills)

    print(f"Compute intersection found these skills: {skills}",flush=True)
    print(f"Compute intersection found these overlaps: {overlap}",flush=True)
    print(f"Compute intersection found these non-overlaps: {unmatched_skills}",flush=True)

    return render_template("skills_overlap.html", 
                           supplied_skills=pp(skills), 
                           unmatched_skills=pp(unmatched_skills), 
                           overlapping_skills = json.dumps(overlap, indent=4),
                           skills=json.dumps(skills),
                           company=company,
                           title=title)


@app.route('/create_new_resume/<company>/<title>')
def do_create_new_resume(company:str,title:str):
    paths = AppPaths(current_app.root_path)
    resume_number, source, dest = _find_safe_resume_number(paths, "resume.json")
   
    skills = get_array_from_arguments(request,"skills")

    print(f"Do Create Resume was called for company: {company} and title: {title} and passed these skills: {skills}")

    overlap, unmatched_skills = _get_skills_overlap(skills)

    print(f"Do Create Resume found this overlap: {overlap}")
    print(f"Do Create Resume found these unmatched: {unmatched_skills}")

    with(open(source,'r') as f):
        resume_str = f.read()
    resume_json = json.loads(resume_str)
    resume_json["company_name"] = company
    resume_json["title_name"] = title
    for exp_company in resume_json["experience"]:
        company_element = _find_element_in_list_matching_criteria(overlap["highlighted experience"], lambda x: x["company"] == exp_company["company"].lower())
        exp_company["skills"] = company_element["keywords"]

    for exp_company in resume_json["individual_contributor_experience"]:
        company_element = _find_element_in_list_matching_criteria(overlap["highlighted experience"], lambda x: x["company"] == exp_company["company"].lower())
        exp_company["skills"] = company_element["keywords"]

    with(open(dest,'w') as f):
        f.write(json.dumps(resume_json))

    print(f"Create Resume wrote this JSON file: {json.dumps(resume_json, indent=4)}")
    return redirect("http://localhost:3000/"+str(resume_number))

@app.route('/rephrase_company/<id>/<name>', methods=['GET'])
def do_rephrase_single_company(id, name):
    paths = AppPaths(current_app.root_path)
    original_resume_json = _get_originial_resume_json()
    original_experience_record = _find_element_in_list_matching_criteria(original_resume_json["experience"], lambda x:x["company"].lower()==name.lower())
    if original_experience_record is None:
        original_experience_record = _find_element_in_list_matching_criteria(original_resume_json["individual_contributor_experience"], lambda x:x["company"].lower()==name.lower())

    resume_json = _get_resume_json_by_id(id)
    experience_record = _get_experience_record_for_company(name, resume_json)

    skills = experience_record["skills"]
    responsibilties = original_experience_record["responsibilities"]
    rephrased = _rephrase_responsibilities_with_skills(responsibilties, skills)

    experience_record["responsibilities"] = rephrased
    with(open(paths.get_local_path("files",f"resume_{id}.json"), 'w') as f):
        f.write(json.dumps(resume_json))
    
    return redirect(url_for("render_build_resume", resume_id = id))

@app.route('/resume', methods=['GET', 'POST'])
def render_html_resume():
    paths = AppPaths(current_app.root_path)
    
    resume_number, source, dest = _find_safe_resume_number(paths, "resume.json")
   
    output = ""
    job_requested_keywords = get_array_from_arguments(request,"skills")
    
    print(f"Requested: {job_requested_keywords}", flush=True)
    intersection, unmatched_skills = _get_skills_overlap(job_requested_keywords)
    print(f"Computed intersection: {pp(intersection)}")

    message_content = f"""
        Rephrase each of the individual "responsibilities" in each "experience" section of the resume emphasizing 
        the "keywords" provided on a per-company basis below:\n\n

        {json.dumps(intersection)}

        \n\nRephrasing should not change the number of responsibilities listed for each company. You should return a 
        json array with one object per item in the "experience" array. Each object should contain a "company" name, 
        an array of rephrased "responsibilities", an array of used keywords, and an array of unused keywords.
    """

    helper = openai_lib.OpenAIHelper(paths)
    
    reply_json = helper.send_message_to_openai_assistant(message_content)

    skills = get_array_from_arguments(request,"skills")

    overlap, unmatched_skills = _get_skills_overlap(skills)

    with(open(dest,'r') as f):
        resume_str = f.read()
    resume_json = json.loads(resume_str)
    
    for company in resume_json["experience"]:
        company_element = _find_element_in_list_matching_criteria(overlap["highlighted experience"], lambda x: x["company"] == company["company"].lower())
        company["skills"] = company_element["keywords"]

    for company in resume_json["individual_contributor_experience"]:
        company_element = _find_element_in_list_matching_criteria(overlap["highlighted experience"], lambda x: x["company"] == company["company"].lower())
        company["skills"] = company_element["keywords"]


    if reply_json is not None:
        for experience in resume_json["experience"]:
            experience["responsibilities"] = _find_element_in_list_matching_criteria(reply_json,lambda x:x["company"] == experience["company"])["responsibilities"]
        for experience in resume_json["individual_contributor_experience"]:
            experience["responsibilities"] = _find_element_in_list_matching_criteria(reply_json,lambda x:x["company"] == experience["company"])["responsibilities"]
        
        with open(dest,'w') as f:
            f.write(json.dumps(resume_json))
    
    return redirect(url_for("render_build_resume", resume_id = resume_number))


def _get_originial_resume_json():
    paths = AppPaths(current_app.root_path)
    with(open(paths.get_local_path("resume.json"),'r') as f):
        json_str = f.read()
    original_resume_json = json.loads(json_str)
    return original_resume_json

def _get_experience_record_for_company(company_name, resume_json):
    experience_record = _find_element_in_list_matching_criteria(resume_json["experience"], lambda x:x["company"].lower()==company_name.lower())
    if experience_record is None:
        experience_record = _find_element_in_list_matching_criteria(resume_json["individual_contributor_experience"], lambda x:x["company"].lower()==company_name.lower())
    return experience_record

def _get_skills_overlap(array_data)->Tuple[any, list]:
    lcase_array = [element.lower() for element in array_data if isinstance(element, str)]
    paths = AppPaths(current_app.root_path)
    
    with open(paths.get_local_path("full_skills.json"), 'r') as f:
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

def _find_safe_resume_number(paths: AppPaths, filename:str):
    resume_number = 1
    while os.path.exists(paths.get_local_path("files",f"resume_{resume_number}.json")) == True:
        resume_number += 1
    
    parts = filename.split(".")

    source = paths.get_local_path(filename)
    dest = paths.get_local_path("files",f"{parts[0]}_{resume_number}.{parts[1]}")
    shutil.copyfile(source,dest)
    return resume_number, source, dest

def _rephrase_responsibilities_with_skills(responsibilities_array, skills_array):
    message = f"""
        I am going to provide you with some resume line items. Rephrase them to include the following keywords. Do not add any keyword more than once. Do not add any keyword to more than one line item. Do not replace keywords that are already in a line item with other keywords.\n\n

        {json.dumps(skills_array)}

        Here are the resume line items: \n\n

        {json.dumps(responsibilities_array)}

        \n\nRephrasing should not change the number of line items. You should return a json array named "responsibilities" containing the rephrased results. 
    """
    class JobResponsibilities(BaseModel):
        responsibilities: list[str]
    reply_json = _get_json_from_openai_completion(message, JobResponsibilities)
    return reply_json["responsibilities"]

def _get_json_from_openai_completion(ai_query, response_format, ai_model="gpt-4o-mini"):
    

    paths = AppPaths(current_app.root_path)
    with open(paths.get_local_path("chatgpt.token"), 'r') as f:
        api_key = f.read()
    
    client = OpenAI(api_key=api_key)
    completion = client.beta.chat.completions.parse(
        model=ai_model,
        response_format = response_format,
        messages=[
            {"role": "developer", "content": "You are a resume writer and software career coach who knows how to fine-tune resumes to help land interviews."},
            {"role": "user", "content": ai_query}
        ]
    )

    print(completion.choices[0].message,flush=True)
    return json.loads(completion.choices[0].message.content)

def _get_resume_json_by_id(id):
    json_str = _get_resume_str_by_id(id)
    json_resume = json.loads(json_str)
    return json_resume

def _write_resume_json_by_id(resume_json, id:int):
    paths = AppPaths(current_app.root_path)
    with(open(paths.get_local_path("files",f"resume_{id}.json"), 'w') as f):
        f.write(json.dumps(resume_json))

def _get_resume_str_by_id(id):
    paths = AppPaths(current_app.root_path)
    with(open(paths.get_local_path("files",f"resume_{id}.json"), 'r') as f):
        json_str = f.read()
    return json_str