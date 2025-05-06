import json


def get_array_from_arguments(request,key):
    print(f"Rquest method is {request.method}",flush=True)
    return_value = None
    if request.method == 'POST':
        try:
            post_key_value = request.form.get(key)
            print(f"Found value of {post_key_value} for {key} in POST",flush=True)
            post_json_object = json.loads(post_key_value)
            print(f"About to return {post_json_object} from get_array...",flush=True)
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
            print(f"About to return {get_json_object} from get_array...",flush=True)
            return_value = get_json_object
        except Exception as e:
            print(f"Exception parsing array: {e}.  Attempting to split on commas.", flush=True)
            return_value = request.args.getlist(key).split(",")
    return return_value


def _find_element_in_list_matching_criteria(to_search:list, criteria:callable):
    for item in to_search:
        if criteria(item) == True:
            return item
    return None