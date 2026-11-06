"""Check ids before they are used in URLs."""


def require_id(value: object) -> str:
    """Return the id as a string, or raise if it is empty.

    With an empty id, a URL such as /races/{id} becomes /races/. The services
    redirect that to /races, and the client follows the redirect: a GET gets
    the list of all races, and a DELETE could delete every item in the list.
    """
    text = "" if value is None else str(value)
    if not text.strip():
        msg = "Mangler id."
        # a plain Exception: the message is shown to the user (see error_text)
        raise Exception(msg)
    return text
