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
		self.dict = None

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
		URL = 'https://api.weatherflow.com/wxengine/rest/model/getModelDataBySpot?callback=jQuery17207893792136264395_1687721822087&units_wind=mph&units_temp=f&units_distance=mi&units_precip=in&spot_id=%i&model_id=211&wf_token=e98f1d911867fbb1943370810d53e775&_=1687721822297' % spot_id

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
		self.dict = wind_dict
		
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

		# Remove the last day if it's a duplicate of the first day
		indices = []

		weekdays = np.unique(df_wind['Weekday'])
		for weekday in weekdays:
			df_temp = df_wind[df_wind['Weekday'] == weekday]
			day_first = df_temp['DateTime'].astype('object').values[0]
			datetimes = np.unique(df_temp['DateTime'].astype('object').values)
			for index, row in df_temp.iterrows():
				if row['DateTime'].day == day_first.day:
					continue
				indices += [index]
		df_wind.drop(index=indices, inplace=True)
		
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
		# plt.figure(figsize=(10,4))

		df_temp = df_wind[df_wind['Hour'] == '12AM']
		for x_temp in df_temp.index:
			plt.axvline(x_temp, markersize=0, linewidth=2, color='red',
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
			               s=weekday, fontsize=10, ha='center', va='center')
		
		x_labels = df_wind['Hour'].values
		x = np.arange(0, len(x_labels), 1)
		y = df_wind['Wind Speed [mph]'].values
		plt.plot(x, y, markersize=0, linewidth=2, markeredgecolor='black',
		         marker='o', color='C0')
		
		# Update y-axis limits
		ymin = plt.ylim()[0]
		ymax = plt.ylim()[1]
		plt.ylim([ymin, ymax + 2])
		
		plt.gca().yaxis.grid(True)

		plt.title('Wind Speed @ %s [mph]' % location, fontsize=12, color='white')
		
		_ = plt.xticks(ticks=x[::6], labels=x_labels[::6], rotation=45, fontsize=8)
	