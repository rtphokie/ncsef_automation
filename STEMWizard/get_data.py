import olefile
import pandas as pd

from utils import headers


def export_list(self, listname):
    '''
    Google prefers all excel files to have an xlsx extension
    :param listname: student, judge, or volunteer
    :param purge_file: delete local file when done, default: false
    :return:
    '''
    if self.token is None:
        raise ValueError('no token found in object, login before calling export_student_list')
    # self.set_columns(listname)
    payload = {'_token': self.token,
               'filetype': 'xls',
               'orderby1': '',
               'sortby1': '',
               'searchhere1': ''
               }
    if listname == 'student':
        url = f'{self.url_base}/fairadmin/export_file'
        payload_specific = {
            'category_select1': '',
            'round2_category_select1': '',
            'child_fair_select1': '',
            'status_select1': '',
            'division1': 0,
            'classperiod_select1': '',
            'student_completion_status1': '',
            'student_checkin_status1': '',
            'student_activation_status1': '',
            'management_user_type_id1': ' 1',
            'checked_fields': '',
            'class_id1': '',
            'admin_status1': '',
            'final_status1': '',
            'files_approval_status1': '',
            'project_status1': '',
            'project_score': '',
            'last_year': '',
        }
    elif listname == 'judge':
        url = f'{self.url_base}/fairadmin/export_file_judge'
        payload_specific = {
            'category_select1': '',
            'judge_types1': '',
            'status_select1': '',
            'final_assigned_category_select1': '',
            'division_judge1': 0,
            'assigned_division1': 0,
            'special_awards_judge1': '',
            'assigned_lead_judge1': '',
            'judge_checkin_status1': '',
            'judge_activation_status1': '',
            'checked_fields_header': '',
            'checked_fields': '',
            'class_id1': '',
            'last_year': '',
            'dashBoardPage1': '',
        }
    elif listname == 'volunteer':
        url = f'{self.url_base}/fairadmin/exportVolunteerExcelPdf'
        payload_specific = {
            'searchhere1': '',
            'registration_status1': '',
            'last_year': '',
        }
    elif listname == 'paymentStatus':
        url = f'{self.url_base}/fairadmin/paymentStatus'
        payload_specific = {
            'management_user_type_id1': '8',
            'student_checkin_status1': '',
            'admin_status1': '',
            'payment_type1': '',
            'division1': '0',
            'number_page': '',
            'page1': '',
            'child_fair_select1': '',
            'origin_fair_select1': '',
            'teacher_id1': '',
            'student_completion_status1': '',
            'final_status1': '',
            'files_approval_status1': '',
            'project_status1': '',
            'checked_fields': '',
        }
    else:
        raise ValueError(f"unknown list {listname}")
    payload.update(payload_specific)

    self.logger.debug(f'posting to {url} using {listname} params')
    rf = self.session.post(url, data=payload, headers=headers, stream=True)
    if rf.status_code >= 300:
        self.logger.error(f"status code {rf.status_code} on post to {url}")
        return
    filename_suggested = rf.headers['Content-Disposition'].replace('attachment; filename="', '').rstrip('"')
    self.logger.info(f'receiving {filename_suggested}')
    filename_local = f'{self.parent_file_dir}/{self.domain}/{listname}_list.xls'

    fp = open(filename_local, 'wb')
    for chunk in rf.iter_content(chunk_size=1024):
        if chunk:  # filter out keep-alive new chunks
            fp.write(chunk)
    fp.flush()
    fp.close()

    ole = olefile.OleFileIO(filename_local)
    df = pd.read_excel(ole.openstream('Workbook'), engine='xlrd')

    remotepath = f'/Automation/{self.domain}/{listname} list.xls'
    if df.shape[0] > 0:
        self.googleapi.create_file(filename_local, remotepath)
    else:
        self.logger.info(f"{listname} list is empty, skipping upload to Google")
    return (filename_local, df)


