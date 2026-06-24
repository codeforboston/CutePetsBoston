# SpeciesItem


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | [optional] 
**type** | **str** |  | [optional] 
**attributes** | [**SpeciesItemAttributes**](SpeciesItemAttributes.md) |  | [optional] 

## Example

```python
from rescuegroups_client.models.species_item import SpeciesItem

# TODO update the JSON string below
json = "{}"
# create an instance of SpeciesItem from a JSON string
species_item_instance = SpeciesItem.from_json(json)
# print the JSON string representation of the object
print(SpeciesItem.to_json())

# convert the object into a dict
species_item_dict = species_item_instance.to_dict()
# create an instance of SpeciesItem from a dict
species_item_from_dict = SpeciesItem.from_dict(species_item_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


