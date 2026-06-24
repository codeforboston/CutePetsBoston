# rescuegroups_client.AnimalsApi

All URIs are relative to *https://api.rescuegroups.org/v5*

Method | HTTP request | Description
------------- | ------------- | -------------
[**get_public_animal**](AnimalsApi.md#get_public_animal) | **GET** /public/animals/{animal_id} | Get Public Animal
[**list_public_animals**](AnimalsApi.md#list_public_animals) | **GET** /public/animals | List Public Animals
[**search_public_animals**](AnimalsApi.md#search_public_animals) | **POST** /public/animals/search/{view_name} | Search Public Animals


# **get_public_animal**
> AnimalSingleResponse get_public_animal(animal_id, include=include)

Get Public Animal

Retrieve a single public adoptable animal by ID.

### Example

* Api Key Authentication (apiKeyAuth):

```python
import rescuegroups_client
from rescuegroups_client.models.animal_single_response import AnimalSingleResponse
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
    api_instance = rescuegroups_client.AnimalsApi(api_client)
    animal_id = 'animal_id_example' # str | The unique animal identifier.
    include = ['include_example'] # List[str] | Related entities to include in the response. (optional)

    try:
        # Get Public Animal
        api_response = api_instance.get_public_animal(animal_id, include=include)
        print("The response of AnimalsApi->get_public_animal:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AnimalsApi->get_public_animal: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **animal_id** | **str**| The unique animal identifier. | 
 **include** | [**List[str]**](str.md)| Related entities to include in the response. | [optional] 

### Return type

[**AnimalSingleResponse**](AnimalSingleResponse.md)

### Authorization

[apiKeyAuth](../README.md#apiKeyAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/vnd.api+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | A single animal record. |  -  |
**401** | Missing or invalid authorization. |  -  |
**404** | Resource not found. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **list_public_animals**
> AnimalListResponse list_public_animals(page=page, limit=limit, sort=sort, fields=fields, include=include)

List Public Animals

Retrieve a paginated list of public adoptable animals.

### Example

* Api Key Authentication (apiKeyAuth):

```python
import rescuegroups_client
from rescuegroups_client.models.animal_list_response import AnimalListResponse
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
    api_instance = rescuegroups_client.AnimalsApi(api_client)
    page = 1 # int | Page number for paginated results. (optional) (default to 1)
    limit = 25 # int | Number of records per page (max 250). (optional) (default to 25)
    sort = 'sort_example' # str | Sort field with optional +/- prefix for direction. (optional)
    fields = ['fields_example'] # List[str] | Specific fields to return. (optional)
    include = ['include_example'] # List[str] | Related entities to include in the response. (optional)

    try:
        # List Public Animals
        api_response = api_instance.list_public_animals(page=page, limit=limit, sort=sort, fields=fields, include=include)
        print("The response of AnimalsApi->list_public_animals:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AnimalsApi->list_public_animals: %s\n" % e)
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

[**AnimalListResponse**](AnimalListResponse.md)

### Authorization

[apiKeyAuth](../README.md#apiKeyAuth)

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/vnd.api+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | A paginated list of animals. |  -  |
**401** | Missing or invalid authorization. |  -  |
**429** | Rate limit exceeded. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **search_public_animals**
> AnimalListResponse search_public_animals(view_name, page=page, limit=limit, sort=sort, include=include, search_request=search_request)

Search Public Animals

Search public adoptable animals using filters, views, and geodistance. Predefined view names include: available, adopted, haspic, cats, dogs, rabbits, and species-specific variants.

### Example

* Api Key Authentication (apiKeyAuth):

```python
import rescuegroups_client
from rescuegroups_client.models.animal_list_response import AnimalListResponse
from rescuegroups_client.models.search_request import SearchRequest
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
    api_instance = rescuegroups_client.AnimalsApi(api_client)
    view_name = 'view_name_example' # str | Predefined view name (e.g., available, adopted, haspic, cats, dogs).
    page = 1 # int | Page number for paginated results. (optional) (default to 1)
    limit = 25 # int | Number of records per page (max 250). (optional) (default to 25)
    sort = 'sort_example' # str | Sort field with optional +/- prefix for direction. (optional)
    include = ['include_example'] # List[str] | Related entities to include in the response. (optional)
    search_request = rescuegroups_client.SearchRequest() # SearchRequest |  (optional)

    try:
        # Search Public Animals
        api_response = api_instance.search_public_animals(view_name, page=page, limit=limit, sort=sort, include=include, search_request=search_request)
        print("The response of AnimalsApi->search_public_animals:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling AnimalsApi->search_public_animals: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **view_name** | **str**| Predefined view name (e.g., available, adopted, haspic, cats, dogs). | 
 **page** | **int**| Page number for paginated results. | [optional] [default to 1]
 **limit** | **int**| Number of records per page (max 250). | [optional] [default to 25]
 **sort** | **str**| Sort field with optional +/- prefix for direction. | [optional] 
 **include** | [**List[str]**](str.md)| Related entities to include in the response. | [optional] 
 **search_request** | [**SearchRequest**](SearchRequest.md)|  | [optional] 

### Return type

[**AnimalListResponse**](AnimalListResponse.md)

### Authorization

[apiKeyAuth](../README.md#apiKeyAuth)

### HTTP request headers

 - **Content-Type**: application/vnd.api+json
 - **Accept**: application/vnd.api+json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Matching animals. |  -  |
**400** | Invalid request parameters. |  -  |
**401** | Missing or invalid authorization. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

