import json
import requests
from datetime import datetime, timedelta

class Fedex:
    def __init__(self) -> None:
        self.api_key = None
        self.secret = json.loads(open('fedex.json').read())
        self.last_key_refresh=None
        self.api_key = self.authenticate()
  
    def authenticate(self):
        """Authenticate with the server, collect api key(FEDEX)"""
        if self.last_key_refresh and (datetime.now() - timedelta(hours=1)) > self.last_key_refresh:
            print("Re-authing within one hour.")
            raise Exception
        url = "https://apis.fedex.com/oauth/token"

        payload = {
            'grant_type':'client_credentials',
            'client_id': self.secret['client_id'],
            'client_secret': self.secret['client_secret']
        }

        headers = {
            'Content-Type': "application/x-www-form-urlencoded"
        }

        response = requests.request("POST", url, data=payload, headers=headers)
        api_key = response.json()['access_token']
        self.last_key_refresh=datetime.now()
        return api_key

    def track_shipment(self, tracking_num, print_response=False):
        """Retrieve tracking info from fedex"""
       
        url = 'https://apis.fedex.com/track/v1/trackingnumbers'

        headers = {
            'Content-Type': "application/json",
            'X-locale': "en_US",
            'Authorization': "Bearer " + self.api_key
        }

        payload = json.dumps({"trackingInfo": 
                        [{"trackingNumberInfo":
                            {"trackingNumber": tracking_num}
                            }],"includeDetailedScans": "true"})
        
        response = requests.request("POST", url, data=payload, headers=headers)

        if print_response:
            print(response.json())
        if(response.status_code == 401):
            print("re-authing -- 401")
            self.api_key = self.authenticate()
            return self.track_shipment(tracking_num)

        return self.process_tracking(response.json())
        
    def process_tracking(self, response):
        """Processes fedex json response"""

        status_info = 'Pending'
        status = response['output']['completeTrackResults'][0]['trackResults'][0]['latestStatusDetail']['statusByLocale']
        latest_ship_event = response['output']['completeTrackResults'][0]['trackResults'][0]['scanEvents'][0]['exceptionDescription']

        try:
            latest_ship_event = response['output']['completeTrackResults'][0]['trackResults'][0]['error']['code']
        except KeyError:
            for i in response['output']['completeTrackResults'][0]['trackResults'][0]['dateAndTimes']:
                if i['type'] == 'ESTIMATED_DELIVERY':
                    status_info = i['dateTime'][0:(i['dateTime']).index('T')] 
                elif i['type'] == 'ACTUAL_DELIVERY':
                    status_info = i['dateTime'][0:(i['dateTime']).index('T')]

            if latest_ship_event == 'Package delayed' or (latest_ship_event == '' and status == 'Delivery exception'):
                for i in response['output']['completeTrackResults'][0]['trackResults'][0]['scanEvents']:
                    if i['eventDescription'] == 'Delivery exception':
                        latest_ship_event = i['exceptionDescription']
                        break
            if status == 'In transit':
                if response['output']['completeTrackResults'][0]['trackResults'][0]['latestStatusDetail']['description'] != 'In transit':
                    latest_ship_event = response['output']['completeTrackResults'][0]['trackResults'][0]['latestStatusDetail']['description']

        return [status, status_info, latest_ship_event]
