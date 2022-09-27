# -*- coding: utf-8 -*-
"""
Created on Sat Sep 24 21:08:53 2022

@author: abhi575
"""
# This is a program written horizontal analysis for financials for different companies.
# Below we will import all the necessary packages in order to fullfill our programs.

import requests
import time
import json
import pandas as pd
import numpy as np
import matplotlib_inline
import matplotlib.pyplot as plt
import matplotlib.ticker as tick


Api_Key = "364f92b5b633786f6936767ad6ff89b6f0193dff77af99df221b99d41d9ba2d1"

from sec_api import QueryApi # we need to import this in order to use the QueryApi function from the package

# Use the Above api key that you got at http://sec-api.io by registering with your email.
def Fetch_Filings_Quart(Api_Key):
    api_query = QueryApi(api_key = Api_Key)
    
    # Now run query to get all the 10-Q filings for Southwestern Airlines using ticker LUV
    query = {
        "query": {
            "query_string": {
                "query": "(formType:\"10-Q\") AND ticker:LUV"
            }
        },
        "from": "0",
        "size": "20",
        "sort": [{ "filedAt": { "order": "desc" } }]
    }
    
    result_quart = api_query.get_filings(query)
    
    accession_numbers = []
    
    # Now we will extract accession numbers for each filing
    for filing in result_quart['filings']:
        accession_numbers.append(filing['accessionNo'])
    return accession_numbers

# Above you got the api key at http://sec-api.io by registering with your email. 
def Fetch_Filings_Annual(Api_Key):
    api_query = QueryApi(api_key = Api_Key)
    
    # Now run query to get all the 10-K filings for Southwestern Airlines using ticker LUV
    query = {
        "query": {
            "query_string": {
                "query": "(formType:\"10-K\") AND ticker:LUV"
            }
        },
        "from": "0",
        "size": "3",
        "sort": [{ "filedAt": {"order": "desc"} }]        
    }
    
    result_annual = api_query.get_filings(query)
    
    accession_numbers = []
    
    # Now we will extract the accession numbers for each filing
    for filing in result_annual["filings"]:
        accession_numbers.append(filing['accessionNo'])
    return accession_numbers
# Below, to get the XBRL-JSON version of a filing, we define a helper function
# You can do this by providing its accession number.



def get_xbrl_json(accession_no, retry = 0):
    xbrl_converter_api_endpoint = "https://api.sec-api.io/xbrl-to-json" # This is the XBRL-to-JSON converter API endpoint
    requesting_url = xbrl_converter_api_endpoint + "?accession-no=" + accession_no + "&token=" + Api_Key
    
    # below is what you do in order to avoid reponse fails in case we send too many requests.
    # this is like a backoff strategy
        
    try:
        tmp_response = requests.get(requesting_url)
        xbrl_json = json.loads(tmp_response.text) # This helps load JSON into the memory
    except:
        if retry > 5:
            raise Exception('API Error')

# If response fails from sending too many requests, we have to wait 500 milliseconds
# below takes care of that wait time to retry the same request.
        time.sleep(0.5)
        return get_xbrl_json(accession_no, retry + 1)
    return xbrl_json

# Next lets convert the XBRL-JSON income statement into a pandas dataframe


def fetch_income_statement(xbrl_json):
    store_income_statement = {}
    
    # You have to iterate over each US GAAP item in the income statement
    
    for usGaapItem in xbrl_json['StatementsOfIncome']:
        values = []
        indicies = []
        
        for fact in xbrl_json['StatementsOfIncome'][usGaapItem]:
            # Only thing required to be considered is items without segment for our analysis
            if 'segment' not in fact:
                index = fact['period']['startDate'] + '-' + fact['period']['endDate']
            # Make sure no index duplicates are created below
                if index not in indicies:
                    values.append(fact['value'])
                    indicies.append(index)
                
        store_income_statement[usGaapItem] = pd.Series(values, index=indicies)
        
    Income_Statement = pd.DataFrame(store_income_statement)
    
    # You have to swtich columns and rows to where US GAAP items are Rows and Date range represents each Column header
    
    return Income_Statement.T

# Here below now we have to clean income statement
# You have to drop columns with +5 NaNs, drop key_0 column, and drop duplicate columns

def cleaning_income_statement(statement):
    for column in statement:
        
        # for column that has more than 5 NaN values
        NaN_Column = statement[column].isna().sum() > 5
        
        if column.endswith('_left') or column == 'key_0' or NaN_Column:
            statement = statement.drop(column, axis=1)
        
    # To make sure 1st column reprensets the 1st quarter, rearrange columns below
    Columns_Sorted = sorted(statement.columns.values, reverse = True)
    
    return statement[Columns_Sorted]

# Now we build our multi-year income statement. 
# Below we will iterate over all accession numbers, generate the XBRL-JSON version
# Create an income statement dataframe and merge the newly generated income statement with our global statement

def Main_Dataframe(accession_numbers):
    previous_income_statement_set = False
    income_statement_final = None
    income_statements = [x[0] for x in enumerate(accession_numbers)]
    for i, accession_no in enumerate(accession_numbers):
    # for accession_no in accession_nums this # doesn't work with filing fied before 2017 - Indicies aren't equal
        print(accession_no)
        
        # Below, now you fetch XBRL-JSON of 10-K filing by accession number
        xbrl_json_data = get_xbrl_json(accession_no)
        
        # Below now convert XBRL-JSON to a pandas dataframe
        Uncleaned_income_statement = fetch_income_statement(xbrl_json_data)
        
        # Below now we store the clean income statement
        Cleaned_income_statement = cleaning_income_statement(Uncleaned_income_statement)
        
        income_statements[i] = Cleaned_income_statement
        
    result = pd.concat(income_statements, axis=1, join="inner")
    result = result.loc[:,~result.columns.duplicated()].copy()
    return result

# Below is our Customized y axis formatter
def Dollars_Format(y, pos=None):
    return int(y/1000000000)

def plotting_variables(result):
    
    fig, ax = plt.subplots(1, 1, figsize =(10, 8))
    
    ax = result.astype(float)\
                             .loc["NetIncomeLoss"]\
                             .plot.line(legend=True)
    ax = result.astype(float)\
                             .loc["RevenueFromContractWithCustomerExcludingAssessedTax"]\
                             .plot.line()
    ax.legend(['Net Income(in Billion USD', 'Revenue(in Billion USD'])
    ax.set_title('Quaterly Revenues & Net Income')
    
    ax.yaxis.set_major_formatter(tick.FuncFormatter(Dollars_Format))
    
    plt.ylabel('in $ Billions')
    
    # This below shows all quarter date ranges
    plt.xticks(ticks=np.arange(len(result.columns)),
           labels=result.columns)
    
    # Below we will format the x-axis
    fig.autofmt_xdate()
    
    plt.show()
    
def Horizontal_Analysis(Api_Key):
    accession_numbers = Fetch_Filings_Annual(Api_Key)
    result= Main_Dataframe(accession_numbers)
    plotting_variables(result)
    
Horizontal_Analysis(Api_Key)

                   
    
        
    
        
    
    
    
    
            
        
        
    

    

            


    

    