# TokenResponseDataAttributes


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**token** | **str** | Bearer authentication token. | [optional] 
**expiration** | **datetime** | Token expiration timestamp. | [optional] 

## Example

```python
from rescuegroups_client.models.token_response_data_attributes import TokenResponseDataAttributes

# TODO update the JSON string below
json = "{}"
# create an instance of TokenResponseDataAttributes from a JSON string
token_response_data_attributes_instance = TokenResponseDataAttributes.from_json(json)
# print the JSON string representation of the object
print(TokenResponseDataAttributes.to_json())

# convert the object into a dict
token_response_data_attributes_dict = token_response_data_attributes_instance.to_dict()
# create an instance of TokenResponseDataAttributes from a dict
token_response_data_attributes_from_dict = TokenResponseDataAttributes.from_dict(token_response_data_attributes_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


