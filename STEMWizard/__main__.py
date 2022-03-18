import os
from datetime import datetime
from pprint import pprint

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup
from tqdm import tqdm

from categories import categories
from fileutils import read_json_cache, write_json_cache
from google_sync import NCSEFGoogleDrive
from logstuff import get_logger
from utils import headers

pd.set_option('display.max_columns', None)


class STEMWizardAPI(object):
    from get_data import export_list, export_report
    from get_data import download_file_from_url_via_get, download_from_stemwizard_via_post
    from get_data import download_file_from_url_via_get, download_from_stemwizard_via_post
    from utils import get_region_info, get_csrf_token, _merge_dicts, _download_to_local_file_path

    def __init__(self, configfile='stemwizardapi.yaml', login_stemwizard=True, login_google=True):
        '''
        initiates a session using credentials in the specified configuration file
        Note that this user must be an administrator on the STEM Wizard site.
        :param configfile: configfile: (default to stemwizardapi.yaml)
        '''
        self.authenticated = None
        self.session = requests.Session()  # shared session, maintains cookies throughout
        self.region_domain = 'unknown'
        self.parent_file_dir = 'files'
        self.region_id = None
        self.csrf = None
        self.username = None
        self.password = None
        if login_google:
            self.googleapi = NCSEFGoogleDrive()
        else:
            self.googleapi = None
        self.read_config(configfile)
        self.logger = get_logger(self.domain)
        if self.username is None or len(self.username) < 6:
            raise ValueError(f'did not find a valid username in {configfile}')
        if self.password is None or len(self.password) < 6:
            raise ValueError(f'did not find a valid password in {configfile}')
        self.url_base = f'https://{self.domain}.stemwizard.com'

        self.get_region_info()

        if login_stemwizard:
            self.authenticated = self.login()
        else:
            self.authenticated = None

        if self.region_domain != self.domain:
            raise ValueError(
                f'STEM Wizard returned a region domain of {self.region_domain}, which varies from the {self.domain} value in the config file')

    def __del__(self):
        self.session.close()

    def read_config(self, configfile):
        """
        reads named yaml configuration file
        :param configfile: (defaulted to stemwizardapi.yaml above)
        :return: nothing, updates username, password and token attribuates on the object
        """
        fp = open(configfile, 'r')
        data_loaded = yaml.safe_load(fp)
        self.domain = data_loaded['domain']
        self.username = data_loaded['username']
        self.password = data_loaded['password']
        fp.close()

    def login(self):
        '''
        authenticates against STEM Wizard
        :return:
        '''
        if self.region_id is None:
            self.get_region_info()

        payload = {'region_domain': self.domain,
                   'region_id': self.region_id,
                   'region': self.region_domain,
                   '_token': self.token,
                   'username': self.username,
                   'password': self.password}

        url_login = f'{self.url_base}/admin/authenticate'

        rp = self.session.post(url_login, data=payload, headers=headers,
                               allow_redirects=True)  # , cookies=session_cookies)
        if rp.status_code >= 300:
            self.logger.error(f"status code {rp.status_code} on post to {url_login}")
            return

        # self.token = token
        # self.region_id = payload['region_id']
        authenticated = rp.status_code == 200
        if authenticated:
            self.logger.info(f"authenticated to {self.domain}")
        else:
            self.logger.error(f"failed to authenticate to {self.domain}")

        self.get_csrf_token()

        return authenticated

    def _student_file_detail(self, studentId, info_id):
        ''' fetches info about a given studentID (project really) '''
        self.get_csrf_token()
        url = f'{self.url_base}/filesAndForms/studentFormsAndFilesDetailedView'
        payload = {'studentId': studentId, 'info_id': info_id}

        headers['X-CSRF-TOKEN'] = self.csrf
        headers['Referer'] = f'{self.url_base}/filesAndForms'
        headers['X-Requested-With'] = 'XMLHttpRequest'
        rfaf = self.session.post(url, data=payload, headers=headers)
        if rfaf.status_code >= 300:
            self.logger.error(f"status code {rfaf.status_code} on post to {url}")
            return
        if info_id is None:
            self.logger.debug(f"getting student info ids for  {studentId}")
            # fp = open('foo.html', 'w')
            # fp.write(rfaf.text)
            # fp.close()
            soup = BeautifulSoup(rfaf.text, 'html.parser')
            # <li class="student_tab" id="64585">
            students = soup.find_all('li', {'class': 'student_tab'})
            data = {}
            for student in students:
                infoid = student['id']
                if infoid is not None:
                    data[f"{studentId} {infoid}"] = self._student_file_detail(studentId, infoid)
        else:
            self.logger.debug(f"getting file info for {studentId} {info_id}")
            data = []
            soup = BeautifulSoup(rfaf.text, 'html.parser')
            # <table class="table table-striped table-bordered table-hover dataTable" style="width:100%;position: relative;border:1px solid #e4e4e4">
            thetable = soup.find('table', {'class': "table table-striped table-bordered table-hover dataTable"})
            # thead = thetable.find('thead')
            th_labels = []
            for th in thetable.find_all('th'):
                th_labels.append(th.text)
            # tbody = thetable.find('tbody')
            for tr in thetable.find_all('tr'):
                row = {}
                for label, td in zip(th_labels, tr.find_all('td')):
                    l = td.find('a')
                    if l is not None:
                        # <a href="#" title="Download" downloadprojfile="McMichael Student Checklist.jpg" downloadprojfilename="McMichael Student Checklist_67263_164437473362.jpg" uploaddocname="https://stem-s3-2021.s3.us-west-1.amazonaws.com/2021/production/project_files/McMichael Student Checklist_67263_164437473362.jpg" class="downloadProjStudent" id="downloadProjStudent" style="text-decoration:none">                            McMichael Student Checklist.jpg</a>
                        if l.has_attr('uploaddocname'):
                            # downloadable from s3 bucket
                            row[label] = {'url': l['uploaddocname'], 'remote_filename': l['downloadprojfilename']}
                        else:
                            # downloadable from STEM Wizard site
                            row[label] = {'remote_filename': l['uploaded_file_name']}

                    else:
                        contents = td.text
                        if label == 'FILE TYPE':
                            # normalize file types
                            contents = contents.replace('2022 NCSEF ', '')
                            contents = contents.replace('Abstract Form', 'Abstract')
                            contents = contents.replace('ISEF ', 'ISEF-')
                            if 'Research Plan' in contents:
                                contents = 'Research Plan'
                        row[label] = contents.strip()
                if len(row):
                    data.append(row)
        return data

    def studentSync(self, cache_file_name='caches/student_data.json', download=True, upload=True, refresh=False, force=False):
        '''
        sync student files from STEM Wizard to local filesystem and then up to Google Drive

        :param cache_file_name: filename
        :param download: download files from AWS and STEM Wizard (default True)
        :param upload:upload files to GoogleDrive (default True)
        :return: dictionary of projects and their metadata
        '''
        if download and not self.authenticated:
            raise Exception("can't download files from an unauthenticated STEM Wizard session")
        if upload and not self.googleapi:
            raise Exception("can't upload files to Google Drive without an authenticated session")
        threads = {
            #                         caches/student_project_data.json
            'project': {'cachefile': 'caches/student_project_data.json',
                        'max_cache_age': 9000,
                        'function': lambda: self.get_project_info()},
            'form': {'cachefile': 'caches/student_form_data.json',
                     'max_cache_age': 12000,
                     'function': lambda: self.get_files_and_forms()},
            'file': {'cachefile': 'caches/student_file_data.json',
                     'max_cache_age': 9000,
                     'function': lambda: self.get_judges_materials()},
        }

        # fetch data from project, forms and files, and files for judges tabs on milestones page,
        # by div/category for performance
        self.logger.info('refreshing local data caches as necessary')
        data = {}
        for k, v in threads.items():
            if refresh:
                v['max_cache_age'] = 0
            data[k] = read_json_cache(v['cachefile'], max_cache_age=v['max_cache_age'])
            if len(data[k]) == 0:
                data[k] = v['function']()
                write_json_cache(data[k], v['cachefile'])

        self.logger.info('merging file information')
        # combine dictionaries into a single view of student metadata
        data = self._merge_dicts(data)
        write_json_cache(data['all'], 'caches/student_data.json')

        # # code around bug on milestones page which fails to differentiate files uploaded by separate team members.
        # data['fixed'] = read_json_cache('caches/student_data_fixed.json', max_cache_age=9000)
        # if len(data['fixed']) == 0:
        #     self.logger.info('patching file information for team projects')
        #     data['fixed'] = self._patch_team_filepaths(data['all'])
        #     write_json_cache(data['fixed'], 'caches/student_data_fixed.json')
        # write_json_cache(data['all'], 'caches/student_data_unpatched.json')
        # data['all'] = data['fixed']

        # generate local names for the files and forms
        self.logger.info('checking local copies of these files')
        data['localized'] = self.analyze_local_files(data['all'])
        write_json_cache(data['localized'], 'caches/student_data.json')

        if download:
            self.logger.info('synching to local filesystem')
            self.sync_files_locally(data['localized'], force=force)
        else:
            self.logger.info('not synching to local filesystem')

        if upload:
            self.logger.info('synching to Google Drive')
            data['localized'] = self.sync_to_google(data['all'])

        return data['localized']

    def analyze_local_files(self, data):
        '''
        iterates over file meta data, determining what the local filename should be

        :param data:
        :return:
        '''
        # dir = f"files/{self.region_domain}"
        dir = ''
        for k, v in data.items():
            project_number = v['Project Number']
            v['participants'] = len(v['Last Name'])
            try:
                div, cat, no = project_number.split('-')
            except:
                cat = 'uncategorized'
                no = k
                if 'Ele' in v['Division']:
                    div = 'ELE'
                elif 'Jun' in v['Division']:
                    div = 'JR'
                elif 'Sen' in v['Division']:
                    div = 'SR'
                else:
                    print(f"unhandled division {v['Division']}")
                    pprint(v)
                    raise
            for filetype, filedata in v['files'].items():
                # ELE-BIOS-001_Participant Signature Page.pdf
                prefix = filetype
                for remote_filename, lastname, firstname in zip(filedata['remote_filename'], v['Last Name'],
                                                                v['First Name']):
                    if len(remote_filename) == 0:
                        continue
                    if len(filedata['remote_filename']) > 1:
                        prefix = f"{filetype}_{lastname}_{firstname}"
                    else:
                        prefix = filetype
                    atoms = remote_filename.split('.')
                    filedata['local_filename'].append(
                        f"{div}/{cat}/{project_number}/{project_number}_{prefix}.{atoms[-1]}")
                for filepath in filedata['local_filename']:
                    fullpath = f"files/ncsef/{filepath}"
                    if os.path.exists(fullpath):
                        filedata['local_lastmod'].append(datetime.fromtimestamp(os.path.getmtime(fullpath)))
                    else:
                        filedata['local_lastmod'].append(None)
        return data

    def sync_to_google(self, data):
        '''
        synchronize locally downloaded files and forms to Google drive by project number, create links with symposium
        relevant files, by project number (flat)

        :param data:
        :return:
        '''
        byp = dict()
        for d in data.values():
            byp[d['Project Number']] = d

        for projectnumber in tqdm(sorted(byp.keys()), desc="sync to google"):
            v = byp[projectnumber]
            for filetype, filedata in v['files'].items():
                for (local_filename, local_lastmod) in zip(filedata['local_filename'], filedata['local_lastmod']):
                    if filetype in ['Abstract Form', '1C', '7']:  # duplicated on judge screen
                        continue
                    remote_filename = f"/Automation/ncsef/by project/{local_filename}"
                    if os.path.exists(f"files/ncsef/{local_filename}"):
                        self.googleapi.create_file(f"files/ncsef/{local_filename}", remote_filename)

        # symposium links
        self.googleapi.list_all(force=False)  # refresh cache with newly created nodes and folders
        for projectnumber in tqdm(sorted(byp.keys()), desc="symposium links"):
            v = byp[projectnumber]
            for filetype, filedata in v['files'].items():
                for (local_filename, local_lastmod) in zip(filedata['local_filename'], filedata['local_lastmod']):
                    remote_filename = f"/Automation/ncsef/by project/{local_filename}"
                    if os.path.exists(f"files/ncsef/{local_filename}"):
                        if filetype in ['Abstract', 'Quad Chart', 'Project Presentation Slides', 'Research Paper',
                                        'Lab Notebook']:
                            elements = remote_filename.replace('by project', 'for symposium').split('/')
                            remote_dir = '/'.join(elements[:-1])
                            self.googleapi.create_shortcut(remote_filename, remote_dir, elements[-1])

        return data

    def sync_files_locally(self, data, force=True):
        '''
        iterate over projects, ensureing each file has been downloaded locally
        :param data:
        :return: nothing
        '''
        for id, v in tqdm(data.items()):
            for filetype, filedata in v['files'].items():
                if filetype in ['Abstract Form', '1C', '7']:  # duplicated on judge screen
                    continue
                if len(filedata['url']) > 0:
                    for (url, local_filename, local_lastmod) in zip(filedata['url'], filedata['local_filename'],
                                                                    filedata['local_lastmod']):
                        if 'amazonaws.com' in url and (force or local_lastmod is None):
                            self.download_file_from_url_via_get(url, local_filename)
                else:
                    for (remote_filename, local_filename, local_lastmod) in zip(filedata['remote_filename'],
                                                                                filedata['local_filename'],
                                                                                filedata['local_lastmod']):
                        if len(remote_filename) > 0 and (force or local_lastmod is None):
                            self.download_from_stemwizard_via_post(remote_filename, local_filename)

    def get_files_and_forms(self):
        '''
        parse files and forms milestone for relevant files

        :return: dictionary of projects with files dictionary
        '''
        if not self.authenticated:
            self.authenticated = self.login()
        data = {}
        headers['X-CSRF-TOKEN'] = self.csrf
        for category_id, category_title in tqdm(categories.items(), desc='Files and Forms'):
            payload = {'page': 1,
                       'per_page': 999,
                       'st_stmile_id': 1337,
                       'mileName': 'Files and Forms',
                       'division': 0,
                       'category_select': category_id,
                       'student_activation_status': 1,
                       }
            url = f'{self.url_base}/fairadmin/getstudentCustomMilestoneDetailView'
            r = self.session.post(url, data=payload, headers=headers)
            soup = BeautifulSoup(r.text, 'lxml')
            head = soup.find('thead')
            th_labels = []
            for th in head.find_all('th'):
                v = th.text.strip()
                v = v.replace('2022 NCSEF ', '')
                if 'Research' in v:
                    v = 'Research Plan'
                if len(v) <= 2:
                    v = f"ISEF-{v.lower()}"
                th_labels.append(v)

            body = soup.find('tbody')
            for row in body.find_all('tr'):
                import uuid
                studentid = f"unknown_{uuid.uuid4()}"
                studentdata = {'studentid': None, 'files': {}}
                for header in th_labels[6:]:
                    studentdata['files'][header] = {'url': [], 'remote_filename': [], 'local_filename': [],
                                                    'local_lastmod': []}
                for n, td in enumerate(row.find_all('td')):
                    if n < 5:
                        studentdata[th_labels[n]] = td.text.strip().replace(" \n\n", ', ')
                        a = td.find('a')
                        if a:
                            l = a['href']
                            atoms = l.split('/')
                            studentid = atoms[-2]
                            studentdata['studentid'] = studentid
                    else:
                        a = td.find_all('a')
                        if a:
                            # studentdata['files'][th_labels[n]] = {'url': []}
                            for link in a:
                                atoms = link['href'].split('/')
                                studentdata['files'][th_labels[n]]['url'].append(link['href'])
                                studentdata['files'][th_labels[n]]['remote_filename'].append(atoms[-1])
                data[studentid] = studentdata
        return data

    def get_judges_materials(self):
        '''
        parse juudges materials milestone for relevant files

        :return: dictionary of projects with files dictionary
        '''
        if not self.authenticated:
            self.authenticated = self.login()
        data = {}
        headers['X-CSRF-TOKEN'] = self.csrf
        for category_id, category_title in tqdm(categories.items(), desc='judges materials'):

            url = f'{self.url_base}/fairadmin/getstudentCustomMilestoneDetailView'
            params = f'page=1&category_select={category_id}&per_page=999&st_stmile_id=3153&student_activation_status=1'
            r = self.session.post(f"{url}?{params}", headers=headers)
            soup = BeautifulSoup(r.text, 'lxml')
            head = soup.find('thead')
            th_labels = []
            for th in head.find_all('th'):
                hasp = th.find('p')
                if hasp:
                    v = th.find('p').text.strip()
                else:
                    v = th.text.strip()
                v = v.replace('2022 NCSEF ', '')
                for shortname in ['Research Paper', 'Abstract', 'Quad Chart', 'Lab Notebook ',
                                  'Project Presentation Slides', '1 minute video', '1C', '7']:
                    if shortname.lower() in v.lower():
                        v = shortname
                th_labels.append(v.strip())  # remove stray whitespace in th text
            body = soup.find('tbody')
            for row in body.find_all('tr'):
                studentdata = {'studentid': None, 'files': {}}
                for header in th_labels[5:]:
                    studentdata['files'][header] = {'url': [], 'remote_filename': [],
                                                    'local_filename': [], 'local_lastmod': []}
                for n, td in enumerate(row.find_all('td')):
                    if n < 5:
                        studentdata[th_labels[n]] = td.text.strip().replace(" \n\n", ', ')
                        a = td.find('a')
                        if a:
                            l = a['href']
                            atoms = l.split('/')
                            studentid = atoms[-2]
                            studentdata['studentid'] = studentid
                    else:
                        a = td.find('a')
                        if a:
                            studentdata['files'][th_labels[n]]['url'].append(a['href'])
                        else:
                            studentdata['files'][th_labels[n]]['remote_filename'].append(td.text)
                data[studentid] = studentdata
        return data

    def get_project_info(self):
        '''
        parse project info milestone for relevant files

        :return: dictionary of projects with files dictionary
        '''
        if not self.authenticated:
            self.authenticated = self.login()

        data = {}
        headers['X-CSRF-TOKEN'] = self.csrf
        for category_id, category_title in tqdm(categories.items(), desc='project'):
            url = f'{self.url_base}/fairadmin/getstudentCustomMilestoneDetailView'
            params = f'page=1&category_select={category_id}&child_fair_select=&searchhere=&orderby=&sortby=&division=&class_id=&per_page=999&student_completion_status=undefined&admin_status=undefined&student_checkin_status=&student_milestone_status=&st_stmile_id=1335&grade_select=&student_activation_status=1'
            r = self.session.post(f"{url}?{params}", headers=headers)
            fp = open(f'/tmp/project.html', 'w')
            fp.write(r.text)
            fp.close()
            soup = BeautifulSoup(r.text, 'lxml')
            head = soup.find('thead')
            if head is None:
                print(r.status_code)
                print(r.text)
                raise ValueError(
                    f'no table head found on project tab for {category_title} of getstudentCustomMilestoneDetailView ')
            th_labels = []
            for th in head.find_all('th'):
                hasp = th.find('p')
                if hasp:
                    v = th.find('p').text.strip()
                else:
                    v = th.text.strip()
                v = v.replace('2022 NCSEF ', '')
                for shortname in ['Research Paper', 'Abstract', 'Quad Chart', 'Lab Notebook ',
                                  'Project Presentation Slides', '1 minute video', '1C', '7']:
                    if shortname.lower() in v.lower():
                        v = shortname
                th_labels.append(v)
            body = soup.find('tbody')
            for row in body.find_all('tr'):
                studentid = row['id'].replace('updatedStudentDiv_', '')
                data[studentid] = {}
                for n, td in enumerate(row.find_all('td')):
                    divs = td.find_all('div')
                    if divs and th_labels[n] != 'Project Name':
                        data[studentid][th_labels[n]] = []
                        for div in divs:
                            data[studentid][th_labels[n]].append(div.text.strip())
                    elif th_labels[n] == 'Project Name':
                        p = td.find('p')
                        if p:
                            data[studentid][th_labels[n]] = p.text.strip()
                        else:
                            data[studentid][th_labels[n]] = td.text.strip()
                    else:
                        data[studentid][th_labels[n]] = td.text.strip()
        return data

    def download_student_reports(self, saved_report_id=972, report_title='Treasurer Report'):
        # wrapper for download_reports
        return self.export_report(saved_report_id, 1, report_title)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action='store_true', default=False, help="force data refresh")
    parser.add_argument("--nostudent", action='store_true', help="refresh data on student files (default: %(default)s)")
    parser.add_argument("--nogoogle", action='store_true', help="sync to Google Drive (default: %(default)s)")
    parser.add_argument("--nodownload", action='store_true',
                        help="download files from STEM Wizard (default: %(default)s)")
    parser.add_argument("--config", default='stemwizardapi_ncsef.yaml', help="config file")
    parser.add_argument('--reports', default='all', const='all', nargs='?',
                        choices=['judge', 'student', 'treasurer', 'all', 'none'],
                        help='(default: %(default)s)')

    args = parser.parse_args()

    print("logging into STEMWizard")
    uut = STEMWizardAPI(configfile=args.config, login_stemwizard=True, login_google=True)

    local_filenames = {'student': 'files/ncsef/student_list.xls'}
    dfs = {}
    for listname in ['student', 'judge']:
        if listname in args.reports or args.reports == 'all':
            print(f'generating {listname} list')
            local_filenames[listname], dfs[listname] = uut.export_list(listname)

    if 'treasurer' in args.reports:
        print(f"generating treasurer's report")
        local_filename = uut.download_student_reports(saved_report_id=972, report_title='Treasurer Report')

    if not args.nostudent:
        print('analyzing student files')
        student_data = uut.studentSync()
