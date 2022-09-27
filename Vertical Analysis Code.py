# -*- coding: utf-8 -*-
"""
Created on Tue Sep 27 17:00:54 2022

@author: abhi575
"""

# Vertical Analysis Report

# URL for 10-Q filing of SouthWest Airlines
import pandas as pd
import requests
import json
from IPython.display import display, HTML

def Filings_Quarterly(Api_Key):
    url_filing = "https://www.sec.gov/ix?doc=/Archives/edgar/data/0000092380/000009238021000101/luv-20210331.htm"

    # Here we again use the XBRL-to-JSON converter API endpoint
    xbrl_converter_api_endpoint = "https://api.sec-api.io/xbrl-to-json"

    url_final = xbrl_converter_api_endpoint + "?htm-url=" + url_filing + "&token=" + Api_Key

    # Below, you have to make request to the API
    response = requests.get(url_final)

    # now we use the load JSON into memory using the function json.loads
    xbrl_json = json.loads(response.text)

    return xbrl_json

# Now below we have to convert XBRL-JSON of income statement to pandas dataframe
def fetch_income_statement(xbrl_json):
    store_income_statement = {}

    # Now lets iterate over each US GAAP item in the income statement
    for usGaapItem in xbrl_json['StatementsOfComprehensiveIncome']:
        Values = []
        Indicies = []

        for fact in xbrl_json['StatementsOfComprehensiveIncome'][usGaapItem]:
            # Only thing required to be considered is items without segment for our analysis
            if 'segment' not in fact:
                index = fact['period']['startDate'] + '-' + fact['period']['endDate']
                # ensure no index duplicates are created
                if index not in Indicies:
                    Values.append(fact['value'])
                    Indicies.append(index)                    

        store_income_statement[usGaapItem] = pd.Series(Values, index=Indicies) 

    income_statement = pd.DataFrame(store_income_statement)
    # You have to swtich columns and rows to where US GAAP items are Rows and Date range represents each Column header
    return income_statement.T 
# get your API key at https://sec-api.io
Api_Key = "364f92b5b633786f6936767ad6ff89b6f0193dff77af99df221b99d41d9ba2d1"

def vertical_analysis(Api_Key):
    xbrl_json = Filings_Quarterly(Api_Key)
    income_statement = fetch_income_statement(xbrl_json)
    income_statement = income_statement[:-5]
    income_statement = income_statement.apply(pd.to_numeric)
    vertical_analysis = income_statement.divide(income_statement.iloc[0]/100)
    return vertical_analysis

vertical_analysis(Api_Key)
