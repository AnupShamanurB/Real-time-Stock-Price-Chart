import json
import time
import requests
import pandas as pd
from datetime import datetime
from flask import Flask, Response, render_template, request, session, stream_with_context
from flask_session import Session
import redis

application = Flask(__name__)
application.config['SECRET_KEY'] = "edplus"
application.config['SESSION_TYPE'] = 'redis'
application.config['SESSION_REDIS'] = redis.from_url('redis://127.0.0.1:6379')
application.config["SESSION_PERMANENT"] = False
application.config["SESSION_TYPE"] = "filesystem"
Session(application)

url_pre = "https://sandbox.iexapis.com/stable/stock/"
url_post = "/price?token=Tsk_df26d04c4e6d418eb1f0fcb7faf953c8"


def generate_all_stocks():
    """
    Loads the list of all the common stocks to the session from NASDAQ listed and other listed files.
    :return:It updates the session variable "allStocks".
    """
    nasdaq = pd.read_csv("stocks/nasdaqListed.txt", delimiter="|")
    other = pd.read_csv("stocks/otherListed.txt", delimiter="|")
    nasdaq = nasdaq[["Symbol", "Security Name"]]
    other = other[["ACT Symbol", "Security Name"]]
    other.columns = ["Symbol", "Security Name"]
    allStocks = pd.concat([nasdaq, other]).drop_duplicates().reset_index(drop=True)
    allStocks = allStocks.values.tolist()
    session["allStocks"] = allStocks


@application.route('/show/<stock>')
def show_stock(stock):
    """
    Updates the stock variable with the required stock.
    :param stock: The stock which is selected by the user.
    :return: It renders the line cart for the particular stock.
    """
    allStocks = session.get("allStocks")
    stocks = session.get("stocks")
    session["stocks"] = stocks
    if stock == "all":
        return render_template('base.html', allStocks=allStocks, stocks=stocks, chartType="bar")
    stock = stock.split("or")[0].strip()
    session["stock_chart_data"] = stock
    return render_template('base.html', allStocks=allStocks, stocks=stocks, chartType="line", stock=stock.upper(),
                           duration="current")


@application.route('/show/<stock>/<duration>')
def show_stock_duration(stock, duration):
    """
    Updates the stock variable with the required stock.
    :param stock: The stock which is selected by the user.
    :param duration: The duration of the data requested by the user for the chart.
    :return: Renders the line cart for the particular stock with the data for the selected duration.
    """
    allStocks = session.get("allStocks")
    stocks = session.get("stocks")
    stock = stock.split("or")[0].strip()
    session["stock_chart_data"] = stock
    stock_chart_data = session.get("stock_chart_data")
    pre = "https://sandbox.iexapis.com/stable/stock/"
    posta = "/chart/"
    postb = "?token=Tsk_df26d04c4e6d418eb1f0fcb7faf953c8"
    result = None
    if duration == "1d":
        result = requests.get(pre + stock_chart_data + posta + duration + postb).json()
    elif duration == "1m":
        result = requests.get(pre + stock_chart_data + posta + duration + postb).json()
    elif duration == "3m":
        result = requests.get(pre + stock_chart_data + posta + duration + postb).json()
    elif duration == "6m":
        result = requests.get(pre + stock_chart_data + posta + duration + postb).json()
    labels = []
    prices = []
    for i in result:
        if i["close"] and i["label"]:
            labels.append(i["label"])
            prices.append(i["close"])
    return render_template('base.html', allStocks=allStocks, stocks=stocks, chartType="line", stock=stock.upper(),
                           duration=duration, labels=labels, prices=prices)


@application.route('/delete/<stock>')
def delete_stock(stock):
    """
    Deletes the stock from the session variable "stocks" and its url from "urls".
    :param stock: Name of the stock which user selected to delete.
    :return: Updates session variables "stock" and "urls".
    """
    allStocks = session.get("allStocks")
    stocks = session.get("stocks")
    urls = session.get("urls")
    stock = stock.split("or")[0].strip()
    if stock.upper() in stocks:
        stocks.remove(stock.upper())
        urls.remove(url_pre + stock.upper() + url_post)
    session["stocks"] = stocks
    session["urls"] = urls
    if stocks:
        return render_template('base.html', allStocks=allStocks, stocks=stocks, chartType="bar")
    else:
        return render_template('base.html', allStocks=allStocks, chartType="")


@application.route('/', methods=["POST", "GET"])
def index():
    """
    Renders the landing page and initializes all the session variables when a get request is sent.
    When a post request is sent it updates the session variable "stocks" and "urls" based on the given stock name and
    renders the bar chart.
    :return: Renders landing page or bar chart based on the type of request sent.
    """
    if request.method == "POST":
        allStocks = session.get("allStocks")
        stocks = session.get("stocks")
        urls = session.get("urls")
        stock = request.form["stock"]
        stock = stock.split("or")[0].strip()
        if stock.upper() not in stocks:
            stocks.append(stock.upper())
            urls.append(url_pre + stock.upper() + url_post)
        session["stocks"] = stocks
        session["urls"] = urls
        return render_template('base.html', stocks=stocks, allStocks=allStocks, chartType="bar")
    else:
        generate_all_stocks()
        allStocks = session.get("allStocks")
        session["stocks"] = []
        session["urls"] = []
        return render_template('base.html', allStocks=allStocks, chartType="")


@application.route('/chart-data')
def chart_data():
    """
    Contains a generator function for line chart which keeps sending the data for line chart for the stock in the
    session variable "stock_chart_data".
    :return: Price of particular stock every 5 seconds.
    """
    @stream_with_context
    def generate_chart_data():
        while True:
            stock_chart_data = session.get("stock_chart_data")
            if stock_chart_data != "":
                try:
                    value = requests.get(url_pre + stock_chart_data + url_post).json()
                except:
                    value = 0
                finally:
                    json_data = json.dumps(
                        {'time': datetime.now().strftime('%H:%M:%S'),
                         'value': value})
                    yield f"data:{json_data}\n\n"
                    time.sleep(5)
            else:
                return ""

    return Response(generate_chart_data(), mimetype='text/event-stream')


@application.route('/bar-data')
def bar_data():
    """
    Contains a generator function for bar chart which keeps sending the data for all the stocks in the
    session variable "stocks".
    :return: Prices of all the stocks as a list every 5 seconds.
    """
    def tester(url):
        try:
            return requests.get(url).json()
        except:
            return 0

    @stream_with_context
    def generate_chart_data():
        while True:
            stocks = session.get("stocks")
            urls = session.get("urls")
            json_data = json.dumps(
                {'stocks': list(stocks), 'value': list(map(tester, urls))})
            yield f"data:{json_data}\n\n"
            time.sleep(5)

    return Response(generate_chart_data(), mimetype='text/event-stream')


if __name__ == '__main__':
    application.run(debug=True)
