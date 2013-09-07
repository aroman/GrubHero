from jinja2 import Template, FileSystemLoader
from jinja2.environment import Environment

env = Environment()
env.loader = FileSystemLoader('./email_templates')

def invite_participant_template(hero, participant):
	template = env.get_template('invite_participant.html')
	return template.render(hero=hero, participant=participant)