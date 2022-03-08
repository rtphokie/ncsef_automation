STEM Wizard is a powerful tool for managing science fairs from the local to the state level.  
Using it to manage larger fairs where student and project information needs to be shared with dozens or
more judges, volunteers and administrators can be challenging as can implementing workflows that stray
from those envisioned by the STEM Wizard developers.

While STEM Wizard does provide export functionality for student, judge and volunteer data, this is 
available only through the webtool, no API has been made available, supported or otherwise, to enable
fairs to customize their solutions.

This package provides some automation to assist there.

# Requirements
- Python 3.9
- an active STEMWizard site
- an account on that site with administrative privileges
- requests, bs4 (BeautifulSoup), pandas, and xlrd packages (see requirements.txt)
- A [google API service account](https://cloud.google.com/docs/authentication/getting-started) (they're free) with access to your organization's Google Drive


# Installation
1. download the package<BR>
   ``git clone https://github.com/rtphokie/ncsef_automation.git``
2. create a virtual environment, and activate it (highly recommended)<BR> 
   ``python3 -m venv venv``<BR>
   ``source venv/bin/activate``
3. create a stemwizardapi.yaml file (see) excample below. Fill in the username, password, and region name (from what appears before .stemwizard.com in your URL) and the google API client email address.
4. ensure the json file downloaded downloaded from Google APIs is accessible (generally in ~/.config)

```
username: <username of a fair admin>
password: <password>
domain: <the part to the left of STEMWizard.com>
google_client_email: something-something-something@something-something-123456.iam.gserviceaccount.com

```

# Usage

```
usage: STEMWizard [-h] [--force] [--nostudent] [--nogoogle] [--nodownload] [--config CONFIG] [--list [{judge,student,all,none}]]

optional arguments:
  -h, --help            show this help message and exit
  --force               force data refresh
  --nostudent           refresh data on student files (default: False)
  --nogoogle            sync to Google Drive (default: False)
  --nodownload          download files from STEM Wizard (default: False)
  --config CONFIG       config file
  --list [{judge,student,all,none}]
                        judges, students or both (default: all)

```


## Features
- Fetches student data
  - saved locally in Excel format
  - available as a Pandas Dataframe for further analysis
- Fetches student files and forms  
  - saved to local directory tree by student id (internal designator to STEM Wizard), student, or project id

## Future features
- Synchronization of data to Google sheet (as an Excel file, but its compatible)
- Syncronization of files and forms to Google Drive, by division (ELE, JR, SR) and division (BIO, PHY, etc.)
- Judge data
- Volunteer data

### About authentication & credentials
This package uses a combination of the Python requests module for direct interaction with the backend servers
along with BeautifulSoup to scrape (parse) web pages for data.  

Credentials (placed in the yaml file) must have admin privledges to access this data.

Access tokens as well as those used to prevent cross site request forgeries are gathered through parsing 
html head sections along with hidden input values in some forms. 


### disclaimers
- This is not a product of STEM Wizard, Glow Touch software, or any of their partners.  It is an attempt
  to fill a specific need of a fair
- No warrenty is expressed or implied, use at your own risk
- throttling controls (e.g. attempts to maintain local cache and other storage 
  outside of STEM Wizard) are there for a reason: to be a responsible user of STEM Wizard.
  Don't circumvent them.
- This was created to support a state level fair, fed by multiple regional fairs, with about 300-400 students
  participating.  Keep this scope in mind when considering how it fits your Fair

