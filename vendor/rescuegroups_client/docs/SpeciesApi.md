# rescuegroups_client.SpeciesApi

All URIs are relative to *https://api.rescuegroups.org/v5*

Method | HTTP request | Description
------------- | ------------- | -------------
[**list_animal_species**](SpeciesApi.md#list_animal_species) | **GET** /public/animals/species | List Animal Species


# **list_animal_species**
> SpeciesListResponse list_animal_species()

List Animal Species

Retrieve all animal species reference values.

### Example

* Api Key Authentication (apiKeyAuth):

```python
import rescuegroups_client
from rescuegroups_client.models.species_list_response import SpeciesListResponse
from rescuegroups_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://api.rescuegroups.org/v5
# See configuration.py for a list of all supported configuration parameters.
configuration = rescuegroups_client.Configuration(
    host = "https://api.rescuegroups.org/v5"
)

# The client must configure the authentication and authorization parameters
# in accordance with the API server security policy.
# Examples for each auth method are provided below, use the example that
# satisfies your auth use case.

# Configure API key authorization: apiKeyAuth
configuration.api_key['apiKeyAuth'] = os.environ["API_KEY"]

# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['apiKeyAuth'] = 'Bearer'

# Enter a context with an instance of the API client
with rescuegroups_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = rescuegroups_client.SpeciesApi(api_client)

    try:
        # List Animal Species
        api_response = api_instance.list_animal_species()
        print("The response of SpeciesApi->list_animal_species:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling SpeciesApi->list_animal_species: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

[**SpeciesListResponse**](SpeciesListResponse.md)

### Authorization

[apiKeyAuth](../README.md#apiKeyAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/vnd.api+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | A list of animal species. |  -  |
**401** | Missing or invalid authorization. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

