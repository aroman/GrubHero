from flask import Flask
from flask_oauth import OAuth

app = Flask(__name__)

VENMO_ACCESS_TOKEN = "eSN3Z3A2KeRbcnNTqgLu6mRA4K9uED9V"

oauth = OAuth()
venmo = oauth.remote_app('venmo',
	base_url = 'https://sandbox-api.venmo.com/',
	request_token_url = 'https://api.venmo.com'
)

@app.route("/")
def hello():
    return "Welcome to GrubHero, you are on the homepage."

@app.route

if __name__ == "__main__":
	app.debug = True
    app.run()