import json
import random
import time
import requests
from datetime import datetime

from flask import Flask, Response, render_template, request

application = Flask(__name__)
random.seed()  # Initialize the random number generator

stocks = []
urls = []
url_pre = "https://sandbox.iexapis.com/stable/stock/"
url_post = "/price?token=Tsk_df26d04c4e6d418eb1f0fcb7faf953c8"
stock_chart_data = ""

@application.route('/show/<stock>', methods=["POST","GET"])
def showStock(stock):
    if stock == "all":
        return render_template('base.html',stocks=stocks,chartType="bar")
    global stock_chart_data
    stock_chart_data = stock
    return render_template('base.html',stocks=stocks,chartType="line",stock=stock.upper(), duration="current")

@application.route('/show/<stock>/<duration>', methods=["POST","GET"])
def showStockDuration(stock,duration):
    global stock_chart_data
    stock_chart_data = stock
    pre = "https://sandbox.iexapis.com/stable/stock/"
    posta = "/chart/"
    postb = "?token=Tsk_df26d04c4e6d418eb1f0fcb7faf953c8"
    result = None
    if duration == "1d":
        result = requests.get(pre+stock_chart_data+posta+duration+postb).json()
    elif duration == "1m":
        result = requests.get(pre+stock_chart_data+posta+duration+postb).json()
    elif duration == "3m":
        result = requests.get(pre+stock_chart_data+posta+duration+postb).json()
    elif duration == "6m":
        result = requests.get(pre+stock_chart_data+posta+duration+postb).json()
    labels = []
    prices = []
    for i in result:
        if i["close"] and i["label"]:
            labels.append(i["label"])
            prices.append(i["close"])
    return render_template('base.html',stocks=stocks,chartType="line",stock=stock.upper(), duration=duration, labels=labels, prices=prices)
    

@application.route('/delete/<stock>', methods=["POST","GET"])
def deleteStock(stock):
    stocks.remove(stock.upper())
    urls.remove(url_pre+stock.upper()+url_post)
    if stocks:
        return render_template('base.html',stocks=stocks,chartType="bar")
    else:
        return render_template('base.html',chartType="")

@application.route('/', methods=["POST","GET"])
def index():
    global stocks
    global urls
    if request.method == "POST":
        stock = request.form["stock"]
        if stock not in stocks:
            stocks.append(stock.upper())
            urls.append(url_pre+stock.upper()+url_post)
        return render_template('base.html',stocks=stocks, chartType="bar")
    else:
        stocks = []
        urls = []
        return render_template('base.html', chartType="")

@application.route('/chart-data')
def chart_data():
    def generate_random_data():
        while True:
            if stock_chart_data != "":
                json_data = json.dumps(
                {'time': datetime.now().strftime('%H:%M:%S'), 'value': requests.get(url_pre+stock_chart_data+url_post).json()})
                yield f"data:{json_data}\n\n"
                time.sleep(5)
            else:
                return ""

    return Response(generate_random_data(), mimetype='text/event-stream')

@application.route('/bar-data')
def bar_data():
    def tester(url):
        return requests.get(url).json()

    def generate_random_data():
        while True:
            json_data = json.dumps(
                {'stocks': list(stocks), 'value': list(map(tester, urls))})
            yield f"data:{json_data}\n\n"
            time.sleep(5)

    return Response(generate_random_data(), mimetype='text/event-stream')

if __name__ == '__main__':
    application.run(debug=True, threaded=True)
