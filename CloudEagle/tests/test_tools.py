import pytest
from unittest.mock import AsyncMock, patch
from app.tools.rest_countries import RestCountriesClient, CountryNotFoundError, RestCountriesAPIError


@pytest.fixture
def rest_countries_client():
    """Create a REST Countries client instance."""
    return RestCountriesClient()


@pytest.fixture
def sample_country_data():
    """Sample country data for Germany."""
    return {
        "name": {
            "common": "Germany",
            "official": "Federal Republic of Germany"
        },
        "population": 83491249,
        "capital": ["Berlin"],
        "currencies": {
            "EUR": {
                "name": "euro",
                "symbol": "€"
            }
        },
        "languages": {
            "deu": "German"
        },
        "region": "Europe",
        "subregion": "Western Europe",
        "area": 357114.0,
        "borders": ["AUT", "BEL", "CZE", "DNK", "FRA", "LUX", "NLD", "POL", "CHE"],
        "timezones": ["UTC+01:00"],
        "continents": ["Europe"],
        "landlocked": False,
        "independent": True,
        "unMember": True,
        "tld": [".de"]
    }


@pytest.mark.asyncio
async def test_get_country_by_name_success(rest_countries_client, sample_country_data):
    """Test successful country data retrieval."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_country_data]
        mock_get.return_value = mock_response
        
        result = await rest_countries_client.get_country_by_name("Germany")
        
        assert result["name"]["common"] == "Germany"
        assert result["population"] == 83491249


@pytest.mark.asyncio
async def test_get_country_by_name_not_found(rest_countries_client):
    """Test country not found error."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        with pytest.raises(CountryNotFoundError):
            await rest_countries_client.get_country_by_name("Atlantis")


@pytest.mark.asyncio
async def test_get_country_by_name_rate_limit(rest_countries_client):
    """Test rate limit error."""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_get.return_value = mock_response
        
        with pytest.raises(RestCountriesAPIError, match="rate limit"):
            await rest_countries_client.get_country_by_name("Germany")


def test_extract_fields_population(rest_countries_client, sample_country_data):
    """Test extracting population field."""
    result = rest_countries_client.extract_fields(sample_country_data, ["population"])
    
    assert "population" in result
    assert result["population"] == 83491249


def test_extract_fields_capital(rest_countries_client, sample_country_data):
    """Test extracting capital field."""
    result = rest_countries_client.extract_fields(sample_country_data, ["capital"])
    
    assert "capital" in result
    assert result["capital"] == "Berlin"


def test_extract_fields_currency(rest_countries_client, sample_country_data):
    """Test extracting currency field."""
    result = rest_countries_client.extract_fields(sample_country_data, ["currency"])
    
    assert "currency" in result
    assert "euro" in result["currency"]
    assert "€" in result["currency"]


def test_extract_fields_languages(rest_countries_client, sample_country_data):
    """Test extracting languages field."""
    result = rest_countries_client.extract_fields(sample_country_data, ["languages"])
    
    assert "languages" in result
    assert result["languages"] == "German"


def test_extract_fields_multiple(rest_countries_client, sample_country_data):
    """Test extracting multiple fields."""
    result = rest_countries_client.extract_fields(
        sample_country_data,
        ["population", "capital", "currency"]
    )
    
    assert len(result) == 3
    assert "population" in result
    assert "capital" in result
    assert "currency" in result
