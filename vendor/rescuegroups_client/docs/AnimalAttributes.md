# AnimalAttributes


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**name** | **str** | Animal name. | [optional] 
**birth_date** | **date** | Animal birth date. | [optional] 
**sex** | **str** | Animal sex. | [optional] 
**age_group** | **str** | Age group category. | [optional] 
**size_group** | **str** | Size group category. | [optional] 
**is_adoption_pending** | **bool** | Whether adoption is pending. | [optional] 
**is_altered** | **bool** | Whether the animal is spayed/neutered. | [optional] 
**picture_count** | **int** | Number of pictures available. | [optional] 
**video_count** | **int** | Number of videos available. | [optional] 
**adopted_date** | **date** | Date the animal was adopted. | [optional] 
**special_needs_details** | **str** | Description of any special needs. | [optional] 
**description_text** | **str** | Plain text description of the animal. | [optional] 
**location_citystate** | **str** | City and state where the animal is located. | [optional] 
**location_state** | **str** | State where the animal is located. | [optional] 
**location_distance** | **float** | Distance from search location. | [optional] 
**rescue_id** | **str** | External rescue ID. | [optional] 
**url** | **str** | URL of the animal profile page. | [optional] 

## Example

```python
from rescuegroups_client.models.animal_attributes import AnimalAttributes

# TODO update the JSON string below
json = "{}"
# create an instance of AnimalAttributes from a JSON string
animal_attributes_instance = AnimalAttributes.from_json(json)
# print the JSON string representation of the object
print(AnimalAttributes.to_json())

# convert the object into a dict
animal_attributes_dict = animal_attributes_instance.to_dict()
# create an instance of AnimalAttributes from a dict
animal_attributes_from_dict = AnimalAttributes.from_dict(animal_attributes_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


