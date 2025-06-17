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

@app.route('/initialize_ai')
def initialize_application():
    output = ""
    
    paths = AppPaths(current_app.root_path)
    
    with open(paths.get_local_path("chatgpt.token"), 'r') as f:
        api_key = f.read()

   

    helper = openai_lib.OpenAIHelper(paths)

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
                    reply_json = json.loads(openai_lib._extract_json_from_message(message_value))
                    print(f"*****************JSON extracted from reply: {json.dumps(reply_json)}", flush=True)
                except Exception as e:
                    print(f"Error extracting JSON from reply: {e}",flush=True)
    else:
        print(f"Run Status is: {run.status}",flush=True)

    return reply_json