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
- an account on that site with administrative privledges 
- requests, bs4 (BeautifulSoup), pandas, and xlrd packages (see requirements.txt)


# Installation
1. download the package<BR>
   ``git clone https://github.com/rtphokie/stemwizardapi.git``
1. create a virtual environment, and activate it (highly recommended)<BR> 
   ``python3 -m venv venv``<BR>
   ``source venv/bin/activate``
1. update the username, password, and region name (from what appears before .stemwizard.com in your URL) in the stemwizadapi.yaml file

# Usage

   


## Features
- Fetches student data
  - saved locallu in Excel format
  - available as a Pandas Dataframe for further analysis
- Fetches student files and forms  
  - saved to local directory tree by student id (internal designator to STEM Wizard), student, or project id

## Future features
- Synchronization of data to Google sheet
- Syncronization of files and forms to Google Drive 
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
