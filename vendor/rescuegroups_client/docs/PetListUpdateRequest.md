# PetListUpdateRequest


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**data** | [**PetListUpdateRequestData**](PetListUpdateRequestData.md) |  | [optional] 

## Example

```python
from rescuegroups_client.models.pet_list_update_request import PetListUpdateRequest

# TODO update the JSON string below
json = "{}"
# create an instance of PetListUpdateRequest from a JSON string
pet_list_update_request_instance = PetListUpdateRequest.from_json(json)
# print the JSON string representation of the object
print(PetListUpdateRequest.to_json())

# convert the object into a dict
pet_list_update_request_dict = pet_list_update_request_instance.to_dict()
# create an instance of PetListUpdateRequest from a dict
pet_list_update_request_from_dict = PetListUpdateRequest.from_dict(pet_list_update_request_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


