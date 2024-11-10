from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="geoapi")
location = geolocator.reverse("10.7718352, 106.6582976", language="en")  
print(location.address)
