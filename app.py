from pprint import pprint as pp
import requests
import flask
from flask import Flask, request, render_template
import sys

app = Flask(__name__)

VENMO_OAUTH_CLIENT_ID = "1354"
VENMO_OAUTH_CLIENT_SECRET = "GakFMxSFCEwWQ8bzYb3RLuJGwmkTBNPE"
VENMO_ACCESS_TOKEN = "eSN3Z3A2KeRbcnNTqgLu6mRA4K9uED9V"

@app.route("/")
def hello():
    return render_template('index.html', VENMO_CLIENT_ID=VENMO_OAUTH_CLIENT_ID)

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
        pp(response.__dict__)
        response_dict = flask.json.loads(response._content)
        access_token = response_dict.get('access_token')
        user = response_dict.get('user')
        return '<center>Hey there %s! <br> <img src="%s"> <br> Your access_token is <strong>%s</strong>.' % (user['name'], user['picture'], access_token)
    else:
        return "Error"
        
if __name__ == "__main__":
    app.debug = True
    app.run(port=int(sys.argv[1]) if len(sys.argv) > 1 else 80)
