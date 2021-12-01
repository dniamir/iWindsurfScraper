"""Simple class to read iWindsurf data and return as a dataframe:

This code simply returns the average windspeed for a given location based
on the pro forecast report

The data itself isn't stored on the iWindsurf website.  When the website is
loaded, a call to an external API is made. This class reads the external page.

This includes data that is behind the iWindsurf paywall.

Currently there's no functionality to change the number of datapoints returned
or other options. However if you modify the URL link, this is fairly easy.

"""
from bs4 import BeautifulSoup as bs
import json
import numpy as np
import matplotlib.pyplot as plt
import datetime
import pandas as pd
import requests


class iWindsurfScraper(object):
	"""Simple class to record and save data from iWindsurf

	Data is saved as a class variable. The highest level in this dictionary is the
	region name. The next level down is also a dictionary with all recently saved
	data"""
	USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
	LANGUAGE = "en-US,en;q=0.5"
	URL = "https://services.surfline.com/kbyg/spots/forecasts/wave?spotId=_ENTER_SPOT_ID_HERE_&days=6&intervalHours=1&maxHeights=false&sds=false"
	DOTW = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
	        'Sunday']
	
	LOCATION_LOOKUP = {'3Rd Ave Channel': 1374,
	                   'Anita Rock-Crissy Field': 411,
	                   'Palo Alto': 425,
	                   'Coyote Point': 408}
	
	def __init__(self):
		self.data = None

	def GetData(self, location):
		"""Read the online iWindsurf data and return data as a dataframe

		Args:
			location: String. Either the iWindsurf location code associated with the
				location of interest, or the location name itself as long as it's been
				pre-recorded in the class location lookup dictionary.

		Outputs:
			df_wind: DataFrame. Dataframe with wind speed and timestamps.
		"""
		USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
		LANGUAGE = "en-US,en;q=0.5"
		
		# Location
		spot_id = self.LOCATION_LOOKUP[location.title()]
		
		# Pro Model Forecast
		# URL = 'https://api.weatherflow.com/wxengine/rest/model/getModelDataBySpot?callback=jQuery17204981289850784012_1608525296698&units_wind=mph&units_temp=f&units_distance=mi&spot_id=%i&model_id=211&wf_token=b9f5e47c00d17fce97f3391d9c5ab285&_=1608525296891' % spot_id
		URL = 'https://api.weatherflow.com/wxengine/rest/model/getModelDataBySpot?callback=jQuery17201072160731006555_1621113757475&units_wind=mph&units_temp=f&units_distance=mi&spot_id=%i&model_id=211&wf_token=ded29f84c9d0aabe36aef4f0170ca838&_=1621113758210' % spot_id
		# Quicklook
		# URL = 'https://api.weatherflow.com/wxengine/rest/model/getModelDataBySpot?callback=jQuery17204981289850784012_1608525296697&units_wind=mph&units_temp=f&units_distance=mi&spot_id=1374&model_id=-1&wf_token=b9f5e47c00d17fce97f3391d9c5ab285&_=1608525296884'
		
		# Pro Forecast
		# URL = "https://api.weatherflow.com/wxengine/rest/forecast/getOperationalForecast?callback=jQuery17206385514518878679_1608524974156&wf_token=b9f5e47c00d17fce97f3391d9c5ab285&forecast_id=2&_=1608524975003"
		
		# Update URL
		url_region = '%s' % (URL)
		
		# Read data from URL
		session = requests.Session()
		session.headers['User-Agent'] = USER_AGENT
		session.headers['Accept-Language'] = LANGUAGE
		session.headers['Content-Language'] = LANGUAGE
		html = session.get(url_region)
		soup = bs(html.text, "html.parser")
		soup_text = soup.text
		
		start_idx = soup_text.index('{')
		end_idx = soup_text.rfind('}') + 1
		wind_dict = json.loads(soup_text[start_idx:end_idx])
		
		df_wind = self.OrganizeData(wind_dict)
		
		if self.data is None:
			self.data = df_wind
		else:
			self.data.append(df_wind)
			self.data.drop_duplicates(subset=['Location', 'DateTime'],
			                          keep='last',
			                          inplace=True,
			                          ignore_index=True)
		
		return df_wind
		
	def OrganizeData(self, wind_dict):
		"""Read in json file information from the iWindsurf website and parse it

		Args:
			wind_dict: Dictionary. Dictonary format of the json read from the
				iWindsurf website with data

		Outputs:
			df: DataFrame. Dataframe with wave height and timestamps.
		"""
		weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
		            'Saturday', 'Sunday']
		
		wind_time = [x['model_time_local'] for x in wind_dict['model_data']]
		wind_speed = [x['wind_speed'] for x in wind_dict['model_data']]
		wind_time = [datetime.datetime.strptime(x[:-5], '%Y-%m-%d %H:%M:%S') for x
		             in wind_time]
		wind_weekday = [x.weekday() for x in wind_time]
		wind_weekday = [weekdays[x] for x in wind_weekday]
		wind_hour = [x.strftime("%I%p") for x in wind_time]
		
		# Remove leading 0 if necessary
		wind_hour = [x[1:] if x[0] == '0' else x for x in wind_hour]
		
		location_id = wind_dict['spot_id']
		inv_map = {v: k for k, v in self.LOCATION_LOOKUP.items()}
		location = inv_map[location_id]
		
		df_wind = pd.DataFrame({'Location': location,
		                        'DateTime': wind_time,
		                        'Weekday': wind_weekday,
		                        'Hour': wind_hour,
		                        'Wind Speed [mph]': wind_speed})
		
		return df_wind
	
	def PlotWindForecast(self, location):
		"""Plot the wind forecast

		Args:
			location: String. Either the iWindsurf location code associated with the
				location of interest, of the location name itself as long as it's been
				pre-recorded in the class location lookup dictionary.
		"""
		df_wind = self.data
		
		inv_map = {v: k for k, v in self.LOCATION_LOOKUP.items()}
		if location.title() in list(inv_map):
			location = inv_map[location.title()]
		df_wind = df_wind[df_wind['Location'] == location.title()]
		
		weekdays = df_wind['Weekday'].values
		_, unique_idxs = np.unique(weekdays, return_index=True)
		
		# Plot lines separating days
		df_temp = df_wind[df_wind['Hour'] == '12AM']
		for x_temp in df_temp.index:
			plt.axvline(x_temp, markersize=0, linewidth=3, color='red',
			            linestyle='--')
		
		# Add weekday text
		max_speed = np.max(df_wind['Wind Speed [mph]'].values)
		weekdays = df_wind['Weekday'].values
		unique_weekdays = np.unique(weekdays)
		for weekday in unique_weekdays:
			df_temp = df_wind[df_wind['Weekday'] == weekday]
			x_temp = df_temp.index.values
			x_temp = (x_temp[0] + x_temp[-1]) / 2
			# Add Weekday Labels
			plt.gca().text(x=x_temp, y=max_speed + 1.5,
			               s=weekday, fontsize=20, ha='center', va='center')
		
		x_labels = df_wind['Hour'].values
		x = np.arange(0, len(x_labels), 1)
		y = df_wind['Wind Speed [mph]'].values
		plt.plot(x, y, markersize=6, linewidth=1, markeredgecolor='black',
		         marker='o', color='C0')
		
		# Update y-axis limits
		ymin = plt.ylim()[0]
		ymax = plt.ylim()[1]
		plt.ylim([ymin, ymax + 2])
		
		plt.gca().yaxis.grid(True)
		# plt.xlabel('Hour', fontsize=12)
		# plt.ylabel('Wind Speed [mph]', fontsize=12)
		plt.title('Wind Speed @ %s [mph]' % location, fontsize=12, color='white')
		
		_ = plt.xticks(ticks=x[::3], labels=x_labels[::3], rotation=45, fontsize=12)
	