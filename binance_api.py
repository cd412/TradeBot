#!/usr/bin/env python

import time
import json
import urllib
import hmac, hashlib
import requests

from urllib.parse import urlparse, urlencode
from urllib.request import Request, urlopen

class Binance():

    methods = {
            #futures
            #'futuresExchangeInfo': {'url': 'fapi/v1/exchangeInfo', 'method': 'GET', 'private': False, 'futures': True},
            #'futuresKlines': {'url': 'fapi/v1/klines', 'method': 'GET', 'private': False, 'futures': True},
            #'MarkPrice': {'url': '/fapi/v1/premiumIndex', 'method': 'GET', 'private': False, 'futures': True},
            #'futuresCreateOrder':      {'url': 'fapi/v1/order', 'method': 'POST', 'private': True, 'futures': True},
            #'QueryOrder':      {'url': 'fapi/v1/order', 'method': 'GET', 'private': True, 'futures': True},
            #'ChangeLeverage': {'url': '/fapi/v1/leverage', 'method': 'POST', 'private':True, 'futures':True},
            'futuresAccount':      {'url': 'fapi/v2/account', 'method': 'GET', 'private': True, 'futures': True},
            #'futuresBalance':      {'url': 'fapi/v2/balance', 'method': 'GET', 'private': True, 'futures': True},
            #'futuresSymbolPriceTicker': {'url': 'fapi/v1/ticker/price', 'method': 'GET', 'private': True, 'futures': True},
            #'futuresOrderInfo': {'url': 'fapi/v1/order', 'method': 'GET', 'private': True, 'futures': True},
            #'futuresCancelOrder':      {'url': 'fapi/v1/order', 'method': 'DELETE', 'private': True, 'futures': True}
    }
    
    def __init__(self, API_KEY, API_SECRET):
        self.API_KEY = API_KEY
        self.API_SECRET = bytearray(API_SECRET, encoding='utf-8')
        self.shift_seconds = 0

    def __getattr__(self, name):
        def wrapper(*args, **kwargs):
            kwargs.update(command=name)
            return self.call_api(**kwargs)
        return wrapper

    def set_shift_seconds(self, seconds):
        self.shift_seconds = seconds
        
    def call_api(self, **kwargs):

        command = kwargs.pop('command')
        api_url = 'https://fapi.binance.com/' + self.methods[command]['url']
        #api_url = 'https://testnet.binancefuture.com:443/' + self.methods[command]['url']
        payload = kwargs
        headers = {}
        
        payload_str = urllib.parse.urlencode(payload)
        
        if self.methods[command]['private']:
            payload.update({'timestamp': int(time.time()*1000 + self.shift_seconds - 1)})
            payload_str = urllib.parse.urlencode(payload).encode('utf-8')
            sign = hmac.new(
                key=self.API_SECRET,
                msg=payload_str,
                digestmod=hashlib.sha256
            ).hexdigest()

            payload_str = payload_str.decode("utf-8") + "&signature="+str(sign) 
            headers = {"X-MBX-APIKEY": self.API_KEY}

        if self.methods[command]['method'] == 'GET':
            api_url += '?' + payload_str
        '''
        print(f"---------------------------------")
        print(f"self.methods[command]['method'] = {self.methods[command]['method']}")
        print(f"api_url = {api_url}")
        print(f"payload_str = {payload_str}")
        print(f"headers = {headers}")
        print(f"---------------------------------")
        '''
        response = requests.request(method=self.methods[command]['method'], url=api_url, data="" if self.methods[command]['method'] == 'GET' else payload_str, headers=headers)
        if 'code' in response.text:
            print(response.text)
        return response.json()

