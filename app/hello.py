import os
import re
from typing import List, Tuple
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

from weasyprint import HTML

app = Flask(__name__)
CORS(app)

FILE_DIRECTORY_NAME = "files"


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



@app.route("/start_resume_by_fetch/", methods=['POST'])
def start_resume_by_fetch():
    resume_number = _do_start_resume()
    return str(resume_number)

@app.route('/start_resume/', methods=['POST'])
def start_resume():
    resume_number = _do_start_resume()

    #print(f"Start Resume wrote this JSON file: {json.dumps(resume_json, indent=4)}")
    print(f"Reached end of start resume", flush=True)
    return redirect(url_for("compute_intersection_by_id", id = resume_number))

def _do_start_resume():
    print(f"start_resume sees request.form as {request.form} and request.args as {request.args.to_dict()}", flush=True)
    if not request.form and not request.args.to_dict():
        request_json = request.get_json()
        company = request_json["company"]
        title = request_json["title"]
        skills = request_json["skills"]
        job_description = request_json["job_description"]
    else:
        company = request.form.get("company")
        title = request.form.get("title")
        skills = get_array_from_arguments(request,"skills")
        job_description = skills
        
    paths = AppPaths(current_app.root_path)
    resume_number, source, dest = _find_safe_resume_number(paths, "resume.json")
   
   

    print(f"Start Resume was called for company: {company} and title: {title} and passed these skills: {skills}",flush=True)

    with(open(source,'r') as f):
        resume_str = f.read()
    resume_json = json.loads(resume_str)
    resume_json["company_name"] = company
    resume_json["title_name"] = title
    resume_json["skills"] = skills
    resume_json["job_description"] = job_description

    with(open(dest,'w') as f):
        f.write(json.dumps(resume_json))
    return resume_number
   

@app.route('/compute_intersection/<id>', methods=['GET'])
def compute_intersection_by_id(id:int):
    print("Hit compute_intersection_by_id", flush=True)
    resume_json = _get_resume_json_by_id(id)
    supplied_skills = resume_json["skills"]
    company = resume_json["company_name"]
    title = resume_json["title_name"]

    overlap, unmatched_skills = _get_skills_overlap(supplied_skills)

    return render_template("skills_overlap_by_id.html", 
                           id=id,
                           supplied_skills=pp(supplied_skills), 
                           unmatched_skills=pp(unmatched_skills), 
                           overlapping_skills = json.dumps(overlap, indent=4),
                           skills=json.dumps(supplied_skills),
                           company=company,
                           title=title)





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

@app.route('/create_new_resume/<id>')
def do_create_new_resume_by_id(id:id):
    resume_json = _get_resume_json_by_id(id)
    skills = resume_json["skills"]
    overlap, unmatched_skills = _get_skills_overlap(skills)



    for exp_company in resume_json["experience"]:
        company_element = _find_element_in_list_matching_criteria(overlap["highlighted experience"], lambda x: x["company"] == exp_company["company"].lower())
        exp_company["skills"] = company_element["keywords"]

    for exp_company in resume_json["individual_contributor_experience"]:
        company_element = _find_element_in_list_matching_criteria(overlap["highlighted experience"], lambda x: x["company"] == exp_company["company"].lower())
        exp_company["skills"] = company_element["keywords"]

    _write_resume_json_by_id(resume_json, id)
    return redirect("http://localhost:3000/"+str(id))
    




@app.route('/build_resume/<resume_id>', methods=['GET'])
def render_build_resume(resume_id):
    resume_json = _get_resume_json_by_id(resume_id)
    print(f"Render Build Resume found this JSON resume: {json.dumps(resume_json, indent=4)}", flush=True)
    for e, experience in enumerate(resume_json["experience"]):
        skills = experience["skills"]
        for skill in experience["skills"]:
            pattern = r"("+skill+r")"
            replacement = r'<span class="highlight">\1</span>'
            # r.replace(skill,f"<span class=\"highlight\">{skill}</span>")
            resume_json["experience"][e]["responsibilities"][:] = [re.sub(pattern,replacement,r, flags=re.IGNORECASE) for r in resume_json["experience"][e]["responsibilities"]]

    print(f"Render Build Resume found this JSON resume after replacement: {json.dumps(resume_json, indent=4)}", flush=True)
    
    return render_template("build_resume.html", resume_id=resume_id, resume=resume_json)

def _rephrase_responsibilities_with_skills(responsibilities_array, skills_array, custom_instructions=None):
    context_data = {
        "keywords": skills_array,
        "resume line items": responsibilities_array
    }
    instructions = """
        I am going to provide you with some resume line items. Rephrase them to include the supplied keywords. 
        Do not add any keyword more than once. Do not add any keyword to more than one line item. 
        Do not replace keywords that are already in a line item with other keywords.
    """

    if custom_instructions is not None:
        instructions = custom_instructions    

    message = f"""
        {instructions}
        Rephrasing should not change the number of line items. 
        You should return a json array named "responsibilities" containing the rephrased results. \n\n

        {json.dumps(context_data)}
    """
    class JobResponsibilities(BaseModel):
        responsibilities: list[str]
    reply_json = _get_json_from_openai_completion(message, JobResponsibilities)
    return reply_json["responsibilities"]

