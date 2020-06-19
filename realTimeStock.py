import json
import time
import requests
import pandas as pd
from datetime import datetime

from flask import Flask, Response, render_template, request, current_app
# from werkzeug.contrib.cache import MemcachedCache
# cache = MemcachedCache(['127.0.0.1:11211'])
from flask_caching import Cache

application = Flask(__name__)
cache = Cache(application, config={"CACHE_TYPE": "simple"})
# stocks = []
# urls = []
url_pre = "https://sandbox.iexapis.com/stable/stock/"
url_post = "/price?token=Tsk_df26d04c4e6d418eb1f0fcb7faf953c8"
# stock_chart_data = ""
# allStocks = None


def generate_all_stocks():
    nasdaq = pd.read_csv("stocks/nasdaqListed.txt", delimiter="|")
    other = pd.read_csv("stocks/otherListed.txt", delimiter="|")
    nasdaq = nasdaq[["Symbol", "Security Name"]]
    other = other[["ACT Symbol", "Security Name"]]
    other.columns = ["Symbol", "Security Name"]
    allStocks = pd.concat([nasdaq, other]).drop_duplicates().reset_index(drop=True)
    allStocks = allStocks.values.tolist()
    cache.set('allStocks', allStocks, timeout=5 * 60)


@application.route('/show/<stock>', methods=["POST", "GET"])
def show_stock(stock):
    allStocks = cache.get("allStocks")
    stocks = cache.get("stocks")
    if stock == "all":
        return render_template('base.html', allStocks=allStocks, stocks=stocks, chartType="bar")
    stock = stock.split("or")[0].strip()
    cache.set('stock_chart_data', stock, timeout=5 * 60)    
    return render_template('base.html', allStocks=allStocks, stocks=stocks, chartType="line", stock=stock.upper(),
                           duration="current")


@application.route('/show/<stock>/<duration>', methods=["POST", "GET"])
def show_stock_duration(stock, duration):
    allStocks = cache.get("allStocks")
    stocks = cache.get("stocks")
    stock = stock.split("or")[0].strip()
    cache.set('stock_chart_data', stock, timeout=5 * 60)
    stock_chart_data = cache.get("stock_chart_data")
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


@application.route('/delete/<stock>', methods=["POST", "GET"])
def delete_stock(stock):
    allStocks = cache.get("allStocks")
    stocks = cache.get("stocks")
    urls = cache.get("urls")
    stock = stock.split("or")[0].strip()
    stocks.remove(stock.upper())
    urls.remove(url_pre + stock.upper() + url_post)
    cache.set('stocks', stocks, timeout=5 * 60)
    cache.set('urls', urls, timeout=5 * 60)
    if stocks:
        return render_template('base.html', allStocks=allStocks, stocks=stocks, chartType="bar")
    else:
        return render_template('base.html', allStocks=allStocks, chartType="")


@application.route('/', methods=["POST", "GET"])
def index():
    if request.method == "POST":
        allStocks = cache.get("allStocks")
        stocks = cache.get("stocks")
        urls = cache.get("urls")
        stock = request.form["stock"]
        if stock.upper() not in stocks:
            stock = stock.split("or")[0].strip()
            stocks.append(stock.upper())
            urls.append(url_pre + stock.upper() + url_post)
            cache.set('stocks', stocks, timeout=5 * 60)
            cache.set('urls', urls, timeout=5 * 60)
        return render_template('base.html', stocks=stocks, allStocks=allStocks, chartType="bar")
    else:
        generate_all_stocks()
        cache.set('stocks', [], timeout=5 * 60)
        cache.set('urls', [], timeout=5 * 60)
        return render_template('base.html', chartType="")


@application.route('/chart-data')
def chart_data():
    def generate_random_data():
        while True:
            stock_chart_data = cache.get("stock_chart_data")
            if stock_chart_data != "":
                json_data = json.dumps(
                    {'time': datetime.now().strftime('%H:%M:%S'),
                     'value': requests.get(url_pre + stock_chart_data + url_post).json()})
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
            stocks = cache.get("stocks")
            urls = cache.get("urls")
            json_data = json.dumps(
                {'stocks': list(stocks), 'value': list(map(tester, urls))})
            yield f"data:{json_data}\n\n"
            time.sleep(5)

    return Response(generate_random_data(), mimetype='text/event-stream')


if __name__ == '__main__':
    application.run(debug=True, threaded=True)