def export_report(self, saved_report_id, user_type, report_title):
    '''
    automates download from the reports screen
    todo: parse the page to discover report ids and titles, require only a matching report title here.
    :param saved_report_id: from the dropdown mention, defaults to the one we care about right now
    :param user_type: 1 = student, 2 = judge, 3 = volunteer, defaults to student
    :param report_title: used for the resulting xls title, defaults to the one we care about right now
    :return:
    '''
    self.get_csrf_token()
    if self.token is None:
        raise ValueError('no token found in object, login before calling export_student_list')
    payload = {'_token': self.token,
               'user_type': user_type,
               'saved_report_id': saved_report_id,
               'downloadSavedReport': 'savedReport'}

    url = f'{self.url_base}/fairadmin/generateReport'

    headers['Referer'] = 'https://ncsef.stemwizard.com/fairadmin/report'
    headers[
        'Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9'
    self.logger.debug(f'posting to {url} using {saved_report_id} report id')
    rf = self.session.post(url, data=payload, headers=headers, stream=True)
    if rf.status_code >= 300:
        self.logger.error(f"status code {rf.status_code} on post to {url}")
        # return
    # filename_suggested = rf.headers['Content-Disposition'].replace('attachment; filename="', '').rstrip('"')
    filename_suggested = 'report.xls'
    self.logger.info(f'receiving {filename_suggested}')
    filename_local = f'{self.parent_file_dir}/{self.domain}/{report_title}.xls'

    fp = open(filename_local, 'wb')
    for chunk in rf.iter_content(chunk_size=1024):
        if chunk:  # filter out keep-alive new chunks
            fp.write(chunk)
    fp.flush()
    fp.close()
    ole = olefile.OleFileIO(filename_local)
    df = pd.read_excel(ole.openstream('Workbook'), engine='xlrd')
    remotepath = f'/Automation/{self.domain}/{report_title} report.xls'
    if df.shape[0] > 0:
        self.googleapi.create_file(filename_local, remotepath)
    else:
        self.logger.info(f"{report_title} report is empty, skipping upload to Google")

    return filename_local


def _patch_team_filepaths(self, data):
    '''
    Note: this is no longer in use as the bug described below has been resolved.  Leaving it in the codebase for now in case
          the problem returns.

    This code patches around a bug on the STEM Wizard milestones page which displays the same link for each team
    member for files that are unique to that team members (ISEF-1b & Participant Signature Page), by using the AJAX
    fetch of this information from the forms and files page. This shouldn't have to exist, but here we are

    :param data: dictionary of dictionaries with what we learned about the files for each student from the "view files"
                 link on the files and forms screen (not the milestone)
    :return:
    '''
    teams = []
    for k, v in data.items():
        if len(v['First Name']) > 1:
            teams.append(k)

    for k in tqdm(teams, desc='patch team files'):
        v = data[k]
        self.logger.info(f'patching file info for {k} {v["Project Number"]}')
        updated = self._student_file_detail(k, None)
        for filetype in ['ISEF-1b', 'Participant Signature Page']:
            for attr in ['url', 'remote_filename']:
                v['files'][filetype][attr] = []
                for rows in updated.values():
                    for row in rows:
                        try:
                            if row['FILE TYPE'] == filetype:
                                if type(row['FILE NAME']) == dict and attr in row['FILE NAME'].keys():
                                    v['files'][filetype][attr].append(row['FILE NAME'][attr])
                        except:
                            pass
    return data


def download_file_from_url_via_get(self, url, local_filename):
    '''
    streams a specified URL to a local filename, generic get of binary file

    :param url: the url
    :param local_filename: the filename to write the streamed file to
    :return:
    '''
    self.logger.info(f"DownloadFileFromS3Bucket: downloading {url} to {local_filename} from S3")
    r = self.session.get(url)

    if r.status_code >= 300:
        self.logger.error(f"status code {r.status_code} on post to {url}")
        return

    return self._download_to_local_file_path(local_filename, r)


def download_from_stemwizard_via_post(self, filename_remote, local_file_path, referer='FilesAndForms'):
    '''
    download files delivered from STEMWizard via a POST call
    :param filename_remote: filename in the STEMWizard system
    :param local_file_path: local filename to download to
    :param referer: STEMWizard page the request comes from, defaulted to FilesAndForms, generally good enough for any request
    :return:
    '''
    self.get_csrf_token()
    headers['X-CSRF-TOKEN'] = self.csrf
    headers['Referer'] = f'{self.url_base}f/fairadmin/{referer}'
    url = f'{self.url_base}/fairadmin/fileDownload'

    payload = {'_token': self.token,
               'download_filen_path': '/EBS-Stem/stemwizard/webroot/stemwizard/public/assets/images/milestone_uploads',
               'download_hideData': filename_remote,
               }

    rf = self.session.post(url, data=payload, headers=headers)
    if rf.status_code >= 300:
        self.logger.error(f"status code {rf.status_code} on post to {url}")
        return
    return self._download_to_local_file_path(local_file_path, rf)
