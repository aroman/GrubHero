from flask import Flask
app = Flask(__name__)

APP_NAME = "venmo-food"

@app.route("/")
def hello():
    return "Welcome to %s!" % APP_NAME

if __name__ == "__main__":
    app.run()
