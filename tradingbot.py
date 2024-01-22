from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime 
from alpaca.common.rest import RESTClient 
from alpaca.data.historical.news import NewsClient
from alpaca.data.requests import NewsRequest
from timedelta import Timedelta 
from finbert_utils import estimate_sentiment
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')
API_SECRET =  os.getenv('API_SECRET')
BASE_URL = "https://paper-api.alpaca.markets"
SYMBOL="SPY"
RISK_AMOUNT=0.25
TAKE_PROFIT_AMOUNT=0.15
STOP_LOSS_AMOUNT=0.05
MIN_PROBABILTY=0.9

ALPACA_CREDS = {
    "API_KEY": API_KEY, 
    "API_SECRET": API_SECRET, 
    "PAPER": True
}

class MLTrader(Strategy): 
    def initialize(self, symbol:str=SYMBOL, cash_at_risk:float=.5): 
        self.symbol = symbol
        self.sleeptime = "24H" 
        self.last_trade = None 
        self.cash_at_risk = cash_at_risk
        self.api = RESTClient(base_url=BASE_URL, api_key=API_KEY, secret_key=API_SECRET)
        self.news_client = NewsClient(api_key=API_KEY, secret_key=API_SECRET, raw_data=True)

    def position_sizing(self): 
        cash = self.get_cash() 
        last_price = self.get_last_price(asset=self.symbol, should_use_last_close=True)
        quantity = round(cash * self.cash_at_risk / last_price, 0)
        return cash, last_price, quantity

    def get_dates(self): 
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today, three_days_prior

    def get_sentiment(self): 
        today, three_days_prior = self.get_dates()
        news = self.news_client.get_news(NewsRequest(symbols=self.symbol, start=three_days_prior, end=today))
        news = [ev["headline"] for ev in news['news']]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment 

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing() 
        print(cash, last_price)
        probability, sentiment = self.get_sentiment()

        if cash > last_price: 
            if sentiment == "positive" and probability > MIN_PROBABILTY: 
                if self.last_trade == "sell": 
                    self.sell_all() 
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "buy", 
                    type="market", 
                    take_profit_price=last_price * (1 + TAKE_PROFIT_AMOUNT), 
                    stop_loss_price=last_price * (1 - STOP_LOSS_AMOUNT)
                )
                self.submit_order(order) 
                self.last_trade = "buy"
            elif sentiment == "negative" and probability > MIN_PROBABILTY: 
                if self.last_trade == "buy": 
                    self.sell_all() 
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "sell", 
                    type="market", 
                    take_profit_price=last_price * (1 - TAKE_PROFIT_AMOUNT), 
                    stop_loss_price=last_price * (1 + STOP_LOSS_AMOUNT)
                )
                self.submit_order(order) 
                self.last_trade = "sell"

start_date = datetime(2023, 1, 1)
end_date = datetime(2023, 12, 31) 
broker = Alpaca(ALPACA_CREDS) 
strategy = MLTrader(name='mlstrat', broker=broker, 
                    parameters={"symbol": SYMBOL, 
                                "cash_at_risk": RISK_AMOUNT})
strategy.backtest(
    YahooDataBacktesting, 
    start_date, 
    end_date, 
    parameters={"symbol": SYMBOL, "cash_at_risk": RISK_AMOUNT}
)
# trader = Trader()
# trader.add_strategy(strategy)
# trader.run_all()
