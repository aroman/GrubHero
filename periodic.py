import time
import datetime
import pymongo
import requests
from pymongo import MongoClient
from pprint import pprint as pp
from datetime import date, timedelta


import mailer

client = MongoClient('mongodb://thehero:thepassword@ds043338.mongolab.com:43338/grubhero-dev')
db = client['grubhero-dev']

while True:
	now = datetime.datetime.utcnow()
	fuck=now-timedelta(hours=4)
	print "Now"
	pp(now)
	print "Fuck"
	pp(fuck)
	meals = db.meals.find({"sent": False,
		"deadline": {"$lte": fuck}})
	if meals:
		print "%i meals have passed their deadlines" % meals.count()
		for meal in meals:
			print "  Meal %s has passed its deadline of %s" % (meal['name'], meal['deadline'])
			hero = db.users.find_one({"venmo_id": meal['hero_venmo_id']})
			print "    Sending an email to the meal's hero, %s..." % hero["email"]
			subject = "The deadline to order %s has passed!" % (meal['name'])
			body = mailer.deadline_reached_template(meal, hero)
			# lol u mad bro?
			url = "https://sendgrid.com/api/mail.send.json?api_user=aviromanoff&api_key=pennapps2013&to=%s&subject=%s&html=%s&from=liazon@grubhero.com&fromname=GrubHero" % (hero['email'], subject, body)
			response = requests.post(url)
			pp(response.json())
			meal['sent'] = True
			db.meals.save(meal)
	else:
		print "No meals are passed their deadlines"
	time.sleep(3)