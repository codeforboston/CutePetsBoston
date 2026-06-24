# rescuegroups_client.PatternsApi

All URIs are relative to *https://api.rescuegroups.org/v5*

Method | HTTP request | Description
------------- | ------------- | -------------
[**list_animal_patterns**](PatternsApi.md#list_animal_patterns) | **GET** /public/animals/patterns | List Animal Patterns


# **list_animal_patterns**
> ReferenceListResponse list_animal_patterns()

List Animal Patterns

Retrieve all animal pattern reference values.

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
    api_instance = rescuegroups_client.PatternsApi(api_client)

    try:
        # List Animal Patterns
        api_response = api_instance.list_animal_patterns()
        print("The response of PatternsApi->list_animal_patterns:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PatternsApi->list_animal_patterns: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

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
**200** | A list of animal patterns. |  -  |
**401** | Missing or invalid authorization. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

