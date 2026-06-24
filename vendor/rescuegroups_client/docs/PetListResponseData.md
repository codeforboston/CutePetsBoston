# PetListResponseData


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | [optional] 
**type** | **str** |  | [optional] 
**attributes** | [**PetListResponseDataAttributes**](PetListResponseDataAttributes.md) |  | [optional] 

## Example

```python
from rescuegroups_client.models.pet_list_response_data import PetListResponseData

# TODO update the JSON string below
json = "{}"
# create an instance of PetListResponseData from a JSON string
pet_list_response_data_instance = PetListResponseData.from_json(json)
# print the JSON string representation of the object
print(PetListResponseData.to_json())

# convert the object into a dict
pet_list_response_data_dict = pet_list_response_data_instance.to_dict()
# create an instance of PetListResponseData from a dict
pet_list_response_data_from_dict = PetListResponseData.from_dict(pet_list_response_data_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


