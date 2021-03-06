from pprint import pprint as pp
import requests
import flask
import datetime
from flask import Flask, request, render_template, session, redirect, url_for, flash
from flask.ext.pymongo import PyMongo
from flask.ext.mail import Mail, Message
from bson.objectid import ObjectId
import sys
from HTMLParser import HTMLParser
from datetime import datetime
import json

import mailer

app = Flask(__name__)
app.config['MAIL_SERVER'] = "smtp.sendgrid.net"
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = ""
app.config['MAIL_PASSWORD'] = ""
app.config['MONGO_URI'] = "mongodb://:@ds043338.mongolab.com:43338/grubhero-dev"
app.secret_key = '<this was removed, smartass>' # cookie-session
mongo = PyMongo(app)
mail = Mail(app)

JQUERY_TIME_FORMAT = "%m/%d/%Y %I:%M %p"

VENMO_OAUTH_CLIENT_ID = "1354"
VENMO_OAUTH_CLIENT_SECRET = "<this was removed, smartass>"
VENMO_ACCESS_TOKEN = "<this was removed, smartass>"
VENMO_OAUTH_URL = "https://venmo.com/oauth/authorize?client_id=%s&scope=make_payments,access_profile&response_type=code" % VENMO_OAUTH_CLIENT_ID

def logged_in():
    return 'venmo_id' in session

# http://stackoverflow.com/a/925630
class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    """Removes HTML tags, and strips leading/trailing whitespace."""
    s = MLStripper()
    s.feed(html.strip())
    return s.get_data()

def single_line(text):
    """Removes redundant whitespace, and strips leading/trailing whitespace."""
    return " ".join(text.strip().split())

@app.route("/order/<meal_id>", methods=["POST", "GET"])
def order(meal_id):
    if not logged_in():
        session['return_url'] = request.url
        return redirect(VENMO_OAUTH_URL)

    meal = mongo.db.meals.find_one_or_404({'_id': ObjectId(meal_id)})

    form_data = {}
    errors = {}

    if request.method == 'POST':

        if 'comment' in request.form and request.form['comment']:
            form_data['comment'] = single_line(strip_tags(request.form['comment']))

        if 'order' in request.form and request.form['order']:
            form_data['order'] = request.form['order']

        participant = mongo.db.users.find_one({"venmo_id": session['venmo_id']})

        orders = []
        form_order_items = json.loads(form_data['order'])
        for i, quantity in form_order_items.iteritems():
            orders.append({
                "entry_index": int(i),
                "quantity": int(quantity)
            })

        to_append = {
            "venmo_id": session['venmo_id'],
            "firstname": participant['firstname'],
            "lastname": participant['lastname'],
            "picture": participant['picture'],
            "username": participant['username'],
            "ordered": datetime.utcnow(),
            "orders": orders
        }
        meal['participants'].append(to_append)

        mongo.db.activities.insert({
            "type": "ordered",
            "username": participant['username'],
            "picture": participant['picture'],
            "firstname": participant['firstname'],
            "lastname": participant['lastname'],
            "meal_id": meal_id,
            "meal_name": meal['name'],
            "when": datetime.utcnow()
        })

        pp(meal)
        mongo.db.meals.save(meal)
        flash("Your order for %s has been recorded!" % meal['name'])
        return redirect(url_for('index'))

    return render_template('order.html',
        logged_in=True,
        meal=meal,
        errors=errors,
        form_data=form_data
    )

@app.route("/")
def index():
    if logged_in():
        pp(session)

        # Meals for which logged in user is the hero
        my_meals = mongo.db.meals.find({"hero_venmo_id": session['venmo_id']})

        # Orders which the user has placed in other meals
        meals_with_orders = mongo.db.meals.find({"participants":
            {"$elemMatch": {"venmo_id": session['venmo_id']}}
        })

        # For activity stream
        activities = list(mongo.db.activities.find().limit(10))[::-1]

        for a in activities:
            pp(a)
            a['when_fuzzy'] = relativeTime(a['when'])
        pp(activities)

        orders = []
        for meal_with_order in meals_with_orders:
            me = None
            for participant in meal_with_order['participants']:
                if participant['venmo_id'] ==  session['venmo_id']:
                    me = participant
                    break
            order_entries = []
            for i, order in enumerate(me['orders']):
                order_entries.append(meal_with_order['entries'][order['entry_index']]['name'])
            tease = ", ".join(order_entries)
            to_append = {
                "name": meal_with_order['name'],
                "entries": order_entries,
                "tease": tease,
                "paid": meal_with_order['paid']
            }
            orders.append(to_append)

        return render_template('index.html',
            logged_in=True,
            meals=list(my_meals)[::-1],
            orders=orders,
            activities=list(activities),
            VENMO_CLIENT_ID=VENMO_OAUTH_CLIENT_ID,
            VENMO_OAUTH_URL=VENMO_OAUTH_URL)
    else:
        return render_template('index_logged_out.html',
            VENMO_OAUTH_URL=VENMO_OAUTH_URL)

