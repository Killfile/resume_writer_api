import os
import re
from typing import Tuple
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

def _create_vector_store_from_file(client, file_object):
    vector_store = client.beta.vector_stores.create(
        file_ids=[file_object.id],
        name="Resume",
    )
    
    return vector_store

def _upload_file_to_openai(paths, client, filename:str):
    local_path = paths.get_local_path(filename)
    size = os.path.getsize(local_path)
    print(f"{local_path} is {size}", flush=True)
    with open(local_path, 'rb') as r:
        
        file_object = client.files.create(
            file = r,
            purpose="assistants"
        )

    return file_object

def _create_assistant(client, vector_store)->any:
    my_assistant = client.beta.assistants.create(
        instructions="You are a career coach and resume writer; you rewrite candidate resumes to make them more attractive to prospective employers and highlight their skills.",
        name="Career Coach",
        tools=[{"type": "file_search"}],
        model="gpt-4o-mini",
        response_format={"type": "text"},
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
        
    )
    return my_assistant

@app.route('/compute_intersection/<company>/<title>', methods=['GET', 'POST'])
def compute_intersection(company:str, title:str):
    skills = _get_array_from_arguments(request,"skills")

    overlap, unmatched_skills = _get_skills_overlap(skills)

    print(f"Compute intersection found these skills: {skills}",flush=True)
    print(f"Compute intersection found these overlaps: {overlap}",flush=True)
    print(f"Compute intersection found these non-overlaps: {unmatched_skills}",flush=True)

    return render_template("skills_overlap.html", 
                           supplied_skills=pp(skills), 
                           unmatched_skills=pp(unmatched_skills), 
                           overlapping_skills = json.dumps(overlap, indent=4),
                           skills=skills,
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

def _rephrase_responsibilities_with_skills(responsibilities_array, skills_array):
    message = f"""
        I am going to provide you with some resume line items. Rephrase them to include the following keywords. Do not add any keyword more than once. Do not add any keyword to more than one line item.\n\n

        {json.dumps(skills_array)}

        Here are the resume line items: \n\n

        {json.dumps(responsibilities_array)}

        \n\nRephrasing should not change the number of responsibilities listed. You should return a 
        json array named "responsibilities" containing the rephrased results. 
    """

    reply_json = _get_json_from_openai_completion(message)
    return reply_json["responsibilities"]


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


def _get_json_from_openai_completion(ai_query, ai_model="gpt-4o-mini"):
    class JobResponsibilities(BaseModel):
        responsibilities: list[str]

    paths = AppPaths(current_app.root_path)
    with open(paths.get_local_path("chatgpt.token"), 'r') as f:
        api_key = f.read()
    
    client = OpenAI(api_key=api_key)
    completion = client.beta.chat.completions.parse(
        model=ai_model,
        response_format = JobResponsibilities,
        messages=[
            {"role": "developer", "content": "You are a resume writer and software career coach who knows how to fine-tune resumes to help land interviews."},
            {"role": "user", "content": ai_query}
        ]
    )

    print(completion.choices[0].message,flush=True)
    return json.loads(completion.choices[0].message.content)

def _get_json_from_openai_assistant(ai_query):
    output = ""
    paths = AppPaths(current_app.root_path)
    with open(paths.get_local_path("chatgpt.token"), 'r') as f:
        api_key = f.read()

    client = OpenAI(api_key=api_key)
    assistant = client.beta.assistants.retrieve("asst_3Y6QVpOimmPe4952EOXijewl")
    thread = client.beta.threads.create()
    
    message_content = ai_query
    
    print(f"Message for OpenAI: {message_content}", flush=True)

    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=message_content)

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions="Rephrase each resume responsibility for the requested company using the provided keywords. The number of responsibilities returned should match the number listed in resume document. Keywords should not be formatted differently than other text."
    )

    reply_json = None
    if run.status == 'completed': 
        messages = client.beta.threads.messages.list(
            thread_id=thread.id
        )
        for index, message in enumerate(messages.data):
            message_value = message.content[0].text.value
            print(f"Reply from OpenAI: {message}",flush=True)

            if message.role == "assistant" and "```json" in message_value:
                try:
                    reply_json = json.loads(_extract_json_from_message(message_value))
                    print(f"*****************JSON extracted from reply: {json.dumps(reply_json)}", flush=True)
                except Exception as e:
                    print(f"Error extracting JSON from reply: {e}",flush=True)
    else:
        print(f"Run Status is: {run.status}",flush=True)

    return reply_json

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
    
    
