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
        print session['firstname']
        return render_template('index.html',
            logged_in=True,
            VENMO_CLIENT_ID=VENMO_OAUTH_CLIENT_ID)
    else:
        return render_template('index_logged_out.html',
         VENMO_CLIENT_ID=VENMO_OAUTH_CLIENT_ID)

# user = None
# user.email

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
        pp(response_dict)

        error = response_dict.get('error')
        if error:
            return "Error from Venmo OAUTH: %s" % error
        access_token = response_dict.get('access_token')
        user = response_dict.get('user')
        pp(user)
        session['venmo_id'] = user['id']
        session['email'] = user['email']
        session['username'] = user['username']
        session['firstname'] = user['firstname']
        session['lastname'] = user['lastname']
        session['photo_url'] = user['picture']
        user = {
            "venmo_id": user['id'],
            "likes_hacking": True,
            "last_visit": datetime.datetime.utcnow()
        }
        mongo.db.users.insert(user)
        return redirect(url_for('index'))
    else:
        return "Error"
        
@app.route("/logout")
def logout():
    session.pop('venmo_id', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.debug = True
    app.run(port=int(sys.argv[1]) if len(sys.argv) > 1 else 80)