@app.route("/video")
def video():
    return redirect("http://vimeo.com/8972896")

@app.route("/setup")
def setup():
    oauth_code = request.args.get('code')
    if oauth_code:
        url = "https://api.venmo.com/oauth/access_token"
        data = {
            "client_id": VENMO_OAUTH_CLIENT_ID,
            "client_secret": VENMO_OAUTH_CLIENT_SECRET,
            "code": oauth_code
        }
        response = requests.post(url, data)
        response_dict = response.json()
        error = response_dict.get('error')
        if error:
            return "Error from Venmo OAUTH: %s" % error
        access_token = response_dict.get('access_token')

        user = response_dict.get('user')
        print "User from venmo oauth:"
        pp(user)

        user_from_db = mongo.db.users.find_one({"venmo_id": user['id']})
        print "User from db:"
        pp(user_from_db)

        if user_from_db:
            print "User has used GrubHero before; we have them in the DB."
            user_from_db['access_token'] = access_token
            user_from_db['firstname'] = user['firstname']
            user_from_db['lastname'] = user['lastname']
            user_from_db['username'] = user['username']
            user_from_db['email'] = user['email']
            user_from_db['picture'] = user['picture']
            user_from_db['last_visit'] = datetime.utcnow()
            mongo.db.users.save(user_from_db)
        else:
            print "User has NOT used GrubHero before. Making account in DB."
            mongo.db.users.insert({
                "venmo_id": user['id'],
                "access_token": access_token,
                "firstname": user['firstname'],
                "lastname": user['lastname'],
                "username": user['username'],
                "email": user['email'],
                "picture": user['picture'],
                "last_visit": datetime.utcnow()
            })
            act_id = mongo.db.activities.insert({
                "type": "joined",
                "username": user['username'],
                "firstname": user['firstname'],
                "picture": user['picture'],
                "lastname": user['lastname'],
                "actor_venmo_id": user['id'],
                "when": datetime.utcnow()
            })
            print "THIS IS FROM SETUP"
            pp(mongo.db.activities.find_one(act_id)['when'])

        session['venmo_id'] = user['id']
        session['email'] = user['email']
        session['username'] = user['username']
        session['firstname'] = user['firstname']
        session['lastname'] = user['lastname']
        session['photo_url'] = user['picture']

        if 'return_url' in session and session['return_url']:
            url = session['return_url']
            session['return_url'] = None
            return redirect(url)
        else:
            return redirect(url_for('index'))
    else:
        return "Error"

@app.route("/meal/<meal_id>", methods=["GET"])
def view_meal(meal_id):
    meal = mongo.db.meals.find_one_or_404({'_id': ObjectId(meal_id)})
    if meal['hero_venmo_id'] != session['venmo_id']:
        return "You aren't this meal's hero."
    else:
        pp(meal)
        return render_template('meal.html',
            logged_in=True,
            meal=meal
        )

@app.route("/meals/new", methods=["POST", "GET"])
def new_meal():
    if not logged_in():
        session['return_url'] = request.url
        return redirect(VENMO_OAUTH_URL)

    form_data = {}
    errors = {}

    # Required fields
    required_fields = {
        "name": "A meal name must be specified.",
        "deadline": "An ordering deadline must be specified.",
        "users": "You must add some users to this meal.",
        "menu": "Menu options must be specified.",
    }

    # Parse / sanitize inputs
    if 'name' in request.form and request.form['name']:
        form_data['name'] = single_line(strip_tags(request.form['name']))

    if 'description' in request.form and request.form['description']:
        form_data['description'] = strip_tags(request.form['description'])

    if 'deadline' in request.form and request.form['deadline']:
        print "Begin"
        pp(request.form['deadline'])

        form_data['deadline'] = datetime.strptime(
            request.form['deadline'], JQUERY_TIME_FORMAT)
        pp(form_data['deadline'])
        form_data['deadline'].strftime("%Y")
        pp(form_data['deadline'])
        print "End"

    if 'users' in request.form and request.form['users']:
        form_data['users'] = json.loads(request.form['users'])

    if 'menu' in request.form and request.form['menu']:
        form_data['menu'] = json.loads(request.form['menu'])
        remove_items = []
        for item in form_data['menu']:
            if item['type'] == "entry" and (
                    not item["name"] or item["price"] is None):
                remove_items.append(item)
        for item in remove_items:
            form_data['menu'].remove(item)

    # Error messages for missing required fields

    if request.method == 'POST':
        for field, error_msg in required_fields.iteritems():
            if (field not in form_data or not form_data[field]
                    and field not in errors):
                errors[field] = error_msg
        if not errors:
            entries = []
            for menu_item in form_data['menu']:
                if menu_item['type'] == 'divider':
                    entries.append({"separator": True})
                else:
                    entries.append({"name": menu_item['name'],
                        "price": menu_item['price']})
            meal = {
                "hero_venmo_id": session['venmo_id'],
                "name": form_data['name'],
                "description": form_data['description'] if 'description' in form_data else None,
                "deadline": form_data['deadline'],
                "invited": form_data['users'],
                "participants": [],
                "created": datetime.utcnow(),
                "entries": entries,
                "sent": False,
                "paid": False 
            }
            mongo.db.meals.insert(meal)

            sender = mongo.db.users.find_one({"venmo_id": session['venmo_id']})

            mongo.db.activities.insert({
                "type": "created meal",
                "username": sender['username'],
                "firstname": sender['firstname'],
                "lastname": sender['lastname'],
                "picture": sender['picture'],
                "actor_venmo_id": session['venmo_id'],
                "meal_name": form_data['name'],
                "when": datetime.utcnow()
            })

            for invitee in meal['invited']:
                msg = Message("%s wants to order %s with you!" % (sender['firstname'], meal['name']),
                    sender=("GrubHero", "liazon@grubhero.com"),
                    recipients=[invitee])
                msg.html = mailer.invite_participant_template(meal, sender, invitee)
                mail.send(msg)

            flash("Meal %s created successfully!" % meal['name'])
            return redirect(url_for('index'))

    return render_template('create_meal.html',
        logged_in=True,
        form_data=form_data,
        JQUERY_TIME_FORMAT=JQUERY_TIME_FORMAT,
        errors=errors)

