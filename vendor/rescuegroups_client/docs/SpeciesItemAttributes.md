# SpeciesItemAttributes


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**singular** | **str** | Singular species name. | [optional] 
**plural** | **str** | Plural species name. | [optional] 
**young_singular** | **str** | Singular name for young of the species. | [optional] 
**young_plural** | **str** | Plural name for young of the species. | [optional] 

## Example

```python
from rescuegroups_client.models.species_item_attributes import SpeciesItemAttributes

# TODO update the JSON string below
json = "{}"
# create an instance of SpeciesItemAttributes from a JSON string
species_item_attributes_instance = SpeciesItemAttributes.from_json(json)
# print the JSON string representation of the object
print(SpeciesItemAttributes.to_json())

# convert the object into a dict
species_item_attributes_dict = species_item_attributes_instance.to_dict()
# create an instance of SpeciesItemAttributes from a dict
species_item_attributes_from_dict = SpeciesItemAttributes.from_dict(species_item_attributes_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


