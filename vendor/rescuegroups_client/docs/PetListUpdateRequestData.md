# PetListUpdateRequestData


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | [optional] 
**id** | **str** |  | [optional] 
**attributes** | **Dict[str, object]** |  | [optional] 

## Example

```python
from rescuegroups_client.models.pet_list_update_request_data import PetListUpdateRequestData

# TODO update the JSON string below
json = "{}"
# create an instance of PetListUpdateRequestData from a JSON string
pet_list_update_request_data_instance = PetListUpdateRequestData.from_json(json)
# print the JSON string representation of the object
print(PetListUpdateRequestData.to_json())

# convert the object into a dict
pet_list_update_request_data_dict = pet_list_update_request_data_instance.to_dict()
# create an instance of PetListUpdateRequestData from a dict
pet_list_update_request_data_from_dict = PetListUpdateRequestData.from_dict(pet_list_update_request_data_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


