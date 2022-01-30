from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Execute Order 66"

def run():
  app.run(host='0.0.0.0',port=8080)

def runServer():
    t = Thread(target=run)
    t.start()