@app.route("/charge/<meal_id>")
def charge_meal(meal_id):
    meal = mongo.db.meals.find_one_or_404({"_id": ObjectId(meal_id)})
    if meal['hero_venmo_id'] != session['venmo_id']:
        return "YOU AREN'T THIS MEAL's HERO, ASSHOLE."
    if meal['paid']:
        return "This meal has already been paid for."
    print "Charging meal %s" % meal['name']
    hero = mongo.db.users.find_one({"venmo_id": meal['hero_venmo_id']})
    print "Hero: %s" % hero['firstname']
    final_total = 0
    for participant in meal['participants']:
        print "Participant %s" % participant['venmo_id']
        total = 0
        for i, order in enumerate(participant['orders']):
            entry = meal['entries'][i]
            print "Ordered %i %s at %.2f each" % (
                order['quantity'],
                entry['name'], 
                entry['price']
            )
            print "Adding %.2f to total" % entry['price'] * order['quantity']
            total += entry['price'] * order['quantity']
        final_total += total
        print "Total for this person: %.2f" % total
        url = "https://api.venmo.com/payments"
        data = {
            "access_token": hero['access_token'],
            "user_id": participant['venmo_id'],
            "note": "%s (via GrubHero)" % meal['name'],
            "amount": -total
        }
        pp(data)
        response = requests.post(url, data)
        pp(response.json())

    meal['paid'] = True
    mongo.db.meals.save(meal)
    mongo.db.activities.insert({
        "type": "collected payments",
        "actor_venmo_id": session['venmo_id'],
        "username": hero['username'],
        "firstname": hero['firstname'],
        "picture": hero['picture'],
        "meal_name": meal['name'],
        "lastname": hero['lastname'],
        "meal_id": meal_id,
        "when": datetime.utcnow()
    })

    flash("Charged %s participants!" % meal['name'])
    return redirect(url_for('index'))
        
@app.route("/logout")
def logout():
    session.pop('venmo_id', None)
    return redirect(url_for('index'))

@app.context_processor
def total_for_participant_and_meal():
    def func(user, meal):
        return sum(map(lambda i: i['quantity'] * meal['entries'][i['entry_index']]['price'], user['orders']))
    return dict(total_for_participant_and_meal=func)

@app.context_processor
def total_for_meal():
    p_and_m_func = total_for_participant_and_meal()
    def func(meal):
        parts = meal['participants']
        total = 0
        for p in parts:
            total += sum(map(lambda i: i['quantity'] * meal['entries'][i['entry_index']]['price'], p['orders']))
        return total
    return dict(total_for_meal=func)

def relativeTime(date):
    pp(datetime.utcnow())
    print "-"
    pp(date)
    date = date.replace(tzinfo=None)
    diff = datetime.utcnow() - date

    if diff.days > 7 or diff.days < 0:
        return date.ctime()
    elif diff.days == 1:
        return '1 day ago'
    elif diff.days > 1:
        return '%d days ago' % diff.days
    elif diff.seconds <= 1:
        return 'just now'
    elif diff.seconds < 60:
        return '%d seconds ago' % diff.seconds
    elif diff.seconds < (60 * 2):
        return '1 minute ago'
    elif diff.seconds < (60 * 60):
        return '%d minutes ago' % (diff.seconds / 60)
    elif diff.seconds < (60 * 60 * 2):
        return '1 hour ago'
    else:
        return '%d hours ago' % (diff.seconds / (60 * 60))

app.debug = True
if __name__ == "__main__":
    app.debug = True
    app.run(port=int(sys.argv[1]) if len(sys.argv) > 1 else 80)
