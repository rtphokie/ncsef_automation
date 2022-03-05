from .utils import headers
import olefile
import pandas as pd

def export_list(self, listname, purge_file=False):
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
    if purge_file:
        try:
            os.remove(filename_local)
        except OSError as e:
            print(f'failed to remove {filename_local} {e}')
    return (filename_local, df)

