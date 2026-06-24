# PetListResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**data** | [**PetListResponseData**](PetListResponseData.md) |  | [optional] 

## Example

```python
from rescuegroups_client.models.pet_list_response import PetListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of PetListResponse from a JSON string
pet_list_response_instance = PetListResponse.from_json(json)
# print the JSON string representation of the object
print(PetListResponse.to_json())

# convert the object into a dict
pet_list_response_dict = pet_list_response_instance.to_dict()
# create an instance of PetListResponse from a dict
pet_list_response_from_dict = PetListResponse.from_dict(pet_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


