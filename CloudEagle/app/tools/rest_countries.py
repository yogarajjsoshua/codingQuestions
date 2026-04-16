import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Dict, Any, List, Optional
import structlog
from cachetools import TTLCache
from datetime import timedelta

from app.config import settings

logger = structlog.get_logger()


class RestCountriesAPIError(Exception):
    """Custom exception for REST Countries API errors."""
    pass


class CountryNotFoundError(RestCountriesAPIError):
    """Exception raised when a country is not found."""
    pass


class RestCountriesClient:
    """Client for interacting with the REST Countries API."""
    
    def __init__(self):
        self.base_url = settings.rest_countries_base_url
        self.timeout = settings.api_timeout_seconds
        self.cache = TTLCache(
            maxsize=500,
            ttl=timedelta(hours=settings.cache_ttl_hours).total_seconds()
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def get_country_by_name(self, country_name: str) -> Dict[str, Any]:
        """
        Fetch country information by name.
        
        Args:
            country_name: Name of the country to fetch
            
        Returns:
            Dictionary containing country information
            
        Raises:
            CountryNotFoundError: If the country is not found
            RestCountriesAPIError: If there's an API error
        """
        cache_key = country_name.lower()
        if cache_key in self.cache:
            logger.info("cache_hit", country=country_name)
            return self.cache[cache_key]
        
        url = f"{self.base_url}/name/{country_name}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info("api_request", url=url, country=country_name)
                response = await client.get(url)
                
                if response.status_code == 404:
                    logger.warning("country_not_found", country=country_name)
                    raise CountryNotFoundError(f"Country '{country_name}' not found")
                
                if response.status_code == 429:
                    logger.error("rate_limit_exceeded", country=country_name)
                    raise RestCountriesAPIError("API rate limit exceeded. Please try again later.")
                
                if response.status_code >= 500:
                    logger.error("api_server_error", status_code=response.status_code)
                    raise RestCountriesAPIError(f"API server error: {response.status_code}")
                
                response.raise_for_status()
                data = response.json()
                
                if not data or not isinstance(data, list):
                    logger.error("malformed_response", data=data)
                    raise RestCountriesAPIError("Malformed API response")
                
                country_data = data[0]
                self.cache[cache_key] = country_data
                
                logger.info("api_success", country=country_name)
                return country_data
                
        except httpx.TimeoutException as e:
            logger.error("api_timeout", country=country_name, error=str(e))
            raise RestCountriesAPIError(f"Request timed out while fetching data for {country_name}")
        except httpx.NetworkError as e:
            logger.error("network_error", country=country_name, error=str(e))
            raise RestCountriesAPIError(f"Network error while fetching data for {country_name}")
        except httpx.HTTPStatusError as e:
            logger.error("http_error", country=country_name, status_code=e.response.status_code)
            raise RestCountriesAPIError(f"HTTP error: {e.response.status_code}")
    
    def extract_fields(self, country_data: Dict[str, Any], requested_fields: List[str]) -> Dict[str, Any]:
        """
        Extract specific fields from the country data.
        
        Args:
            country_data: Raw country data from API
            requested_fields: List of fields to extract
            
        Returns:
            Dictionary with extracted field values
        """
        extracted = {}
        
        for field in requested_fields:
            value = self._extract_field(country_data, field)
            if value is not None:
                extracted[field] = value
        
        return extracted
    
    def _extract_field(self, data: Dict[str, Any], field: str) -> Any:
        """
        Extract a specific field from country data.
        
        Args:
            data: Country data dictionary
            field: Field name to extract
            
        Returns:
            Extracted field value or None
        """
        field_mapping = {
            "population": lambda d: d.get("population"),
            "capital": lambda d: d.get("capital", [None])[0] if d.get("capital") else None,
            "currency": lambda d: self._extract_currency(d.get("currencies", {})),
            "currencies": lambda d: self._extract_currency(d.get("currencies", {})),
            "language": lambda d: self._extract_languages(d.get("languages", {})),
            "languages": lambda d: self._extract_languages(d.get("languages", {})),
            "region": lambda d: d.get("region"),
            "subregion": lambda d: d.get("subregion"),
            "area": lambda d: d.get("area"),
            "borders": lambda d: d.get("borders", []),
            "timezones": lambda d: d.get("timezones", []),
            "continents": lambda d: d.get("continents", []),
            "flag": lambda d: d.get("flag"),
            "maps": lambda d: d.get("maps", {}),
            "landlocked": lambda d: d.get("landlocked"),
            "independent": lambda d: d.get("independent"),
            "un_member": lambda d: d.get("unMember"),
            "tld": lambda d: d.get("tld", []),
            "official_name": lambda d: d.get("name", {}).get("official"),
            "common_name": lambda d: d.get("name", {}).get("common"),
        }
        
        extractor = field_mapping.get(field.lower())
        if extractor:
            try:
                return extractor(data)
            except Exception as e:
                logger.warning("field_extraction_error", field=field, error=str(e))
                return None
        
        return None
    
    def _extract_currency(self, currencies: Dict[str, Any]) -> Optional[str]:
        """Extract currency information."""
        if not currencies:
            return None
        
        currency_list = []
        for code, info in currencies.items():
            name = info.get("name", code)
            symbol = info.get("symbol", "")
            if symbol:
                currency_list.append(f"{name} ({symbol})")
            else:
                currency_list.append(name)
        
        return ", ".join(currency_list) if currency_list else None
    
    def _extract_languages(self, languages: Dict[str, str]) -> Optional[str]:
        """Extract language information."""
        if not languages:
            return None
        
        return ", ".join(languages.values())


rest_countries_client = RestCountriesClient()
