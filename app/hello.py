import os
from typing import Tuple
from app.openai_lib import OpenAIHelper
from app.array_lib import _find_element_in_list_matching_criteria, get_array_from_arguments
from flask import Flask, request, current_app, send_from_directory, render_template, redirect, url_for
import json
from openai import OpenAI
from pprintpp import pformat as pp
import shutil


from app.app_paths import AppPaths
from app.resume_writer import ResumeWriter
from weasyprint import HTML, CSS

app = Flask(__name__)

description =   '''
                <!DOCTYPE html>
                <head>
                <title>MarkApplied API</title>
                </head>
                <body>  
                    <h2>Diagnostics</h2>
                    <h3>Compute Intersection</h3>
                    <p><a href="http://localhost:5000/compute_intersection?skills=[%22Agile%22,%22DevOps%22]">Compute the intersection</a> between the stored skill-list and a supplied skill-list</p>
                    <h2>AI Operations</h2>
                    <p>The following operations are supported for interacting with the AI:
                    <h3>Initialization...</h3>
                    <a href="http://localhost:5000/initialize_ai">We need a one-time setup to get the AI initialized.</a>
                    <h3>Generate a resume</h3>
                    <a href="http://localhost:5000/resume?skills=[%22Agile%22,%22DevOps%22]">Generate a resume from a list of keywords</a>
                </body>
                '''

@app.route('/', methods=['GET'])
def api_descrpition():
    # return a html format string that is rendered in the browser
	return description

@app.route('/initialize_ai')
def initialize_application():
    output = ""
    
    paths = AppPaths(current_app.root_path)
    
    with open(paths.get_local_path("chatgpt.token"), 'r') as f:
        api_key = f.read()

   

    helper = OpenAIHelper(paths)

    file_object = helper._upload_file_to_openai(paths, "resume.json")
    output += "\n" + pp(file_object)

    vector_store = helper._create_vector_store_from_file(file_object)
    output += "\n" + pp(vector_store)

    assistant = helper._create_assistant(vector_store)
    output += "\n" + pp(assistant)

    return_value =  f'''
                    <!DOCTYPE html>
                    <head>
                    <title>MarkApplied API</title>
                    </head>
                    <body>  
                        <h3>Output...</h3>
                        <pre>{output}</pre>
                    </body>
                    '''
    return return_value

@app.route('/compute_intersection', methods=['GET', 'POST'])
def compute_intersection():
    skills = get_array_from_arguments(request,"skills")

    overlap, unmatched_skills = _get_skills_overlap(skills)

    print(f"Compute intersection found these skills: {skills}",flush=True)
    print(f"Compute intersection found these overlaps: {overlap}",flush=True)
    print(f"Compute intersection found these non-overlaps: {unmatched_skills}",flush=True)

    return render_template("skills_overlap.html", 
                           supplied_skills=pp(skills), 
                           unmatched_skills=pp(unmatched_skills), 
                           overlapping_skills = json.dumps(overlap, indent=4),
                           skills=skills)

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

@app.route('/create_new_resume')
def do_create_new_resume():
    paths = AppPaths(current_app.root_path)
    resume_number, source, dest = _find_safe_resume_number(paths, "resume.json")
   
    skills = get_array_from_arguments(request,"skills")

    print(f"Do Create Resume was passed these skills: {skills}")

    overlap, unmatched_skills = _get_skills_overlap(skills)

    print(f"Do Create Resume found this overlap: {overlap}")
    print(f"Do Create Resume found these unmatched: {unmatched_skills}")

    with(open(source,'r') as f):
        resume_str = f.read()
    resume_json = json.loads(resume_str)
    for company in resume_json["experience"]:
        company_element = _find_element_in_list_matching_criteria(overlap["highlighted experience"], lambda x: x["company"] == company["company"].lower())
        company["skills"] = company_element["keywords"]

    for company in resume_json["individual_contributor_experience"]:
        company_element = _find_element_in_list_matching_criteria(overlap["highlighted experience"], lambda x: x["company"] == company["company"].lower())
        company["skills"] = company_element["keywords"]

    with(open(dest,'w') as f):
        f.write(json.dumps(resume_json))

    print(f"Create Resume wrote this JSON file: {json.dumps(resume_json, indent=4)}")
    return redirect(url_for("render_build_resume", resume_id = resume_number))



@app.route('/build_resume/<resume_id>', methods=['GET'])
def render_build_resume(resume_id):
    paths = AppPaths(current_app.root_path)
    with(open(paths.get_local_path("files", f"resume_{resume_id}.json"),'r') as r):
        resume_str = r.read()

    resume_json = json.loads(resume_str)
    print(f"Render Build Resume found this JSON resume: {json.dumps(resume_json, indent=4)}", flush=True)
    for e, experience in enumerate(resume_json["experience"]):
        skills = experience["skills"]
        for skill in experience["skills"]:
            resume_json["experience"][e]["responsibilities"][:] = [r.replace(skill,f"<span class=\"highlight\">{skill}</span>") for r in resume_json["experience"][e]["responsibilities"]]

    print(f"Render Build Resume found this JSON resume after replacement: {json.dumps(resume_json, indent=4)}", flush=True)
    
    return render_template("build_resume.html", resume_id=resume_id, resume=resume_json)

