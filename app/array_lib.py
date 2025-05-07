import json


def get_array_from_arguments(request,key):
    print(f"Rquest method is {request.method}",flush=True)
    return_value = None
    if request.method == 'POST':
        request_data = request.form
    else:
        request_data = request.args

    try:
        string_value = request_data.get(key)
        print(f"Attempting to extract list as JSON from POST: {string_value}", flush=True)
        json_object = json.loads(string_value)
        print(f"JSON Parse successful - returning {json_object}",flush=True)
        return json_object
    except Exception as e:
        print(f"JSON Parsing failed: {e}. Running getlist...", flush=True)
        return request.getlist(key)
  


def _find_element_in_list_matching_criteria(to_search:list, criteria:callable):
    for item in to_search:
        if criteria(item) == True:
            return item
    return None