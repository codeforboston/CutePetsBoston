# GeoDistance


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**postalcode** | **str** | Postal code for distance search. | [optional] 
**lat** | **float** | Latitude for coordinate-based search. | [optional] 
**lon** | **float** | Longitude for coordinate-based search. | [optional] 
**miles** | **int** | Search radius in miles. | [optional] 
**kilometers** | **int** | Search radius in kilometers. | [optional] 

## Example

```python
from rescuegroups_client.models.geo_distance import GeoDistance

# TODO update the JSON string below
json = "{}"
# create an instance of GeoDistance from a JSON string
geo_distance_instance = GeoDistance.from_json(json)
# print the JSON string representation of the object
print(GeoDistance.to_json())

# convert the object into a dict
geo_distance_dict = geo_distance_instance.to_dict()
# create an instance of GeoDistance from a dict
geo_distance_from_dict = GeoDistance.from_dict(geo_distance_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


