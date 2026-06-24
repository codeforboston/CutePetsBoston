# PetListResponseDataAttributes


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**keystring** | **str** |  | [optional] 
**name** | **str** |  | [optional] 

## Example

```python
from rescuegroups_client.models.pet_list_response_data_attributes import PetListResponseDataAttributes

# TODO update the JSON string below
json = "{}"
# create an instance of PetListResponseDataAttributes from a JSON string
pet_list_response_data_attributes_instance = PetListResponseDataAttributes.from_json(json)
# print the JSON string representation of the object
print(PetListResponseDataAttributes.to_json())

# convert the object into a dict
pet_list_response_data_attributes_dict = pet_list_response_data_attributes_instance.to_dict()
# create an instance of PetListResponseDataAttributes from a dict
pet_list_response_data_attributes_from_dict = PetListResponseDataAttributes.from_dict(pet_list_response_data_attributes_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


