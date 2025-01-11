from typing import Tuple
from flask import Flask, request, current_app, send_from_directory
import json
from openai import OpenAI

from app.app_paths import AppPaths
from app.resume_writer import ResumeWriter
#from weasyprint import HTML, CSS

app = Flask(__name__)

description =   '''
                <!DOCTYPE html>
                <head>
                <title>MarkApplied API</title>
                </head>
                <body>  
                    <h3>An API that will generate a resume, maybe?</h3>
                    <a href="http://localhost:5000/api?value=keyword">A simple request that makes sure that a given keyword is included in a resume</a>
                </body>
                '''

@app.route('/', methods=['GET'])
def hello_world():
    return description

@app.route('/api', methods=['GET'])
def generate_resume():
    if not all(k in request.args for k in (["keyword"])):
        error_message =     f"\
                            Required paremeters: 'keyword'<br>\
                            Supplied paremeters: {[k for k in request.args]}\
                            "
        return error_message
    else:
        keyword = request.args.get('keyword', type=str)
        return_value =  f"A resume containing the keyword: {keyword}"
        return json.dumps({"Resume": return_value}) 

@app.route('/create_resume')
def create_resume():
    #TODO: Somehow allow file upload?
    output = ""
    
    
    paths = AppPaths(current_app.root_path)
    with open(paths.get_local_path("chatgpt.token"), 'r') as f:
        api_key = f.read()

    client = OpenAI(api_key=api_key)

    return_tuple = create_assistant(output, client)
    output += return_tuple[0]
    assistant = return_tuple[1]



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

def create_assistant(output, client)->Tuple[str,any]:
    schema =    {
                    "name":"resume_revisions",
                    "description":"Revises the responsibilities sections of resumes to align with job description keywords.",
                    "strict":"true",
                    "schema": {
                        "type": "array",
                        "title":"companies",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "title": "Company Name",
                                    "description": "The name of the job"
                                },
                                "responsibilities": {
                                    "type": "array",
                                    "title": "Responsibilities",
                                    "description": "A list of responsibilities at the company",
                                    "items": {
                                        "type": "string"
                                    }
                                }
                            },
                            "required": ["name", "responsibilities"]
                        }
                    }
                }

    my_assistant = client.beta.assistants.create(
        instructions="You are a career coach and resume writer; you rewrite candidate resumes to make them more attractive to prospective employers and highlight their skills.",
        name="Career Coach",
        tools=[{"type": "file_search"}],
        model="gpt-4o-mini",
        response_format="json_schema"
        json_schema=json_dumps(schema),
    )
    output = str(my_assistant)
    return output, my_assistant

@app.route('/html_resume')
def render_html_resume():
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
        "GxP",
        "21 CFR Part 11",
        "SOC-2 compliance",
        "emerging technology trends",
        "Generative AI",
        "vendor partnerships",
        "technical needs",
        "engineering objectives",
        "senior leadership",
        "engineering organization management",
        "diverse teams",
        "inclusive environments",
        "cloud-native expertise",
        "automation best practices",
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
    
    paths = AppPaths(current_app.root_path)
    with open(paths.get_local_path("chatgpt.token"), 'r') as f:
        api_key = f.read()

    client = OpenAI(api_key=api_key)

    with open(paths.get_local_path("resume.json"), 'r') as j:
        resume_json_str = j.read()

    with open(paths.get_local_path("skills.json"),'r') as j:
        skills_json_str = j.read()

    skills_json = json.loads(skills_json_str)
    resume_json = json.loads(resume_json_str)
    
    for job in skills_json["jobs"]:
        supplied_keywords = job["skills"]

        prompt = f"""
                        You identify which keywords in a Supplied List either match or are similar to those in the Requested List.  An item is a "match" if it would pass a case-insensitive character-by-character match disregarding punctuation (EG: "backend development" and "Back-End Development").  Items are similar if they are commonly used as a synonyms for each other in the software development industry (EG: "relational databases" and "SQL").    Items should also be considered similar if an item on the Supplied List is an example of or a subset of an item on the Requested List (EG: "terraform" on the supplied list should match "infrastructure as code" on the requested list).

                        You should return a json object which shows the relationship between the elements elements in the Requested List and the Supplied List. EG: [{{"claimed":"red", "requested":"scarlet", "relationship":"similar"}}, {{"claimed":"blue","requested":"blue","relationship":"match"}}]

                        Your Requested List is:
                        {job_requested_keywords}

                        "Your Supplied List is 
                        {supplied_keywords}"
                        """
        
        messages = [
                { 
                    "role": "system",
                    "content": 
                        f"""
                        You identify which keywords in a Supplied List either match or are similar to those in the Requested List.  An item is a "match" if it would pass a case-insensitive character-by-character match disregarding punctuation (EG: "backend development" and "Back-End Development").  Items are similar if they are commonly used as a synonyms for each other in the software development industry (EG: "relational databases" and "SQL").    Items should also be considered similar if an item on the Supplied List is an example of or a subset of an item on the Requested List (EG: "terraform" on the supplied list should match "infrastructure as code" on the requested list).

                        You should return a json object which shows the relationship between the elements elements in the Requested List and the Supplied List. EG: [{{"claimed":"red", "requested":"scarlet", "relationship":"similar"}}, {{"claimed":"blue","requested":"blue","relationship":"match"}}]

                        Your requested list is:
                        {job_requested_keywords}
                        """
                },
                {
                    "role": "user",
                    "content": f"Your supplied list is {supplied_keywords}"
                }
            ]

        reply = client.chat.completions.create(model="gpt-4o-mini", messages=messages)

        print(f"ChatGPT says the keyword intersection for {job['name']} looks like {reply.model_dump_json(indent=2)}")

    writer = ResumeWriter(paths, client)
    return writer.write_resume(resume_json)

#@app.route('/pdf_resume')
#def render_pdf_resume():
#    def html_to_pdf(html_content, output_path):
#       HTML(string=html_content).write_pdf(output_path)
#    html = render_html_resume()
#    file_directory = os.path.join(current_app.root_path, "files")
#    output_filename = "test.pdf"
#    os.path.join(file_directory, output_filename)
#    html_to_pdf(output_path)
#    return send_from_directory(file_directory, output_filename, as_attachment=True)
    
if __name__ == "__main__":
    # for debugging locally
	app.run(debug=True, host='0.0.0.0',port=5000)
	
	# for production
	# app.run(host='0.0.0.0', port=5000)
    
    
