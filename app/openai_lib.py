import json
import os
from app.app_paths import AppPaths
from app.string_lib import _trim_after_last_substring, trim_before_substring
from openai import OpenAI
from pydantic import BaseModel

class OpenAIHelper:
    def __init__(self, app_paths):
        self._app_paths = app_paths
        with open(self._app_paths.get_local_path("chatgpt.token"), 'r') as f:
            self._api_key = f.read()
        self._client = OpenAI(api_key=self._api_key)
        
        
    def _create_assistant(self, vector_store)->any:
        my_assistant = self._client.beta.assistants.create(
            instructions="You are a career coach and resume writer; you rewrite candidate resumes to make them more attractive to prospective employers and highlight their skills.",
            name="Career Coach",
            tools=[{"type": "file_search"}],
            model="gpt-4o-mini",
            response_format={"type": "text"},
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},

        )
        return my_assistant


    def _extract_json_from_message(self, message):
        json_end_marker = "```"
        json_start_marker = json_end_marker + "json"
        return_value = trim_before_substring(_trim_after_last_substring(message,json_end_marker),json_start_marker)
        return_value = return_value.replace(json_start_marker,"",1)
        return_value = return_value.replace(json_end_marker,"",1)
        return return_value

    def send_message_to_openai_assistant(self, message):
        assistant = self._client.beta.assistants.retrieve("asst_3Y6QVpOimmPe4952EOXijewl")
        thread = self._client.beta.threads.create()
        
        print(f"Message for OpenAI: {message}", flush=True)

        message = self._client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=message)

        run = self._client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id,
            instructions="Rephrase each resume responsibility for the requested company using the provided keywords. The number of responsibilities returned should match the number listed in resume document. Keywords should not be formatted differently than other text."
        )

        reply_json = None
        if run.status == 'completed': 
            messages = self._client.beta.threads.messages.list(
                thread_id=thread.id
            )
            for index, message in enumerate(messages.data):
                message_value = message.content[0].text.value
                print(f"Reply from OpenAI: {message_value}",flush=True)

                if "```json" in message_value:
                    output+= "******\n\n"
                    try:
                        reply_json = json.loads(self._extract_json_from_message(message_value))
                        print(f"JSON extracted from reply: {json.dumps(reply_json)}", flush=True)
                        return reply_json
                    except Exception as e:
                        print(f"Error extracting JSON from reply: {e}",flush=True)
                        return None
        else:
            print(f"Run Status is: {run.status}",flush=True)
            return None


    def send_message_to_openai(self, ai_query)->dict:
        class JobResponsibilities(BaseModel):
            responsibilities: list[str]
  
        completion = self._client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            response_format = JobResponsibilities,
            messages=[
                {"role": "developer", "content": "You are a resume writer and software career coach who knows how to fine-tune resumes to help land interviews."},
                {"role": "user", "content": ai_query}
            ]
        )

        print(completion.choices[0].message,flush=True)
        return json.loads(completion.choices[0].message.content)


    def _get_json_from_openai_assistant(self, ai_query):
        output = ""
        paths = self._paths
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
                        reply_json = json.loads(self._extract_json_from_message(message_value))
                        print(f"*****************JSON extracted from reply: {json.dumps(reply_json)}", flush=True)
                    except Exception as e:
                        print(f"Error extracting JSON from reply: {e}",flush=True)
        else:
            print(f"Run Status is: {run.status}",flush=True)

        return reply_json


def _upload_file_to_openai(self, paths, filename:str):
    local_path = paths.get_local_path(filename)
    size = os.path.getsize(local_path)
    print(f"{local_path} is {size}", flush=True)
    with open(local_path, 'rb') as r:

        file_object = self._client.files.create(
            file = r,
            purpose="assistants"
        )

    return file_object


def _create_vector_store_from_file(self, file_object):
    vector_store = self._client.beta.vector_stores.create(
        file_ids=[file_object.id],
        name="Resume",
    )

    return vector_store