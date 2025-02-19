def trim_before_substring(main_string:str, substring:str)->str:
    index = main_string.find(substring)
    if index != -1:
        return main_string[index:]
    return main_string


def _trim_after_last_substring(main_string:str, substring)->str:
    index = main_string.rfind(substring)
    if index != -1:
        return main_string[:index + len(substring)]
    return main_string