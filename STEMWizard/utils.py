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

def set_columns(self, listname='judge'):
    '''
    there's lots of if-then-else going on here because of inconsistencies in naming across
    STEM Wizard, still worth centralizing setting all columns to be visible across judge, student, and volunteer lists

    :param listname: expects, judge, volunteer, or student
    :return: nothing
    '''
    if listname == 'volunteer':
        endpoint = 'fairadmin/volunteers'
    else:
        endpoint = f'fairadmin/{listname}'
    self.get_csrf_token()
    headers['X-CSRF-TOKEN'] = self.csrf
    headers['Referer'] = f'{self.url_base}f/fairadmin/{listname}'
    headers['X-Requested-With'] = 'XMLHttpRequest'

    # https://ncregtest.stemwizard.com/fairadmin/showVolunteerList
    # https://ncregtest.stemwizard.com/fairadmin/showVolunteerList

    # build list URL, these aren't consistently named
    if listname == 'judge':
        url = f'{self.url_base}/fairadmin/ShowJudgesList'
        payload = {'per_page': 50,
                   'page': 1,
                   'searchhere': '',
                   'category_select': '',
                   'judge_types': '',
                   'judge_activation_status': '',
                   'status_select': '',
                   'final_assigned_category_select': '',
                   'special_awards_judge': '',
                   'final_status': '',
                   'division_judge': 0,
                   'assigned_division': 0,
                   'judge_checkin_status': '',
                   'division': 0,
                   'last_year': '',
                   'dashBoardPage': '',
                   'assigned_lead_judge': ''
                   }
    elif listname == 'student':
        url = f'{self.url_base}/fairadmin/ShowStudentList'
        payload = {
            'page': 1,
            'searchhere': '',
            'category_select': '',
            'round2_category_select': '',
            'child_fair_select': '',
            'status_select': '',
            'class_id': '',
            'student_completion_status': '',
            'files_approval_status': '',
            'final_status': '',
            'project_status': '',
            'admin_status': '',
            'student_checkin_status': '',
            'student_activation_status': '',
            'division': 0,
            'project_score': '',
            'last_year': '',
            'round_select': '',
        }
    elif listname == 'volunteer':
        url = f'{self.url_base}/fairadmin/showVolunteerList'
        payload = {'per_page': 999,
                   'page': 1,
                   'searchhere': '',
                   'registration_status': '', 'last_year': ''
                   }

    else:
        raise ValueError(f'unhandled list name {listname} in set_columns')

    r1 = self.session.post(url, data=payload, headers=headers)
    if r1.status_code != 200:
        raise ValueError(f"status code {r1.status_code}")

    # find the column codes
    soup = BeautifulSoup(r1.text, 'lxml')
    all_columns = {'0','1','2'}
    for ele in soup.find_all('input', {'class', 'ace chkslct'}):
        jkl=ele.get('value')
        if len(jkl):
            all_columns.add(jkl)
    payload = {'checked_fields': ','.join(all_columns),
               'region_id': self.region_id,
               'management_user_type_id': 3}

    # set all columns to be visible
    url2 = f'{self.url_base}/fairadmin/saveStudentColumnSettings'
    r2 = self.session.post(url2, data=payload, headers=headers)
    if r2.status_code != 200:
        raise ValueError(f"status code {r2.status_code} from POST to {url2}")

