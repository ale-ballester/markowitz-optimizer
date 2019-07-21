import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import scipy.optimize as sco

NUMBER_OF_PORTFOLIOS = 25000
TRADINGDAYS = 207 # Try 200
NUMBER_OF_EFFICIENT_PORTFOLIOS = 50


## Functions

def find_nearest(array, value):
    array = np.asarray(array)
    ind = np.abs(array-value).argmin()
    return array[ind], ind 

def mean_daily_log_return(log_returns):
    return log_returns.mean()

def portfolio_features(w, mean_daily_log_returns, tradingdays):
    ret = np.sum((mean_daily_log_returns * w)) * tradingdays
    risk = np.sqrt(np.dot(w.T, np.dot(log_returns.cov()*tradingdays, w)))
    return ret, risk

def sharpe(rets, risk, risk_free_return=0):
    return (rets-risk_free_return)/risk

def generate_portfolios(number_of_portfolios, log_returns, tradingdays, risk_free_return=0):
    np.random.seed(42)
    number_of_assets = len(log_returns.columns)

    weights = np.zeros((number_of_portfolios, number_of_assets))
    features = np.zeros((number_of_portfolios, 3))

    for i in range(number_of_portfolios):
        # Weights
        ws = np.array(np.random.random(number_of_assets))
        ws = ws/np.sum(ws)
        weights[i,:] = ws

        r, v = portfolio_features(ws, mean_daily_log_return(log_returns), tradingdays)
        s = sharpe(r, v, risk_free_return)
        
        # Expected return / volatility
        features[i,:] = [r,v,s]
        
    return features, weights

# To minimize
def portfolio_volatility(w, mean_daily_log_returns, tradingdays):
    ret, risk = portfolio_features(w, mean_daily_log_returns, tradingdays)
    return risk

# Returns objects containing:
# Weights that minimize volatility for each target return
# The associated volatility
def efficient_return(target_return, mean_daily_log_returns, tradingdays):
    number_of_assets = len(mean_daily_log_returns)
    args = (mean_daily_log_returns, tradingdays)

    portfolio_return = lambda w: portfolio_features(w, mean_daily_log_returns, tradingdays)[0]

    constraints = ({'type': 'eq', 'fun': lambda x: portfolio_return(x) - target_return},
                   {'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
    bounds = tuple((0,1) for asset in range(number_of_assets))

    return sco.minimize(portfolio_volatility, number_of_assets*[1/number_of_assets], args=args, method='SLSQP', bounds=bounds, constraints=constraints)

def efficient_frontier(mean_daily_log_returns, returns_range, tradingdays):
    efficients = []
    for r in returns_range:
        efficients.append(efficient_return(r, mean_daily_log_returns, tradingdays))
    return efficients

## Read data: Data will be fed by FIX

stocks = pd.read_csv("data/series.csv", index_col="Date", parse_dates=True)

"""
AMZN = pd.read_csv("data/AMZN.csv", index_col="Date", parse_dates=True).drop(labels=["Open", "High", "Low", "Close", "Volume"], axis=1)
AAPL = pd.read_csv("data/AAPL.csv", index_col="Date", parse_dates=True).drop(labels=["Open", "High", "Low", "Close", "Volume"], axis=1)
IBM = pd.read_csv("data/IBM.csv", index_col="Date", parse_dates=True).drop(labels=["Open", "High", "Low", "Close", "Volume"], axis=1)
CSCO = pd.read_csv("data/CSCO.csv", index_col="Date", parse_dates=True).drop(labels=["Open", "High", "Low", "Close", "Volume"], axis=1)
SYP500 = pd.read_csv("data/SYP500.csv", index_col="Date", parse_dates=True).drop(labels=["Open", "High", "Low", "Close", "Volume"], axis=1)
TSLA = pd.read_csv("data/TSLA.csv", index_col="Date", parse_dates=True).drop(labels=["Open", "High", "Low", "Close", "Volume"], axis=1)
GOOG = pd.read_csv("data/GOOG.csv", index_col="Date", parse_dates=True).drop(labels=["Open", "High", "Low", "Close", "Volume"], axis=1)

stocks = pd.concat((AMZN, AAPL, IBM, CSCO, SYP500, TSLA, GOOG), axis=1)
"""

log_returns = np.log(stocks/stocks.shift(1))    

## Generate portfolios / Risk tolerance

risk_tolerance = float(input("Enter your risk tolerance [0-100]: "))
features, weights = generate_portfolios(NUMBER_OF_PORTFOLIOS, log_returns, TRADINGDAYS)

## Max sharpe / Min risk

ind = features[:,2].argmax()
portfolio_max_sharpe = {
    'return': features[ind,0], 
    'volatility': features[ind,1], 
    'sharpe': features[ind,2], 
    'weights': weights[ind],
    'index': ind,
}

ind = features[:,1].argmin()
portfolio_min_risk = {
    'return': features[ind,0], 
    'volatility': features[ind,1], 
    'sharpe': features[ind,2], 
    'weights': weights[ind],
    'index': ind,
}

ind = features[:,0].argmax()
portfolio_max_return = {
    'return': features[ind,0], 
    'volatility': features[ind,1], 
    'sharpe': features[ind,2], 
    'weights': weights[ind],
    'index': ind,
}


## Efficient frontier

min_return, max_return = portfolio_min_risk['return'], portfolio_max_return['return']
target_return = np.linspace(min_return, max_return, NUMBER_OF_EFFICIENT_PORTFOLIOS)
efficient_portfolios = efficient_frontier(mean_daily_log_return(log_returns), target_return, TRADINGDAYS)

## Optimizer

investor_risk = portfolio_min_risk['volatility'] + (risk_tolerance/100)*(portfolio_max_return['volatility']-portfolio_min_risk['volatility'])


efficient_volatilities = [p['fun'] for p in efficient_portfolios]

investor_risk, investor_index = find_nearest(efficient_volatilities, investor_risk)
print(investor_risk)

investor_portfolio = {
    'return': target_return[investor_index], 
    'volatility': investor_risk, 
    'sharpe': target_return[investor_index]/investor_risk, 
    'weights': efficient_portfolios[investor_index]['x'],
    'efficient-index': investor_index,
}

print(investor_portfolio)

## Plot

plt.figure(figsize=(12,8))
plt.scatter(features[:,1], features[:,0], c=features[:,2], cmap='BuGn', s=10)
plt.colorbar(label='Sharpe Ratio')
plt.xlabel('Volatility')
plt.ylabel('Return')
plt.scatter(portfolio_max_sharpe['volatility'], portfolio_max_sharpe['return'], marker='*', color='k', s=500, label='Maximum Sharpe ratio')
plt.scatter(portfolio_min_risk['volatility'], portfolio_min_risk['return'], marker='*', color='m', s=500, label='Minimum volatility')
plt.scatter(investor_portfolio['volatility'], investor_portfolio['return'], marker='*', color='b', s=500, label='Investor portfolio')
plt.legend(labelspacing=0.8)
plt.plot(efficient_volatilities, target_return, linestyle='-.', color='red', label='efficient frontier')
plt.title('Portfolio optimization')
plt.show()