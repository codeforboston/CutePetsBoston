# OrgAttributes


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Organization name. | [optional] 
**type** | **str** | Organization type (rescue, shelter, etc.). | [optional] 
**email** | **str** | Contact email address. | [optional] 
**phone** | **str** | Contact phone number. | [optional] 
**street** | **str** | Street address. | [optional] 
**city** | **str** | City. | [optional] 
**state** | **str** | State or province. | [optional] 
**country** | **str** | Country. | [optional] 
**postalcode** | **str** | Postal code. | [optional] 
**url** | **str** | Organization website URL. | [optional] 
**adoption_url** | **str** | Adoption application URL. | [optional] 
**about** | **str** | Organization description. | [optional] 
**serve_areas** | **str** | Geographic areas the organization serves. | [optional] 
**facebook_url** | **str** | Facebook page URL. | [optional] 

## Example

```python
from rescuegroups_client.models.org_attributes import OrgAttributes

# TODO update the JSON string below
json = "{}"
# create an instance of OrgAttributes from a JSON string
org_attributes_instance = OrgAttributes.from_json(json)
# print the JSON string representation of the object
print(OrgAttributes.to_json())

# convert the object into a dict
org_attributes_dict = org_attributes_instance.to_dict()
# create an instance of OrgAttributes from a dict
org_attributes_from_dict = OrgAttributes.from_dict(org_attributes_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


