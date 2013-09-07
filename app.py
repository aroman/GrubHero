from pprint import pprint as pp
import requests
import flask
import datetime
from flask import Flask, request, render_template, session, redirect, url_for
from flask.ext.pymongo import PyMongo
import sys

app = Flask(__name__)
app.config['MONGO_URI'] = "mongodb://thehero:thepassword@ds043338.mongolab.com:43338/grubhero-dev"
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT' # cookie-session
mongo = PyMongo(app)


VENMO_OAUTH_CLIENT_ID = "1354"
VENMO_OAUTH_CLIENT_SECRET = "GakFMxSFCEwWQ8bzYb3RLuJGwmkTBNPE"
VENMO_ACCESS_TOKEN = "eSN3Z3A2KeRbcnNTqgLu6mRA4K9uED9V"

@app.route("/")
def index():
    if 'venmo_id' in session:
        pp(session)

        return render_template('index.html',
            logged_in=True,
            meals=mongo.db.meals.find(),
            VENMO_CLIENT_ID=VENMO_OAUTH_CLIENT_ID)
    else:
        return render_template('index_logged_out.html',
         VENMO_CLIENT_ID=VENMO_OAUTH_CLIENT_ID)


@app.route("/create_meal/<name>")
def create_meal(name):
    if 'venmo_id' in session:
        meal = {
            "hero_venmo_id": session['venmo_id'],
            "name": name,
            "description": "Because finals are tomorrow",
            "deadline": datetime.datetime(2013, 9, 8, 18),
            "paid": False
        }
        mongo.db.meals.insert(meal)
        return 'Meal with name %s created. <a href="/">Go home</a>' % name
    else:
        return redirect(url_for('index'))

@app.route("/setup")
def setup():
    oauth_code = request.args.get('code')
    if oauth_code:
        data = {
            "client_id": VENMO_OAUTH_CLIENT_ID,
            "client_secret": VENMO_OAUTH_CLIENT_SECRET,
            "code": oauth_code
        }

        url = "https://api.venmo.com/oauth/access_token"
        response = requests.post(url, data)
        response_dict = response.json()
        error = response_dict.get('error')
        if error:
            return "Error from Venmo OAUTH: %s" % error
        access_token = response_dict.get('access_token')
        user = response_dict.get('user')
        session['venmo_id'] = user['id']
        session['email'] = user['email']
        session['username'] = user['username']
        session['firstname'] = user['firstname']
        session['lastname'] = user['lastname']
        session['photo_url'] = user['picture']
        user = {
            "venmo_id": user['id'],
            "access_token": access_token,
            "firstname": user['firstname'],
            "lastname": user['lastname'],
            "picture": user['picture'],
            "last_visit": datetime.datetime.utcnow()
        }
        mongo.db.users.insert(user)
        return redirect(url_for('index'))
    else:
        return "Error"

@app.route("/user/<venmo_id>")
def user(venmo_id):
    if 'venmo_id' in session:
        person = mongo.db.users.find_one_or_404({"venmo_id": venmo_id})
        return render_template('user.html', person=person, logged_in=True)
    else:
        return redirect(url_for('index'))

@app.route("/logout")
def logout():
    session.pop('venmo_id', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.debug = True
    app.run(port=int(sys.argv[1]) if len(sys.argv) > 1 else 80)
