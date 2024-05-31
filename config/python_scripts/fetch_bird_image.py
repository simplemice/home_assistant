import requests
import json
import re
from bs4 import BeautifulSoup

page_url = data.get('url')

# Fetch the Wikipedia Page
wiki_page = requests.get(page_url)
soup = BeautifulSoup(wiki_page.content, 'html.parser')

# Parsing Wikipedia Page to get Page ID
wgArticleIdRegex = re.compile(r'wgArticleId":(d+)')
wgArticleId = wgArticleIdRegex.findall(str(soup))[0]

# Fetch the image url from mediawiki API
response = requests.get(f"https://www.mediawiki.org/w/api.php?action=query&format=json&prop=pageimages&piprop=original&pageids={wgArticleId}").json()

# Extract image url
image_url = response['query']['pages'][wgArticleId]['original']['source']

# Set the state of bird image url sensor
hass.states.set('sensor.bird_image_url', image_url)
