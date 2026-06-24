# rescuegroups_client.AuthenticationApi

All URIs are relative to *https://api.rescuegroups.org/v5*

Method | HTTP request | Description
------------- | ------------- | -------------
[**create_token**](AuthenticationApi.md#create_token) | **POST** /tokens | Create Authentication Token


# **create_token**
> TokenResponse create_token(token_request=token_request)

Create Authentication Token

Obtain a bearer token for authenticated (private data) access.

### Example


```python
import rescuegroups_client
from rescuegroups_client.models.token_request import TokenRequest
from rescuegroups_client.models.token_response import TokenResponse
from rescuegroups_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to https://api.rescuegroups.org/v5
# See configuration.py for a list of all supported configuration parameters.
configuration = rescuegroups_client.Configuration(
    host = "https://api.rescuegroups.org/v5"
)


# Enter a context with an instance of the API client
with rescuegroups_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = rescuegroups_client.AuthenticationApi(api_client)
    token_request = rescuegroups_client.TokenRequest() # TokenRequest |  (optional)

    try:
        # Create Authentication Token
        api_response = api_instance.create_token(token_request=token_request)
        print("The response of AuthenticationApi->create_token:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AuthenticationApi->create_token: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **token_request** | [**TokenRequest**](TokenRequest.md)|  | [optional] 

### Return type

[**TokenResponse**](TokenResponse.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: application/vnd.api+json
 - **Accept**: application/vnd.api+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**201** | Token created successfully. |  -  |
**400** | Invalid request parameters. |  -  |
**401** | Missing or invalid authorization. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

