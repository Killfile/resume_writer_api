import os
from typing import Tuple
from flask import Flask, request, current_app, send_from_directory, render_template, redirect, url_for
import json
from openai import OpenAI
from pprintpp import pformat as pp


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
def create_resume():
    output = ""
    
    paths = AppPaths(current_app.root_path)
    
    with open(paths.get_local_path("chatgpt.token"), 'r') as f:
        api_key = f.read()

    client = OpenAI(api_key=api_key)

    

    file_object = upload_file_to_openai(paths, client, "resume.json")
    output += "\n" + pp(file_object)

    vector_store = create_vector_store_from_file(client, file_object)
    output += "\n" + pp(vector_store)


    assistant = create_assistant(client, vector_store)
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

def create_vector_store_from_file(client, file_object):
    vector_store = client.beta.vector_stores.create(
        file_ids=[file_object.id],
        name="Resume",
    )
    
    return vector_store

def upload_file_to_openai(paths, client, filename:str):
    local_path = paths.get_local_path(filename)
    size = os.path.getsize(local_path)
    print(f"{local_path} is {size}", flush=True)
    with open(local_path, 'rb') as r:
        
        file_object = client.files.create(
            file = r,
            purpose="assistants"
        )

    return file_object

def create_assistant(client, vector_store)->any:
    schema =    {
                "name": "get_responsibiliets",
                "description": "Rephrases job responsibilites using keywords",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "company": {
                            "type": "string",
                            "description": "The name of the employer"
                        },
                        "responsibility": {
                            "type": "string",
                            "description": "The rephrased job responsibility",
                        }
                    },
                    "additionalProperties": False,
                    "required": ["company", "responsibility"]
                }
                }

    my_assistant = client.beta.assistants.create(
        instructions="You are a career coach and resume writer; you rewrite candidate resumes to make them more attractive to prospective employers and highlight their skills.",
        name="Career Coach",
        tools=[{"type": "file_search"}],
        model="gpt-4o-mini",
        #response_format={"type":"json_schema", "json_schema":schema},
        response_format={"type": "text"},
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
        
    )
    return my_assistant

@app.route('/compute_intersection', methods=['GET', 'POST'])
def compute_intersection():
    skills = get_array_from_arguments(request,"skills")

    overlap, unmatched_skills = get_skills_overlap(skills)

    return render_template("skills_overlap.html", 
                           supplied_skills=pp(skills), 
                           unmatched_skills=pp(unmatched_skills), 
                           overlapping_skills = json.dumps(overlap, indent=4),
                           skills=skills)

def get_skills_overlap(array_data)->Tuple[any, list]:
    lcase_array = [element.lower() for element in array_data if isinstance(element, str)]
    paths = AppPaths(current_app.root_path)
    
    with open(paths.get_local_path("full_skills.json"), 'r') as f:
        json_str = f.read()
    matched_skills = json.loads(json_str.lower())

    all_overlapping_skills = set()

    for company in matched_skills["highlighted experience"]:
        company_intersection = set(company["keywords"]).intersection(set(lcase_array))
        all_overlapping_skills = all_overlapping_skills.union(company_intersection)
        company["keywords"] = list(company_intersection)

    unmatched_skills = list(set(lcase_array).difference(all_overlapping_skills))    
    return matched_skills,unmatched_skills
   
def trim_before_substring(main_string:str, substring:str)->str:
    index = main_string.find(substring)
    if index != -1:
        return main_string[index:]
    return main_string

def trim_after_last_substring(main_string:str, substring)->str:
    index = main_string.rfind(substring)
    if index != -1:
        return main_string[:index + len(substring)]
    return main_string

def extract_json_from_message(message):
    json_end_marker = "```"
    json_start_marker = json_end_marker + "json"
    return_value = trim_before_substring(trim_after_last_substring(message,json_end_marker),json_start_marker)
    return_value = return_value.replace(json_start_marker,"",1)
    return_value = return_value.replace(json_end_marker,"",1)
    return return_value

def get_array_from_arguments(request,key):
    print(f"Rquest method is {request.method}",flush=True)
    return_value = None
    if request.method == 'POST':
        try:
            post_key_value = request.form.get(key)
            print(f"Found value of {post_key_value} for {key} in POST",flush=True)
            post_json_object = json.loads(post_key_value)
            print(f"About to return {pp(post_json_object)} from get_array...",flush=True)
            return_value = post_json_object
        except Exception as e:
            print(f"Something went wrong parsing post json. {e}. Running getlist.", flush=True)
            return_value = request.form.getlist(key)
    else:
        # http://localhost:6969/compute_intersection?skills=[%22AJAX%22,%22CSS%22,%22Agile%22]
        try:
            get_key_value = request.args.get(key)
            print(f"Found value of {get_key_value} for {key} in GET",flush=True)
            get_json_object = json.loads(get_key_value)
            print(f"About to return {pp(get_json_object)} from get_array...",flush=True)
            return_value = get_json_object
        except Exception as e:
            return_value = request.args.getlist(key)
    return return_value

