# SpeciesListResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**data** | [**List[SpeciesItem]**](SpeciesItem.md) |  | [optional] 

## Example

```python
from rescuegroups_client.models.species_list_response import SpeciesListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of SpeciesListResponse from a JSON string
species_list_response_instance = SpeciesListResponse.from_json(json)
# print the JSON string representation of the object
print(SpeciesListResponse.to_json())

# convert the object into a dict
species_list_response_dict = species_list_response_instance.to_dict()
# create an instance of SpeciesListResponse from a dict
species_list_response_from_dict = SpeciesListResponse.from_dict(species_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


