# TokenResponseData


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** | Token ID. | [optional] 
**attributes** | [**TokenResponseDataAttributes**](TokenResponseDataAttributes.md) |  | [optional] 

## Example

```python
from rescuegroups_client.models.token_response_data import TokenResponseData

# TODO update the JSON string below
json = "{}"
# create an instance of TokenResponseData from a JSON string
token_response_data_instance = TokenResponseData.from_json(json)
# print the JSON string representation of the object
print(TokenResponseData.to_json())

# convert the object into a dict
token_response_data_dict = token_response_data_instance.to_dict()
# create an instance of TokenResponseData from a dict
token_response_data_from_dict = TokenResponseData.from_dict(token_response_data_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


