# AnimalRelationships


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**breeds** | [**RelationshipData**](RelationshipData.md) |  | [optional] 
**colors** | [**RelationshipData**](RelationshipData.md) |  | [optional] 
**patterns** | [**RelationshipData**](RelationshipData.md) |  | [optional] 
**species** | [**RelationshipData**](RelationshipData.md) |  | [optional] 
**orgs** | [**RelationshipData**](RelationshipData.md) |  | [optional] 
**pictures** | [**RelationshipData**](RelationshipData.md) |  | [optional] 

## Example

```python
from rescuegroups_client.models.animal_relationships import AnimalRelationships

# TODO update the JSON string below
json = "{}"
# create an instance of AnimalRelationships from a JSON string
animal_relationships_instance = AnimalRelationships.from_json(json)
# print the JSON string representation of the object
print(AnimalRelationships.to_json())

# convert the object into a dict
animal_relationships_dict = animal_relationships_instance.to_dict()
# create an instance of AnimalRelationships from a dict
animal_relationships_from_dict = AnimalRelationships.from_dict(animal_relationships_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


