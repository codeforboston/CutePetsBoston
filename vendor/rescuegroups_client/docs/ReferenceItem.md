# ReferenceItem


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | [optional] 
**type** | **str** |  | [optional] 
**attributes** | [**ReferenceItemAttributes**](ReferenceItemAttributes.md) |  | [optional] 

## Example

```python
from rescuegroups_client.models.reference_item import ReferenceItem

# TODO update the JSON string below
json = "{}"
# create an instance of ReferenceItem from a JSON string
reference_item_instance = ReferenceItem.from_json(json)
# print the JSON string representation of the object
print(ReferenceItem.to_json())

# convert the object into a dict
reference_item_dict = reference_item_instance.to_dict()
# create an instance of ReferenceItem from a dict
reference_item_from_dict = ReferenceItem.from_dict(reference_item_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


