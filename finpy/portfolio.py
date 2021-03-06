"""
(c) 2013 Tsung-Han Yang
This source code is released under the New BSD license.  
blacksburg98@yahoo.com
Created on April 1, 2013
"""
import datetime as dt
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates 
import csv
from order import Order

class Portfolio():
    def __init__(self, equities, cash, dates, nml=False, order_list=[]):
        """
        Portfolio has three items.
        equities is a dictionay of Equity instances. 
        Reference by ticker. self.equities['AAPL']
        cash is a pandas series with daily cash balance.
        total is the daily balance.
        nml indicate whether the porfolio is using normalized price or not.
        order_list is a list of Order
        """
        self.equities = equities
        self.nml = nml
        self.ldt_timestamps = dates
        ol = order_list
        ol.sort(key=lambda x: x.date)
        self.order = ol
        for x in [x for x in order_list if x.price == None]:
            if self.nml:
                x.price = self.equities[x.tick]['nml_close'][x.date]
            else:
                x.price = self.equities[x.tick]['close'][x.date]
        self.cash = pd.Series(index=dates)
        self.cash[0] = cash
        self.total = pd.Series(index=dates)
        self.total[0] = self.dailysum(dates[0])

    def dailysum(self, date):
        " Calculate the total balance of the date."
        if self.nml: 
            equities_total = np.nansum(
                [x['shares'][date] * x['nml_close'][date] for x in self.equities.values()])
        else:
            equities_total = np.nansum(
                [x['shares'][date] * x['close'][date] for x in self.equities.values()])
        total = equities_total + self.cash[date]
        return total

    def buy(self, shares, tick, price, date, update_ol=False):
        """
        Portfolio Buy 
        Calculate shares and cash upto the date.
        Before we buy, we need to update share numbers. "
        """
#        print "Buy", shares, "shares of ", tick, "at", price, "on", date
        self.cal_total(date)
        self.equities[tick].buy(date, shares, price, self.ldt_timestamps)
        self.cash[date] -= price*shares
        self.total[date] = self.dailysum(date)
        if update_ol:
            self.order.append(Order(action="buy", date=date, tick=tick, shares=shares, price=price))

    def sell(self, shares, tick, price, date, update_ol=False):
        """
        Portfolio sell 
        Calculate shares and cash upto the date.
        """
#        print "Sell", shares, "shares of ", tick, "at", price, "on", date
        self.equities[tick].sell(date, shares, price, self.ldt_timestamps)
        self.cal_total(date)
        self.cash[date] += price*shares
        self.total[date] = self.dailysum(date)
        if update_ol:
            self.order.append(Order(action="sell", date=date, tick=tick, shares=shares, price=price))

    def fillna_cash(self, date):
        " fillna on cash up to date "
        update_start = self.cash.last_valid_index()
        update_end = date
        self.cash[update_start:update_end] = self.cash[update_start]
        return update_start, update_end 

    def fillna(self, date):
        """
        fillna cash and all equities.
        return update_start and update_end.
        """
        update_start, update_end = self.fillna_cash(date)
        for e in self.equities:
            self.equities[e].fillna_shares(date, self.ldt_timestamps)
        return update_start, update_end

    def cal_total(self, date):
        """
        Calculate total up to "date".
        """
        update_start, update_end = self.fillna(date)
        for date_id in range(self.ldt_timestamps.index(update_start),self.ldt_timestamps.index(update_end)+1):
            xdate = self.ldt_timestamps[date_id]
            self.total[date_id] = self.dailysum(xdate)

    def put_orders(self):
        """
        Put the order list to the DataFrame.
        Update shares, cash, buy and sell columns of each Equity
        """
        for o in self.order:
            if o.action.lower() == "buy":
                self.buy(date=o.date, shares=np.float(o.shares), price=np.float(o.price), tick=o.tick)
            elif o.action.lower() == "sell":
                self.sell(shares=np.float(o.shares), tick=o.tick, price=np.float(o.price), date=o.date)

    def sim(self, ldt_timestamps=None):
        """
        Go through each day and calculate total and cash.
        """
        self.put_orders()
        if ldt_timestamps == None:
            ldt_timestamps = self.ldt_timestamps
        dt_end = ldt_timestamps[-1]
        self.cal_total(dt_end)

    def csvwriter(self, equity_col=None, csv_file="pf.csv", total=True, cash=True, d=','):
        """
        Write the content of the Portfolio to a csv file.
        If total is True, the total is printed to the csv file.
        If cash is True, the cash is printed to the csv file.
        equity_col specify which columns to print for an equity.
        The specified column of each equity will be printed.
        """
        lines = []
        l = []
        l.extend(["Year", "Month", "Date"])
        if total:
            l.append("Total")
        if cash:
            l.append("Cash")
        if equity_col != None:
            for e in self.equities:
                for col in equity_col:
                    label = e + col
                    l.append(label)
        lines.append(l)
        for i in self.ldt_timestamps:
            l = []
            l.extend([i.strftime("%Y"), i.strftime("%m"), i.strftime("%d")])
            if total:
                l.append(round(self.total[i], 2))
            if cash:
                l.append(round(self.cash[i], 2))
            if equity_col != None:
                for e in self.equities:
                    for col in equity_col:
                        l.append(round(self.equities[e][col][i], 2))
            lines.append(l)
        with open(csv_file, 'w') as fp:
            cw = csv.writer(fp, lineterminator='\n', delimiter=d)
            for line in lines:
                cw.writerow(line)

    def dailyrtn(self):
        """
        Return the return of each day, a list.
        """
        daily_rtn = []
        for date in range(len(self.ldt_timestamps)):
            if date == 0:
                daily_rtn.append(0)
            else:
             daily_rtn.append((self.total[date]/self.total[date-1])-1)
        return daily_rtn

    def avg_dailyrtn(self):
        " Average of the dailyrtn list "
        return np.average(self.dailyrtn())

    def std(self):
        " Standard Deviation of the dailyrtn "
        return np.std(self.dailyrtn())

    def sharpe(self, k=252):
        " Return Sharpe ratio. You can overwrite the coefficient with k"
        return np.sqrt(k) * self.avg_dailyrtn()/self.std()

    def totalrtn(self):
        " Return the return ratio of the period "
        return self.total[-1]/self.total[0]

    def plot(self, ax, ldt_timestamps, nml=True):
        " plot the total of Portfolio "
        if nml:
            ax.plot(ldt_timestamps, self.total/self.total[0])
        else:
            ax.plot(ldt_timestamps, self.total)

    def moving_average(self, window=20, nml=False):
      """
      Return an array of moving average. Window specified how many days in
      a window.
      """
      if nml:
        ma = pd.stats.moments.rolling_mean(self.total/self.total[0], window=window)
      else:
        ma = pd.stats.moments.rolling_mean(self.total, window=window)
      ma[0:window] = ma[window]
      return ma
