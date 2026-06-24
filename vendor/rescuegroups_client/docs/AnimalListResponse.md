# AnimalListResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**meta** | [**ResponseMeta**](ResponseMeta.md) |  | [optional] 
**data** | [**List[Animal]**](Animal.md) |  | [optional] 
**included** | **List[object]** |  | [optional] 

## Example

```python
from rescuegroups_client.models.animal_list_response import AnimalListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of AnimalListResponse from a JSON string
animal_list_response_instance = AnimalListResponse.from_json(json)
# print the JSON string representation of the object
print(AnimalListResponse.to_json())

# convert the object into a dict
animal_list_response_dict = animal_list_response_instance.to_dict()
# create an instance of AnimalListResponse from a dict
animal_list_response_from_dict = AnimalListResponse.from_dict(animal_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


