# AnimalSingleResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**data** | [**Animal**](Animal.md) |  | [optional] 
**included** | **List[object]** |  | [optional] 

## Example

```python
from rescuegroups_client.models.animal_single_response import AnimalSingleResponse

# TODO update the JSON string below
json = "{}"
# create an instance of AnimalSingleResponse from a JSON string
animal_single_response_instance = AnimalSingleResponse.from_json(json)
# print the JSON string representation of the object
print(AnimalSingleResponse.to_json())

# convert the object into a dict
animal_single_response_dict = animal_single_response_instance.to_dict()
# create an instance of AnimalSingleResponse from a dict
animal_single_response_from_dict = AnimalSingleResponse.from_dict(animal_single_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