@app.route('/rephrase_company/<id>/<name>', methods=['GET'])
def do_rephrase_single_company(id, name):
    paths = AppPaths(current_app.root_path)
    helper = OpenAIHelper(paths)

    with(open(paths.get_local_path("resume.json"),'r') as f):
        json_str = f.read()
    original_resume_json = json.loads(json_str)
    original_experience_record = _find_element_in_list_matching_criteria(original_resume_json["experience"], lambda x:x["company"].lower()==name.lower())
    if original_experience_record is None:
        original_experience_record = _find_element_in_list_matching_criteria(original_resume_json["individual_contributor_experience"], lambda x:x["company"].lower()==name.lower())

    with(open(paths.get_local_path("files",f"resume_{id}.json"), 'r') as f):
        json_str = f.read()
    resume_json = json.loads(json_str)
    experience_record = _find_element_in_list_matching_criteria(resume_json["experience"], lambda x:x["company"].lower()==name.lower())
    if experience_record is None:
        experience_record = _find_element_in_list_matching_criteria(resume_json["individual_contributor_experience"], lambda x:x["company"].lower()==name.lower())

    

    message = f"""
        I am going to provide you with some resume line items. Rephrase them to include the following keywords without changing the meaning of sentence.\n\n

        {json.dumps(experience_record["skills"])}

        Here are the resume line items: \n\n

        {json.dumps(original_experience_record["responsibilities"])}

        \n\nRephrasing should not change the number of responsibilities listed. You should return a 
        json array named "responsibilities" containing the rephrased results. 
    """

    reply_json = helper.send_message_to_openai(message)

    experience_record["responsibilities"] = reply_json["responsibilities"]
    with(open(paths.get_local_path("files",f"resume_{id}.json"), 'w') as f):
        f.write(json.dumps(resume_json))
    
    return redirect(url_for("render_build_resume", resume_id = id))

@app.route('/map_skills', methods=['POST'])
def do_map_skills():
    paths = AppPaths(current_app.root_path)
    skills = get_array_from_arguments(request,"skills")
    with(open(paths.get_local_path('full_skills.json'), 'r') as f):
        json_str = f.read()
    skills_json = json.loads(json_str)
    companies = [item["company"] for item in skills_json["highlighted experience"]]
    for company in companies:
        company_skill_array_from_form = request.form.getlist(company)
        company_element = _find_element_in_list_matching_criteria(skills_json["highlighted experience"],lambda x: x["company"] == company)
        company_element["keywords"].extend(company_skill_array_from_form)
        print(f"Company {company} was assigned these skills: {company_skill_array_from_form}",flush=True)
    
    with(open(paths.get_local_path('full_skills.json'), 'w') as f):
        f.writelines(json.dumps(skills_json))

    return redirect(url_for('compute_intersection', skills=skills))

@app.route('/select_skills', methods=['GET','POST'])
def render_select_skills():
    paths = AppPaths(current_app.root_path)
    skills = get_array_from_arguments(request,"skills")

    overlap, unmatched_skills = _get_skills_overlap(skills)
    with(open(paths.get_local_path('full_skills.json'), 'r') as f):
        json_str = f.read()
    skills_json = json.loads(json_str)
    companies = [item["company"] for item in skills_json["highlighted experience"]]
    return render_template('select_skills.html',unmatched_skills=unmatched_skills,companies=companies, skills=json.dumps(skills))


@app.route('/resume/<id>', methods=['GET'])
def render_json_resume_as_pdf(id):
    paths = AppPaths(current_app.root_path)
    file_directory_name = "files"

    with(open(paths.get_local_path(file_directory_name, f"resume_{id}.json"),'r') as r):
        resume_str = r.read()

    resume_json = json.loads(resume_str)
    writer = ResumeWriter(paths,None)
    resume_html =  writer.write_resume(resume_json)
    output_filename = "Chris Thomas Resume.pdf"
    output_path = paths.get_local_path(file_directory_name,output_filename)
    file_directory = paths.get_local_path(file_directory_name)
    HTML(string=resume_html).write_pdf(output_path)
    return send_from_directory(file_directory, output_filename, as_attachment=True)


@app.route('/resume', methods=['GET', 'POST'])
def render_html_resume():
    paths = AppPaths(current_app.root_path)
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

    helper = OpenAIHelper(paths)
    
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
    

    
if __name__ == "__main__":
    # for debugging locally
	app.run(debug=True, host='0.0.0.0',port=5000)
	
	# for production
	# app.run(host='0.0.0.0', port=5000)
    
    
