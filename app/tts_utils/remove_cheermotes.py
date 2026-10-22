PREFIXES = [
    "cheer", "hrycheer", "biblethump", "cheerwhal", "corgo", "uni", "showlove", "party", "seemsgood",
    "pride", "kappa", "frankerz", "heyguys", "dansgame", "elegiggle", "trihard", "kreygasm", "4head",
    "swiftrage", "notlikethis", "failfish", "vohiyo", "pjsalt", "mrdestructoid", "bday", "ripcheer",
    "shamrock"
]

def remove_cheermotes(raw_message):
    word_list = raw_message.split(" ")
    message = ""
    for word in word_list:
        if word.lower().startswith(tuple(PREFIXES)) and word[-1].isdigit():
            continue
        message += word + " "
    message.strip()
    return message