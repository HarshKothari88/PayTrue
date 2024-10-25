import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from functools import lru_cache, wraps
import os
import time

def ttl_cache(maxsize=128, ttl=300):
    """
    Decorator that creates a cache with time-based expiration.
    
    Args:
        maxsize (int): Maximum size of the cache
        ttl (int): Time to live in seconds
    """
    def decorator(func):
        cache = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            current_time = time.time()
            
            # Check if key exists and hasn't expired
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < ttl:
                    return result
                else:
                    del cache[key]
            
            # If cache is full, remove oldest item
            if len(cache) >= maxsize:
                oldest_key = min(cache.keys(), key=lambda k: cache[k][1])
                del cache[oldest_key]
            
            # Calculate new value and store in cache
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            return result
            
        return wrapper
    return decorator

class CurrencyAPIClient:
    """
    Client for interacting with Free Currency API
    Documentation: https://freecurrencyapi.com/docs/
    """
    def __init__(self):
        self.base_url = "https://api.freecurrencyapi.com/v1"
        self.api_key = os.getenv('CURRENCY_API_KEY')
        if not self.api_key:
            raise ValueError("Please set CURRENCY_API_KEY environment variable")

    @ttl_cache(maxsize=1, ttl=3600)  # Cache for 1 hour
    def get_supported_currencies(self) -> Dict:
        """Get list of supported currencies and their details."""
        endpoint = f"{self.base_url}/currencies"
        params = {
            "apikey": self.api_key
        }
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()['data']
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch supported currencies: {str(e)}")

    def get_current_rates(self, base_currency: str, target_currencies: List[str]) -> Dict:
        """
        Get current exchange rates for specified currencies.
        
        Args:
            base_currency: The base currency code (e.g., 'USD')
            target_currencies: List of currency codes to get rates for
            
        Returns:
            Dictionary of currency rates
        """
        endpoint = f"{self.base_url}/latest"
        params = {
            "apikey": self.api_key,
            "currencies": ",".join(target_currencies)
        }
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()['data']
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch current rates: {str(e)}")

    def get_historical_rates(
        self,
        target_currencies: List[str],
        days: int = 30
    ) -> Dict:
        """Get historical exchange rates for the past n days."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        endpoint = f"{self.base_url}/historical"
        params = {
            "apikey": self.api_key,
            "currencies": ",".join(target_currencies),
            "date_from": start_date.strftime("%Y-%m-%d"),
            "date_to": end_date.strftime("%Y-%m-%d")
        }
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()['data']
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch historical rates: {str(e)}")

@dataclass
class CurrencyInfo:
    symbol: str
    name: str
    symbol_native: str
    decimal_digits: int
    rounding: int
    code: str
    name_plural: str

@dataclass
class MoneyChanger:
    id: str
    name: str
    location: str
    rating: float
    markup_percentage: float
    operating_hours: Dict[str, str]
    supported_currencies: List[str]

class ExchangeRateService:
    def __init__(self):
        self.api_client = CurrencyAPIClient()
        self.money_changers: List[MoneyChanger] = []
        self.currencies: Dict[str, CurrencyInfo] = {}
        self._load_money_changers()
        self._load_currencies()

    def _load_currencies(self):
        """Load and cache supported currencies."""
        try:
            currency_data = self.api_client.get_supported_currencies()
            self.currencies = {
                code: CurrencyInfo(
                    symbol=data['symbol'],
                    name=data['name'],
                    symbol_native=data['symbol_native'],
                    decimal_digits=data['decimal_digits'],
                    rounding=data['rounding'],
                    code=data['code'],
                    name_plural=data['name_plural']
                )
                for code, data in currency_data.items()
            }
        except Exception as e:
            print(f"Warning: Failed to load currencies: {str(e)}")
            self.currencies = {}

    def _load_money_changers(self):
        """Load money changer data from configuration."""
        self.money_changers = [
            MoneyChanger(
                id="mc1",
                name="Global Exchange",
                location="Airport Terminal 1",
                rating=4.5,
                markup_percentage=2.5,
                operating_hours={
                    "weekday": "09:00-21:00",
                    "weekend": "10:00-20:00"
                },
                supported_currencies=["USD", "EUR", "GBP", "JPY", "AUD"]
            ),
            MoneyChanger(
                id="mc2",
                name="City Forex",
                location="Downtown",
                rating=4.3,
                markup_percentage=2.0,
                operating_hours={
                    "weekday": "09:00-18:00",
                    "weekend": "10:00-16:00"
                },
                supported_currencies=["USD", "EUR", "GBP", "SGD", "CHF"]
            )
        ]

    def get_best_rates(
        self,
        from_currency: str,
        to_currency: str,
        amount: float
    ) -> List[Dict]:
        """Get current rates from all money changers."""
        try:
            # Validate currencies
            if from_currency not in self.currencies or to_currency not in self.currencies:
                raise ValueError("Invalid currency code")

            # Get current rates for the currency pair
            rates = self.api_client.get_current_rates(
                base_currency=from_currency,
                target_currencies=[to_currency]
            )
            
            base_rate = rates[to_currency]
            
            # Calculate rates for each money changer
            changer_rates = []
            for changer in self.money_changers:
                # Check if money changer supports both currencies
                if from_currency in changer.supported_currencies and \
                   to_currency in changer.supported_currencies:
                    
                    # Apply money changer's markup
                    rate = base_rate * (1 + changer.markup_percentage / 100)
                    converted_amount = amount * rate
                    
                    # Format according to currency's decimal digits
                    decimal_digits = self.currencies[to_currency].decimal_digits
                    
                    changer_rates.append({
                        'money_changer': changer.name,
                        'location': changer.location,
                        'rate': round(rate, decimal_digits),
                        'converted_amount': round(converted_amount, decimal_digits),
                        'markup_percentage': changer.markup_percentage,
                        'from_currency': {
                            'code': from_currency,
                            'symbol': self.currencies[from_currency].symbol
                        },
                        'to_currency': {
                            'code': to_currency,
                            'symbol': self.currencies[to_currency].symbol
                        },
                        'operating_hours': changer.operating_hours
                    })
            
            # Sort by rate (best to worst)
            changer_rates.sort(key=lambda x: x['rate'])
            
            # Calculate savings compared to highest rate
            if changer_rates:
                highest_amount = max(r['converted_amount'] for r in changer_rates)
                for rate_info in changer_rates:
                    rate_info['savings_vs_highest'] = round(
                        highest_amount - rate_info['converted_amount'],
                        self.currencies[to_currency].decimal_digits
                    )
            
            return changer_rates

        except Exception as e:
            raise Exception(f"Failed to get exchange rates: {str(e)}")

def example_usage():
    """Example of how to use the ExchangeRateService."""
    # Initialize service
    service = ExchangeRateService()
    
    try:
        # Get best rates for exchanging 1000 USD to EUR
        rates = service.get_best_rates('USD', 'EUR', 1000)
        
        print("\nCurrent Exchange Rates:")
        for rate_info in rates:
            print(f"\n{rate_info['money_changer']} ({rate_info['location']}):")
            print(f"Rate: {rate_info['from_currency']['symbol']}1 = "
                  f"{rate_info['to_currency']['symbol']}{rate_info['rate']}")
            print(f"Converted Amount: {rate_info['to_currency']['symbol']}"
                  f"{rate_info['converted_amount']}")
            print(f"Potential savings: {rate_info['to_currency']['symbol']}"
                  f"{rate_info['savings_vs_highest']}")
            print(f"Operating Hours:")
            for day_type, hours in rate_info['operating_hours'].items():
                print(f"  {day_type}: {hours}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    example_usage()