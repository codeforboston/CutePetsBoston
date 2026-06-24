# OrgListResponse


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**meta** | [**ResponseMeta**](ResponseMeta.md) |  | [optional] 
**data** | [**List[Organization]**](Organization.md) |  | [optional] 

## Example

```python
from rescuegroups_client.models.org_list_response import OrgListResponse

# TODO update the JSON string below
json = "{}"
# create an instance of OrgListResponse from a JSON string
org_list_response_instance = OrgListResponse.from_json(json)
# print the JSON string representation of the object
print(OrgListResponse.to_json())

# convert the object into a dict
org_list_response_dict = org_list_response_instance.to_dict()
# create an instance of OrgListResponse from a dict
org_list_response_from_dict = OrgListResponse.from_dict(org_list_response_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


