from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'}


def get_region_info(self):
    '''
    gets admin login page, scrapes region and token info for later use
    :return: nothing, updates region_id, region_domain, and token parameters in the object
    '''
    url = f'{self.url_base}/admin/login'
    r = self.session.get(url, headers=headers, allow_redirects=True)
    if r.status_code >= 300:
        self.logger.error(f"status code {r.status_code} on post to {url}")
        return

    # scrape token
    soup = BeautifulSoup(r.text, 'html.parser')
    token_ele = soup.find('input', {'name': '_token'})
    token = token_ele.get('value')
    self.token = token

    # scrape region info
    data = {'region_id': None, 'region_domain': None}
    for x in soup.find_all('input'):
        if 'region' in x.get('name'):
            data[x.get('name')] = x.get('value')
    if data['region_id'] is not None:
        self.region_id = data['region_id']
    else:
        self.logger.error(f"region id not found on login page")
        raise ValueError('region id not found on login page')
    if data['region_domain'] is not None:
        self.region_domain = data['region_domain']
    else:
        self.logger.error(f"region domain not found on login page")
        raise ValueError('region domain not found on login page')


def get_csrf_token(self):
    '''
    ensures a valid cross site request forgery prevention token is on the object
    :return: nothing
    '''
    if self.csrf is None:
        url = f'{self.url_base}/filesAndForms'
        r = self.session.get(url, headers=headers)
        if r.status_code >= 300:
            self.logger.error(f"status code {r.status_code} on post to {url}")
            return
        soup = BeautifulSoup(r.text, 'lxml')
        csrf = soup.find('meta', {'name': 'csrf-token'})
        if csrf is not None:
            self.csrf = csrf.get('content')
        self.logger.info(f"gathered CSRF token {self.csrf}")
