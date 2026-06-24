# rescuegroups_client.PetListsApi

All URIs are relative to *https://api.rescuegroups.org/v5*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_pet_list**](PetListsApi.md#get_pet_list) | **GET** /public/petlists/{keystring} | Get Pet List
[**update_pet_list**](PetListsApi.md#update_pet_list) | **PUT** /public/petlists/{keystring} | Update Pet List


# **get_pet_list**
> PetListResponse get_pet_list(keystring)

Get Pet List

Retrieve a pet list by its keystring.

### Example

* Api Key Authentication (apiKeyAuth):

```python
import rescuegroups_client
from rescuegroups_client.models.pet_list_response import PetListResponse
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
    api_instance = rescuegroups_client.PetListsApi(api_client)
    keystring = 'keystring_example' # str | The pet list keystring identifier.

    try:
        # Get Pet List
        api_response = api_instance.get_pet_list(keystring)
        print("The response of PetListsApi->get_pet_list:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PetListsApi->get_pet_list: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **keystring** | **str**| The pet list keystring identifier. | 

### Return type

[**PetListResponse**](PetListResponse.md)

### Authorization

[apiKeyAuth](../README.md#apiKeyAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/vnd.api+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | A pet list. |  -  |
**401** | Missing or invalid authorization. |  -  |
**404** | Resource not found. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **update_pet_list**
> PetListResponse update_pet_list(keystring, pet_list_update_request=pet_list_update_request)

Update Pet List

Update a pet list by its keystring.

### Example

* Bearer Authentication (bearerAuth):

```python
import rescuegroups_client
from rescuegroups_client.models.pet_list_response import PetListResponse
from rescuegroups_client.models.pet_list_update_request import PetListUpdateRequest
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

# Configure Bearer authorization: bearerAuth
configuration = rescuegroups_client.Configuration(
    access_token = os.environ["BEARER_TOKEN"]
)

# Enter a context with an instance of the API client
with rescuegroups_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = rescuegroups_client.PetListsApi(api_client)
    keystring = 'keystring_example' # str | The pet list keystring identifier.
    pet_list_update_request = rescuegroups_client.PetListUpdateRequest() # PetListUpdateRequest |  (optional)

    try:
        # Update Pet List
        api_response = api_instance.update_pet_list(keystring, pet_list_update_request=pet_list_update_request)
        print("The response of PetListsApi->update_pet_list:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling PetListsApi->update_pet_list: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **keystring** | **str**| The pet list keystring identifier. | 
 **pet_list_update_request** | [**PetListUpdateRequest**](PetListUpdateRequest.md)|  | [optional] 

### Return type

[**PetListResponse**](PetListResponse.md)

### Authorization

[bearerAuth](../README.md#bearerAuth)

### HTTP request headers

 - **Content-Type**: application/vnd.api+json
 - **Accept**: application/vnd.api+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Updated pet list. |  -  |
**401** | Missing or invalid authorization. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

