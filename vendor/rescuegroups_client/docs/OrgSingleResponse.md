# OrgSingleResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**data** | [**Organization**](Organization.md) |  | [optional] 

## Example

```python
from rescuegroups_client.models.org_single_response import OrgSingleResponse

# TODO update the JSON string below
json = "{}"
# create an instance of OrgSingleResponse from a JSON string
org_single_response_instance = OrgSingleResponse.from_json(json)
# print the JSON string representation of the object
print(OrgSingleResponse.to_json())

# convert the object into a dict
org_single_response_dict = org_single_response_instance.to_dict()
# create an instance of OrgSingleResponse from a dict
org_single_response_from_dict = OrgSingleResponse.from_dict(org_single_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


