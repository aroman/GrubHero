from pprint import pprint as pp
import requests
import flask
from flask import Flask, request, render_template, session, redirect, url_for
import sys

app = Flask(__name__)
# For sessions
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

VENMO_OAUTH_CLIENT_ID = "1354"
VENMO_OAUTH_CLIENT_SECRET = "GakFMxSFCEwWQ8bzYb3RLuJGwmkTBNPE"
VENMO_ACCESS_TOKEN = "eSN3Z3A2KeRbcnNTqgLu6mRA4K9uED9V"

@app.route("/")
def index():
    if 'venmo-id' in session:
        return render_template('index.html',
            logged_in=True,
            VENMO_CLIENT_ID=VENMO_OAUTH_CLIENT_ID)
    else:
        return render_template('index.html',
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
        access_token = response_dict.get('access_token')
        user = response_dict.get('user')
        session['venmo-id'] = response_dict.get('venmo-id')
        session['firstname'] = response_dict.get('firstname')
        session['lastname'] = response_dict.get('lastname')
        return redirect(url_for('index'))
    else:
        return "Error"
        
@app.route("/logout")
def logout():
    session.pop('venmo-id', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.debug = True
    app.run(port=int(sys.argv[1]) if len(sys.argv) > 1 else 80)
