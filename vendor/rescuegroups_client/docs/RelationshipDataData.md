# RelationshipDataData


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**type** | **str** |  | [optional] 
**id** | **str** |  | [optional] 

## Example

```python
from rescuegroups_client.models.relationship_data_data import RelationshipDataData

# TODO update the JSON string below
json = "{}"
# create an instance of RelationshipDataData from a JSON string
relationship_data_data_instance = RelationshipDataData.from_json(json)
# print the JSON string representation of the object
print(RelationshipDataData.to_json())

# convert the object into a dict
relationship_data_data_dict = relationship_data_data_instance.to_dict()
# create an instance of RelationshipDataData from a dict
relationship_data_data_from_dict = RelationshipDataData.from_dict(relationship_data_data_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


