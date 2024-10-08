import re


def check_link(link: str) -> bool:
    pattern = r"^(https?://)?(www\.)?[a-zA-Z0-9-]+(\.[a-zA-Z]{2,})+(/[a-zA-Z0-9#-]*)*$"
    if re.match(pattern, link):
        return True
    return False