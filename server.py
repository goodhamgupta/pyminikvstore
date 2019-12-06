def master(env, start_response):
    start_response("200 OK", [("Content-Type", "text/html")])
    return [b"Cmon mate"]


def volume(env, start_response):
    start_response("200 OK", [("Content-Type", "text/html")])
    return [b"Cmon mate"]
