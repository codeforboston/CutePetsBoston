# SearchRequestData


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**filters** | [**List[SearchFilter]**](SearchFilter.md) |  | [optional] 
**filter_processing** | **str** | Boolean expression for filter combination. | [optional] 
**geodistance** | [**GeoDistance**](GeoDistance.md) |  | [optional] 

## Example

```python
from rescuegroups_client.models.search_request_data import SearchRequestData

# TODO update the JSON string below
json = "{}"
# create an instance of SearchRequestData from a JSON string
search_request_data_instance = SearchRequestData.from_json(json)
# print the JSON string representation of the object
print(SearchRequestData.to_json())

# convert the object into a dict
search_request_data_dict = search_request_data_instance.to_dict()
# create an instance of SearchRequestData from a dict
search_request_data_from_dict = SearchRequestData.from_dict(search_request_data_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