def find_element_in_list_matching_criteria(to_search:list, criteria:callable):
    for item in to_search:
        if criteria(item) == True:
            return item
    return None
    
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
        company_element = find_element_in_list_matching_criteria(skills_json["highlighted experience"],lambda x: x["company"] == company)
        company_element["keywords"].extend(company_skill_array_from_form)
        print(f"Company {company} was assigned these skills: {company_skill_array_from_form}",flush=True)
    
    with(open(paths.get_local_path('full_skills.json'), 'w') as f):
        f.writelines(json.dumps(skills_json))

    return redirect(url_for('compute_intersection', skills=skills))

@app.route('/select_skills', methods=['GET','POST'])
def render_select_skills():
    paths = AppPaths(current_app.root_path)
    skills = get_array_from_arguments(request,"skills")

    overlap, unmatched_skills = get_skills_overlap(skills)
    with(open(paths.get_local_path('full_skills.json'), 'r') as f):
        json_str = f.read()
    skills_json = json.loads(json_str)
    companies = [item["company"] for item in skills_json["highlighted experience"]]
    return render_template('select_skills.html',unmatched_skills=unmatched_skills,companies=companies, skills=json.dumps(skills))
    

@app.route('/resume', methods=['GET', 'POST'])
def render_html_resume():
    paths = AppPaths(current_app.root_path)
    output = ""
    job_requested_keywords = get_array_from_arguments(request,"skills")
    if(job_requested_keywords == ""):
        job_requested_keywords = [
            "engineering strategy",
            "sprint operations",
            "quarterly roadmap",
            "engineering organization",
            "team ownership",
            "team accountability",
            "develop talent",
            "engineering brand",
            "cloud-native infrastructure",
            "automation",
            "infrastructure-as-code",
            "Agile operations",
            "high-quality software",
            "product goals",
            "cross-functional teams",
            "data dashboards",
            "operational analytics",
            "regulated environment",
            "vendor partnerships",
            "technical needs",
            "engineering objectives",
            "senior leadership",
            "engineering organization management",
            "diverse teams",
            "inclusive environments",
            "cloud-native expertise",
            "Agile processes",
            "structured engineering operations",
            "data tools",
            "SQL",
            "strategic planning",
            "HIPAA compliance",
            "collaborative culture",
            "integrating technologies",
            "healthcare data",
            "life sciences data",
            "FHIR",
            "HL7",
            "Data Science team",
            "regulated operations",
            "high-growth startup",
            "Cloud-native environments",
            "Infrastructure as code",
            "Automation",
            "Agile processes",
            "Data tools (SQL)",
            "Generative AI",
            "Engineering operations",
            "Healthcare data experience",
            "Vendor management",
            "Regulated environments experience"
        ]
    
    print(f"Requested: {job_requested_keywords}", flush=True)
    intersection, unmatched_skills = get_skills_overlap(job_requested_keywords)
    print(f"Computed intersection: {pp(intersection)}")
    
    with open(paths.get_local_path("chatgpt.token"), 'r') as f:
        api_key = f.read()

    client = OpenAI(api_key=api_key)
    assistant = client.beta.assistants.retrieve("asst_3Y6QVpOimmPe4952EOXijewl")
    thread = client.beta.threads.create()
    
    message_content = f"""
        Rephrase each of the individual "responsibilities" in each "experience" section of the resume emphasizing 
        the "keywords" provided on a per-company basis below:\n\n

        {json.dumps(intersection)}

        \n\nRephrasing should not change the number of responsibilities listed for each company. You should return a 
        json array with one object per item in the "experience" array. Each object should contain a "company" name, 
        an array of rephrased "responsibilities", an array of used keywords, and an array of unused keywords.
    """
    
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
            print(f"Reply from OpenAI: {message_value}",flush=True)

            if "```json" in message_value:
                output+= "******\n\n"
                try:
                    reply_json = json.loads(extract_json_from_message(message_value))
                    print(f"JSON extracted from reply: {json.dumps(reply_json)}", flush=True)
                except Exception as e:
                    print(f"Error extracting JSON from reply: {e}",flush=True)
    else:
        print(f"Run Status is: {run.status}",flush=True)

    if reply_json is not None:
        with open(paths.get_local_path("resume.json"), 'r') as f:
            resume_json = json.loads(f.read())
        writer = ResumeWriter(paths, reply_json)
        resume_html =  writer.write_resume(resume_json)
        output_filename = "Chris Thomas Resume.pdf"
        file_directory_name = "files"
        output_path = paths.get_local_path(file_directory_name,output_filename)
        file_directory = paths.get_local_path(file_directory_name)
        HTML(string=resume_html).write_pdf(output_path)
        return send_from_directory(file_directory, output_filename, as_attachment=True)

    return render_template("bare_output.html", output=output)

    
if __name__ == "__main__":
    # for debugging locally
	app.run(debug=True, host='0.0.0.0',port=5000)
	
	# for production
	# app.run(host='0.0.0.0', port=5000)
    
    
