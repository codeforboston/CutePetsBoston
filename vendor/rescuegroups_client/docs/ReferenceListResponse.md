# ReferenceListResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**meta** | [**ResponseMeta**](ResponseMeta.md) |  | [optional] 
**data** | [**List[ReferenceItem]**](ReferenceItem.md) |  | [optional] 

## Example

```python
from rescuegroups_client.models.reference_list_response import ReferenceListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of ReferenceListResponse from a JSON string
reference_list_response_instance = ReferenceListResponse.from_json(json)
# print the JSON string representation of the object
print(ReferenceListResponse.to_json())

# convert the object into a dict
reference_list_response_dict = reference_list_response_instance.to_dict()
# create an instance of ReferenceListResponse from a dict
reference_list_response_from_dict = ReferenceListResponse.from_dict(reference_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


