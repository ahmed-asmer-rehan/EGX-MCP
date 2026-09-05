from tvDatafeed import TvDatafeed, Interval
from retry import retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta, date
import datetime as dt
import pandas as pd
import numpy as np
import holidays
from datetime import datetime as dt
import logging

logger = logging.getLogger("egx_dnld")
logger.setLevel(logging.DEBUG)  # Capture all levels
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@retry((Exception), tries=3, delay=0.3, backoff=0)
def get_OHLCV_data(symbol,exchange,interval,n_bars):
    """fetches close prices for a single ticker

    Args:
        symbol (str): Ticker
        exchange (str): Exchange / Market "EGX"
        interval (str): ['Daily', 'Weekly','Monthly']
        n_bars (int): Last n bars

    Returns:
        pd.DataFrame: response
    """

    interval_dic = {'Daily':Interval.in_daily, 'Weekly':Interval.in_weekly, 'Monthly':Interval.in_monthly}
    if interval not in interval_dic.keys():
        raise ValueError("Invalid Interval value, it should be one of {}".format(interval_dic.keys()))

    tv = TvDatafeed()
    response = tv.get_hist(symbol=symbol,
                           exchange=exchange,interval=interval_dic[interval],
                           n_bars=n_bars)
    return response



@retry((Exception), tries=3, delay=0.3, backoff=0)
def _get_intraday_close_price_data(symbol,exchange,interval,n_bars):
    """fetches close prices for a single ticker

    Args:
        symbol (str): Ticker
        exchange (str): Exchange / Market "EGX"
        interval (str): ['1 Minute', '5 Minute','30 Minute']
        n_bars (int): Last n bars

    Returns:
        pd.DataFrame: response
    """

    interval_dic = {'1 Minute':Interval.in_1_minute, '5 Minute':Interval.in_5_minute, '30 Minute':Interval.in_30_minute}
    if interval not in interval_dic.keys():
        raise ValueError("Invalid Interval value, it should be one of {}".format(interval_dic.keys()))

    tv = TvDatafeed()
    response = tv.get_hist(symbol=symbol,
                           exchange=exchange,
                           interval=interval_dic[interval],
                           n_bars=n_bars)['close']
    return response

@retry((Exception), tries=3, delay=0.3, backoff=0)
def _get_close_price_data(symbol,exchange,interval,n_bars):
    """fetches close prices for a single ticker

    Args:
        symbol (str): Ticker
        exchange (str): Exchange / Market "EGX"
        interval (str): ['Daily', 'Weekly','Monthly']
        n_bars (int): Last n bars

    Returns:
        pd.DataFrame: response
    """

    interval_dic = {'Daily':Interval.in_daily, 'Weekly':Interval.in_weekly, 'Monthly':Interval.in_monthly}
    if interval not in interval_dic.keys():
        raise ValueError("Invalid Interval value, it should be one of {}".format(interval_dic.keys()))


    tv = TvDatafeed()
    response = tv.get_hist(symbol=symbol,
                           exchange=exchange,
                           interval=interval_dic[interval], 
                           n_bars=n_bars
                           )['close']
    return response



def get_EGXdata(stock_list:list, interval:str, start:date, end:date):
    """Fetches Historical close prices data for EGX stocks

    Args:
        stock_list (list): desired stock list
        interval (str): ['Daily', 'Weekly','Monthly']
        start (date): starting date
        end (date): end date

    Returns:
        pd.DataFrame: close prices indexed by date
    """

    work_days_count = holidays.country_holidays('EG').get_working_days_count(start,end)

    close_prices_dic = {}
    skip_dic = {}

    if work_days_count < 1:
        return pd.DataFrame()

    def _fetch_one(stock):
        return stock, _get_close_price_data(
            symbol=stock, exchange='EGX',
            interval=interval, n_bars=work_days_count)

    executor = ThreadPoolExecutor(max_workers=10)
    try:
        futures = {executor.submit(_fetch_one, stock): stock for stock in stock_list}
        try:
            for future in as_completed(futures, timeout=25):
                stock = futures[future]
                try:
                    _, close = future.result(timeout=0)
                    close_prices_dic[stock] = close
                except Exception as e:
                    skip_dic[stock] = str(e)
        except TimeoutError:
            # A timeout here means some futures are still pending; keep whatever
            # already completed instead of discarding the whole batch (see
            # research.md R3 addendum for the incident this fixes).
            pending = [futures[f] for f in futures if not f.done()]
            logger.warning("Timed out waiting for tickers: {}".format(pending))
    finally:
        executor.shutdown(wait=False)

    logger.info("Got Stock Prices: {}".format(close_prices_dic.keys()))
    logger.info("Failed Stocks: {}".format(skip_dic))

    if not close_prices_dic:
        return pd.DataFrame()

    df = pd.concat(close_prices_dic,axis=1)
    df.index = pd.to_datetime(df.index.date)
    df.index.name = 'Date'

    return df.loc[start:end,:]


def _compute_intraday_bars(interval: str, start: date, end: date) -> int:
    interval_minutes = {'1 Minute': 1, '5 Minute': 5, '30 Minute': 30}
    minutes_per_interval = interval_minutes.get(interval, 1)
    # EGX trades ~270 minutes/day (10:00 - 14:30)
    bars_per_day = (300 // minutes_per_interval) + 10
    trading_days = max(1, holidays.country_holidays('EG').get_working_days_count(start, end))
    return min(bars_per_day * trading_days, 5000)


def get_EGX_intraday_data(stock_list:list, interval:str, start:date, end:date):
    """Fetches intraday data for EGX stocks

    Args:
        stock_list (list): desired stocks
        interval (str): ['1 Minute', '5 Minute','30 Minute']
        start (date): starting date
        end (date): end date

    Returns:
        pd.DataFrame: close prices
    """

    n = _compute_intraday_bars(interval, start, end)

    close_prices_dic = {}
    skip_dic = {}

    def _fetch_one(stock):
        return stock, _get_intraday_close_price_data(
            symbol=stock, exchange='EGX',
            interval=interval, n_bars=n)

    executor = ThreadPoolExecutor(max_workers=10)
    try:
        futures = {executor.submit(_fetch_one, stock): stock for stock in stock_list}
        try:
            for future in as_completed(futures, timeout=25):
                stock = futures[future]
                try:
                    _, close = future.result(timeout=0)
                    close_prices_dic[stock] = close
                except Exception as e:
                    skip_dic[stock] = str(e)
        except TimeoutError:
            # See get_EGXdata above: keep whatever completed rather than discarding
            # the whole batch on a partial timeout (research.md R3 addendum).
            pending = [futures[f] for f in futures if not f.done()]
            logger.warning("Timed out waiting for tickers: {}".format(pending))
    finally:
        executor.shutdown(wait=False)

    logger.info("Got Intraday Prices: {}".format(close_prices_dic.keys()))
    logger.info("Failed Stocks: {}".format(skip_dic))

    if not close_prices_dic:
        return pd.DataFrame()

    df = pd.concat(close_prices_dic,axis=1)

    return df.loc[start:end,:].tz_localize("Europe/London").tz_convert("UTC+02:00")
