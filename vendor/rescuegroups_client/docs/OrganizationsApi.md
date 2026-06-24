# rescuegroups_client.OrganizationsApi

All URIs are relative to *https://api.rescuegroups.org/v5*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_public_org**](OrganizationsApi.md#get_public_org) | **GET** /public/orgs/{org_id} | Get Public Organization
[**list_public_orgs**](OrganizationsApi.md#list_public_orgs) | **GET** /public/orgs | List Public Organizations


# **get_public_org**
> OrgSingleResponse get_public_org(org_id)

Get Public Organization

Retrieve a single public rescue organization by ID.

### Example

* Api Key Authentication (apiKeyAuth):

```python
import rescuegroups_client
from rescuegroups_client.models.org_single_response import OrgSingleResponse
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
    api_instance = rescuegroups_client.OrganizationsApi(api_client)
    org_id = 'org_id_example' # str | The unique organization identifier.

    try:
        # Get Public Organization
        api_response = api_instance.get_public_org(org_id)
        print("The response of OrganizationsApi->get_public_org:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling OrganizationsApi->get_public_org: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **org_id** | **str**| The unique organization identifier. | 

### Return type

[**OrgSingleResponse**](OrgSingleResponse.md)

### Authorization

[apiKeyAuth](../README.md#apiKeyAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/vnd.api+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | A single organization record. |  -  |
**401** | Missing or invalid authorization. |  -  |
**404** | Resource not found. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_public_orgs**
> OrgListResponse list_public_orgs(page=page, limit=limit, sort=sort, fields=fields, include=include)

List Public Organizations

Retrieve a paginated list of public rescue organizations.

### Example

* Api Key Authentication (apiKeyAuth):

```python
import rescuegroups_client
from rescuegroups_client.models.org_list_response import OrgListResponse
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
    api_instance = rescuegroups_client.OrganizationsApi(api_client)
    page = 1 # int | Page number for paginated results. (optional) (default to 1)
    limit = 25 # int | Number of records per page (max 250). (optional) (default to 25)
    sort = 'sort_example' # str | Sort field with optional +/- prefix for direction. (optional)
    fields = ['fields_example'] # List[str] | Specific fields to return. (optional)
    include = ['include_example'] # List[str] | Related entities to include in the response. (optional)

    try:
        # List Public Organizations
        api_response = api_instance.list_public_orgs(page=page, limit=limit, sort=sort, fields=fields, include=include)
        print("The response of OrganizationsApi->list_public_orgs:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling OrganizationsApi->list_public_orgs: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **page** | **int**| Page number for paginated results. | [optional] [default to 1]
 **limit** | **int**| Number of records per page (max 250). | [optional] [default to 25]
 **sort** | **str**| Sort field with optional +/- prefix for direction. | [optional] 
 **fields** | [**List[str]**](str.md)| Specific fields to return. | [optional] 
 **include** | [**List[str]**](str.md)| Related entities to include in the response. | [optional] 

### Return type

[**OrgListResponse**](OrgListResponse.md)

### Authorization

[apiKeyAuth](../README.md#apiKeyAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/vnd.api+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | A paginated list of organizations. |  -  |
**401** | Missing or invalid authorization. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