def _generate_summary_from_skills_and_description(skills_array, job_description, experience, custom_instructions=None):

    context_data = {
        "skills": skills_array,
        "previous_experience": experience,
        "job_description": job_description,
        }

    instructions = """
        Here is a job description I'm interested in. 
        Please craft a concise professional summary that highlights my expertise while aligning with the role's responsibilities and qualifications. 
        Incorporate leadership experience, technical skills, and any industry-specific nuances as needed. 
        
        Tone and style: All sentences should be structured as if they start with 'I am' or 'I am a' but should not actually include those words.
    """

    if custom_instructions is not None:
        instructions = custom_instructions   

    #   You should return a json object with an element named "summary" which contains the result.

    message = f"""
        {instructions}


        {json.dumps(context_data)}
    """
    class ResumeSummary(BaseModel):
        summary: str
        additional_suggestions: List[str]

    reply_json = _get_json_from_openai_completion(message, ResumeSummary)
    return reply_json

@app.route('/rate_resume/<id>', methods=['GET'])
def do_rate_resume(id):
    def remove_key_recursive(data, key_to_remove):
        if isinstance(data, dict):
            return {k: remove_key_recursive(v, key_to_remove) for k, v in data.items() if k != key_to_remove}
        elif isinstance(data, list):
            return [remove_key_recursive(item, key_to_remove) for item in data]
        else:
            return data

    resume_json = remove_key_recursive(_get_resume_json_by_id(id), "skills")
    message = f"""
        The included JSON represents a resume to be submitted to a job ad.  
        The company, title, and job description for the job ad are represented by the company_name, title_name, and job_description fields.
        The rest of the JSON file represents the applicant resume.
        <first> Evaluate the job description; identify the 3 most important hard and soft skills, and the most relevant experience from the resume.
        <second> Evaluate how well the resume matches the job description along three dimentions, each of which will be scored on a scale of 0-100:
        1. Leadership Experience and Seniority
        2. Technical Skills and Industry Experience
        3. Soft Skills 

        Your explanation of the score should ONLY note how the resume can be improved and include specific suggestions for improvement; it should not discuss the resume's strengths.
        {resume_json}
    """

    class JobDescriptionAssessment(BaseModel):
        most_important_hard_skills: List[str]
        most_important_soft_skills: List[str]
        most_relevant_experience: List[str]

    class ScoreComponents(BaseModel):
        leadership_experience: int
        technical_skills: int
        soft_skills: int

    class ResumeGrade(BaseModel):
        job_description_assessment: JobDescriptionAssessment
        score_components: ScoreComponents
        explanation: List[str]

    reply_json = _get_json_from_openai_completion(message, ResumeGrade, temperature=0.0)
    return reply_json

@app.route('/rephrase_summary/<id>', methods=['POST'])
def do_rephrase_summary(id):
    request_json = request.get_json()
    custom_instructions = request_json.get("custom_instructions")

    resume_json = _get_resume_json_by_id(id)
    job_description = resume_json["job_description"]
    skills = resume_json["skills"]
    experience = resume_json["experience"]
    description = _generate_summary_from_skills_and_description(skills, job_description, experience, custom_instructions)
    resume_json["summary"]["description"] = description
    _write_resume_json_by_id(resume_json,id)
    
    return jsonify(description)

@app.route('/rephrase_responsibilities', methods=['POST'])
def de_rephrase_responsibilities_with_skills():
    request_json = request.get_json()
    skills = request_json["skills"]
    responsibilities = request_json["responsibilities"]
    
    rephrased = _rephrase_responsibilities_with_skills(responsibilities, skills)
    return jsonify(rephrased)

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


def _get_json_from_openai_completion(ai_query, response_format, ai_model="gpt-4o-mini", temperature=0.8):
    

    paths = AppPaths(current_app.root_path)
    with open(paths.get_local_path("chatgpt.token"), 'r') as f:
        api_key = f.read()
    
    client = OpenAI(api_key=api_key)
    completion = client.beta.chat.completions.parse(
        model=ai_model,
        response_format = response_format,
        messages=[
            {"role": "developer", "content": "You are a resume writer and software career coach specialized in the software development industry who knows how to fine-tune resumes to help land interviews."},
            {"role": "user", "content": ai_query}
        ],
        temperature=temperature
    )

    print(completion.choices[0].message,flush=True)
    return json.loads(completion.choices[0].message.content)



@app.route('/resume/render_as_pdf/<id>', methods=['GET'])
def render_json_resume_as_pdf(id):
    paths = AppPaths(current_app.root_path)
    
    resume_json = _get_resume_json_by_id(id)
    company = resume_json["company_name"]
    title = resume_json["title_name"]
    writer = ResumeWriter(paths,None)
    resume_html =  writer.write_resume(resume_json)
    output_filename = f"Chris Thomas-{title}-{company}.pdf"
    output_path = paths.get_local_path(FILE_DIRECTORY_NAME,output_filename)
    file_directory = paths.get_local_path(FILE_DIRECTORY_NAME)
    HTML(string=resume_html).write_pdf(output_path)
    return send_from_directory(file_directory, output_filename, as_attachment=True)

@app.route('/resume/read/<id>', methods=['GET'])
def resume_read(id):
    resume_str = _get_resume_str_by_id(id)
    return jsonify(json.loads(resume_str))

@app.route("/resume/write/<id>", methods=['POST'])
def resume_write(id):
    resume_json = request.get_json()
    print(f"Json extracted from request: {resume_json}")
    paths = AppPaths(current_app.root_path)
    


    with(open(paths.get_local_path(FILE_DIRECTORY_NAME,f"resume_{id}.json"), 'w') as f):
        f.write(json.dumps(resume_json))
    
    return jsonify(resume_json)


    

    
if __name__ == "__main__":
    # for debugging locally
	app.run(debug=True, host='0.0.0.0',port=5000)
	
	# for production
	# app.run(host='0.0.0.0', port=5000)
    
    
