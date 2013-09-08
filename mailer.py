from jinja2 import Template, FileSystemLoader
from jinja2.environment import Environment

env = Environment()
env.loader = FileSystemLoader('./email_templates')

def invite_participant_template(meal, hero, invitee):
	template = env.get_template('invite_participant.html')
	return template.render(meal=meal, hero=hero, invitee=invitee)

def deadline_reached_template(meal, hero):
	template = env.get_template('deadline_reached.html')
	return template.render(meal=meal, hero=hero)