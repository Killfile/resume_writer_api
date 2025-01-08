import os
from flask import Flask, request, current_app, send_from_directory
import json
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

def _read_template(filename:str):
    with open(os.path.join(current_app.root_path, "template", filename)) as f:
        contents = f.read()
    return contents

@app.route('/html_resume')
def render_html_resume():

    def render_job_experience(experience, job_html_template, job_responsibility_html_template):
        job_experience = str(job_html_template)
        print(f"Experience: {experience}", flush=True)
        job_experience = job_experience.replace("<<CompanyPlaceholder>>", experience["company"])
        job_experience = job_experience.replace("<<LocationPlaceholder>>", experience["location"])
        job_experience = job_experience.replace("<<TitlePlaceholder>>", experience["position"])
        job_experience = job_experience.replace("<<DatesPlaceholder>>", experience["dates"])

        job_responsibilities_html = ""
        for responsibility in experience["responsibilities"]:
            job_responsibility_html = str(job_responsibility_html_template)
            job_responsibility_html = job_responsibility_html.replace("<<ResponsibilityPlaceholder>>", responsibility)
            job_responsibilities_html += job_responsibility_html

        job_experience = job_experience.replace("<<ResponsibilitiesPlaceholder>>", job_responsibilities_html)
        return job_experience

    file_directory = os.path.join(current_app.root_path, "files")
    output_filename = "test.pdf"
    with open(os.path.join(current_app.root_path, "resume.json"), 'r') as j:
        json_str = j.read()
    resume_json = json.loads(json_str)
    resume_html = _read_template("resume.html")
    job_html_template = _read_template("job.html")
    job_responsibility_html_template = _read_template("job_responsibility.html")

    experience_html = ""
    print("Testing...", flush=True)
    for experience in resume_json["experience"]:
        job_experience = render_job_experience(experience, job_html_template, job_responsibility_html_template)
        experience_html += job_experience
    
    ic_experience_html = ""
    for experience in resume_json["individual_contributor_experience"]:
        job_experience = render_job_experience(experience, job_html_template, job_responsibility_html_template)
        ic_experience_html += job_experience
        
    resume_html = resume_html.replace("<<ExperiencePlaceholder>>",experience_html)
    resume_html = resume_html.replace("<<ICExperiencePlaceholder>>", ic_experience_html)
    return resume_html

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
	# app.run(debug=True, host='0.0.0.0',port=5000)
	
	# for production
	#app.run(host='0.0.0.0', port=5000)
    app.app_context()
    render_html_resume()
