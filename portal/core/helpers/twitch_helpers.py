from num2words import num2words
import emoji
import re

# Standard message object for Action use
class MessageObject():
	def __init__(
			self,
			event: str,
			broadcaster: str,
			file_name: str,
			message: str,
			user: str,
			cost: int
		):

		self.event = event
		self.broadcaster = broadcaster
		self.file_name = file_name
		message = replace_emoji(message)
		message = convert_numbers(message)
		self.message = message
		self.user = user
		self.cost = cost

def replace_emoji(message: str) -> str:
	message = re.sub(':[\\w_]+:', lambda m: re.sub('[:_]', ' ', m.group()), emoji.demojize(message))
	return message


def convert_numbers(message: str) -> str:
	message = re.sub('£(\\d+)', lambda m: num2words(m.group(1), to='currency', currency='GBP'), message)
	message = re.sub('\\$(\\d+)', lambda m: num2words(m.group(1), to='currency', currency='USD'), message)
	message = re.sub('(\\d+)', lambda m: num2words(m.group()), message)
	return message

def remove_cheermotes(raw_message: str) -> str:
	prefixes = (
		"cheer", "hrycheer", "biblethump", "cheerwhal",
		"corgo", "uni", "showlove", "party",
		"seemsgood", "pride", "kappa", "frankerz",
		"heyguys", "dansgame", "elegiggle", "trihard",
		"kreygasm",	"4head", "swiftrage", "notlikethis",
		"failfish", "vohiyo", "pjsalt", "mrdestructoid",
		"bday",	"ripcheer",	"shamrock"
	)

	word_list = raw_message.split(" ")
	message = ""
	for word in word_list:
		if word.lower().startswith(prefixes) and word[-1].isdigit():
			continue
		message += word + " "
	message.strip()
	return message