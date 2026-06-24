# rescuegroups_client.BreedsApi

All URIs are relative to *https://api.rescuegroups.org/v5*

Method | HTTP request | Description
------------- | ------------- | -------------
[**list_animal_breeds**](BreedsApi.md#list_animal_breeds) | **GET** /public/animals/breeds | List Animal Breeds


# **list_animal_breeds**
> ReferenceListResponse list_animal_breeds(page=page, limit=limit)

List Animal Breeds

Retrieve all animal breed reference values.

### Example

* Api Key Authentication (apiKeyAuth):

```python
import rescuegroups_client
from rescuegroups_client.models.reference_list_response import ReferenceListResponse
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
    api_instance = rescuegroups_client.BreedsApi(api_client)
    page = 1 # int | Page number for paginated results. (optional) (default to 1)
    limit = 25 # int | Number of records per page (max 250). (optional) (default to 25)

    try:
        # List Animal Breeds
        api_response = api_instance.list_animal_breeds(page=page, limit=limit)
        print("The response of BreedsApi->list_animal_breeds:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling BreedsApi->list_animal_breeds: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **page** | **int**| Page number for paginated results. | [optional] [default to 1]
 **limit** | **int**| Number of records per page (max 250). | [optional] [default to 25]

### Return type

[**ReferenceListResponse**](ReferenceListResponse.md)

### Authorization

[apiKeyAuth](../README.md#apiKeyAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/vnd.api+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | A list of animal breeds. |  -  |
**401** | Missing or invalid authorization. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

