from pprint import pprint as pp
import requests
import flask
import datetime
from flask import Flask, request, render_template, session, redirect, url_for
from flask.ext.pymongo import PyMongo
from flask.ext.mail import Mail, Message
import sys
from HTMLParser import HTMLParser
from datetime import datetime

import mailer

app = Flask(__name__)
app.config['MAIL_SERVER'] = "smtp.sendgrid.net"
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = "aviromanoff"
app.config['MAIL_PASSWORD'] = "pennapps2013"
app.config['MONGO_URI'] = "mongodb://thehero:thepassword@ds043338.mongolab.com:43338/grubhero-dev"
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT' # cookie-session
app.config
mongo = PyMongo(app)
mail = Mail(app)

JQUERY_TIME_FORMAT = "%m/%d/%Y %I:%M %p"

VENMO_OAUTH_CLIENT_ID = "1354"
VENMO_OAUTH_CLIENT_SECRET = "GakFMxSFCEwWQ8bzYb3RLuJGwmkTBNPE"
VENMO_ACCESS_TOKEN = "eSN3Z3A2KeRbcnNTqgLu6mRA4K9uED9V"
VENMO_OAUTH_URL = "https://sandbox-api.venmo.com/oauth/authorize?client_id=%s&scope=make_payments,access_profile&response_type=code" % VENMO_OAUTH_CLIENT_ID

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

        orders = []
        for meal_with_order in meals_with_orders:
            me = None
            for participant in meal_with_order['participants']:
                if participant['venmo_id'] ==  session['venmo_id']:
                    me = participant
                    break
            order_entries = []
            for i, order in enumerate(me['orders']):
                if 'separator' in meal_with_order['entries'][order['entry_index']]:
                    continue
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
            meals=my_meals,
            orders=orders,
            VENMO_CLIENT_ID=VENMO_OAUTH_CLIENT_ID,
            VENMO_OAUTH_URL=VENMO_OAUTH_URL)
    else:
        return render_template('index_logged_out.html',
            VENMO_OAUTH_URL=VENMO_OAUTH_URL)


@app.route("/send_email_to/<target_venmo_id>")
def send_email_to(target_venmo_id):
    sender = mongo.db.users.find_one({"venmo_id": session['venmo_id']})
    target = mongo.db.users.find_one({"venmo_id": target_venmo_id})
    msg = Message("%s wants to be your Grub Hero!" % sender['firstname'],
        sender=("GrubHero", "liazon@grubhero.com"),
        recipients=[target['email']])
    msg.html = mailer.invite_participant_template(sender, target)
    mail.send(msg)
    return "Email sent :)"

@app.route("/create_meal/<name>")
def create_meal(name):
    if not logged_in():
        session['return_url'] = request.url
        return redirect(VENMO_OAUTH_URL)

    meal = {
        "hero_venmo_id": session['venmo_id'],
        "name": name,
        "description": "Because finals are tomorrow",
        "deadline": datetime(2013, 9, 8, 18),
        "paid": False
    }
    mongo.db.meals.insert(meal)
    return 'Meal with name %s created. <a href="/">Go home</a>' % name

@app.route("/setup")
def setup():
    oauth_code = request.args.get('code')
    if oauth_code:
        url = "https://sandbox-api.venmo.com/oauth/access_token"
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
                "email": user['email'],
                "picture": user['picture'],
                "last_visit": datetime.utcnow()
            })

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

@app.route("/user/<venmo_id>")
def user(venmo_id):
    if not logged_in():
        session['return_url'] = request.url
        return redirect(VENMO_OAUTH_URL)

    person = mongo.db.users.find_one_or_404({"venmo_id": venmo_id})
    return render_template('user.html', person=person, logged_in=True)

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
        form_data['deadline'] = datetime.strptime(
            request.form['deadline'], JQUERY_TIME_FORMAT)
        form_data['deadline'].strftime("%Y")

    # Error messages for missing required fields

    if request.method == 'POST':
        for field, error_msg in required_fields.iteritems():
            if (field not in form_data or not form_data[field]
                    and field not in errors):
                errors[field] = error_msg

    return render_template('create_meal.html',
        logged_in=True,
        form_data=form_data,
        JQUERY_TIME_FORMAT=JQUERY_TIME_FORMAT,
        errors=errors)

@app.route("/bbq")
def lolwtfbbq():
    le_meal = mongo.db.meals.find_one({"name": "Le Chinese Dinner"})
    charge_meal(le_meal)
    return "TROLOLOLOLOLOL"

def charge_meal(meal):
    print "Charging meal %s" % meal['name']
    hero = mongo.db.users.find_one({"venmo_id": meal['hero_venmo_id']})
    print "Hero: %s" % hero['firstname'] 
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
        print "Total for this person: %.2f" % total
        url = "https://sandbox-api.venmo.com/payments"
        data = {
            "access_token": hero['access_token'],
            "user_id": "153136" or participant['venmo_id'],
            "note": "%s (via GrubHero)" % meal['name'],
            "amount": -0.10 or -total
        }
        pp(data)
        response = requests.post(url, data)
        pp(response.json())
        
@app.route("/logout")
def logout():
    session.pop('venmo_id', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.debug = True
    app.run(port=int(sys.argv[1]) if len(sys.argv) > 1 else 80)
