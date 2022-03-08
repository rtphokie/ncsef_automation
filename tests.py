import os
import unittest
from pprint import pprint

from STEMWizard import google_sync, STEMWizardAPI
from STEMWizard.fileutils import write_json_cache
from STEMWizard.google_sync import NCSEFGoogleDrive

configfile = 'stemwizardapi.yaml'
configfile_prod = 'stemwizardapi_ncsef.yaml'


class GoogleSheetsSyncTestCases(unittest.TestCase):

    def test_sheet(self):
        sheet = google_sync.get_sheet('NCSEF 2022 student list')


class GoogleDriveSyncTestCases(unittest.TestCase):

    def destructive_test_updatefile(self):
        uut = NCSEFGoogleDrive()
        localpath = 'files/ncsef/judge_list.xls'
        remotepath = '/Automation/ncsef/by judge/judge list.xls'
        uut.create_file(localpath, remotepath)
        # print(uut)

    def test_drive_dump(self):
        uut = NCSEFGoogleDrive()
        str = uut.__str__()
        lines = str.split("\n")
        self.assertGreaterEqual(len(lines), 125)
        seen = {}
        for x in lines:
            if x not in seen.keys():
                seen[x] = 0
            seen[x] += 1
        self.assertEqual(len(lines), sum(seen.values()))  # ensure each full path shows up just once in output
        print(uut)

    def test_drive_dump_specific_folder(self):
        uut = NCSEFGoogleDrive()
        str = uut.dump('/Automation/ncsef/by category/SR', indent_character=".", show_emoji=True)
        lines = str.split("\n")
        self.assertNotEqual(len(uut.ids), len(lines))
        self.assertIn('📁/Automation/ncsef/by category/SR', lines)
        self.assertIn('.📁/Automation/ncsef/by category/SR/BSA', lines)

    def test_create_folder(self):
        uut = NCSEFGoogleDrive()
        # uut.list_all(cache_update_ttl=0)
        data = {'ELE': ['BioS', 'Chem', 'EaEn', 'EnTe', 'PhyM'],
                'JR': ['BSA', 'BSB', 'CHE', 'EES', 'ENG', 'MAT', 'PHY', 'TEC'],
                'SR': ['BSA', 'BSB', 'CHE', 'EES', 'ENG', 'MAT', 'PHY', 'TEC']
                }
        uut.list_all(cache_update_ttl=0)
        for fair in ['ncsef', 'ncsefreg1', 'ncsefreg3a', 'ncsefreg7', 'ncregtest']:
            for orgmethod in ['by category', 'by internal id', 'by judge', 'by student', 'by project']:
                uut.create_folder(f'/Automation/{fair}/{orgmethod}')
            for division in data.keys():
                uut.create_folder(f'/Automation/{fair}/by category/{division}', refresh=False)
                for category in data[division]:
                    uut.create_folder(f'/Automation/{fair}/by category/{division}/{category}', refresh=False)

        uut.list_all(cache_update_ttl=0)

    def test_create_folder_full(self):
        uut = NCSEFGoogleDrive()
        uut.create_folder('/Automation/ncregtest/by internal id/53240')
        uut.create_folder('/Automation/ncregtest/by internal id/53240/ISEF 1')

    def test_find_file(self):
        fullpath = "/Automation/ncsef"
        id = '1l704Kp_kNVsPT9Idx-AuLb2cYUYaYOjL'
        uut = NCSEFGoogleDrive()
        # find a node by fullpath name
        nodeid, parentid, parentpath, title, isafolder = uut._find_file(fullpath)
        self.assertEqual(id, nodeid)

        # remove that id , and search again without refresh, should not be found
        del uut.ids[id]
        # pprint( uut.ids[id])
        nodeid, parentid, parentpath, title, isafolder = uut._find_file(fullpath, refresh=False)
        self.assertIsNone(nodeid)
        # now allow refresh to happen, should be found
        nodeid, parentid, parentpath, title, isafolder = uut._find_file(fullpath, refresh=True)
        self.assertEqual(id, nodeid)

        f"/Automation/ncsef/by student/ Schmidt, Garrett",
        nodeid, parentid, parentpath, title, isafolder = uut._find_file(fullpath)
        print(nodeid)

    def test_jkl(self):
        uut = NCSEFGoogleDrive()
        uut.create_folder('/Automation/ncsef/by internal id/32773')
        nodeid, parentid, parentpath, title, isafolder = uut._find_file('/Automation/ncsef/by internal id/32773')
        print(f"nodeid:     {nodeid}")
        print(f"parentid:   {parentid}")
        print(f"parentpath: {parentpath}")
        print(f"parentpath: {title}")
        print(f"isafolder:  {isafolder}")

    def test_create_link(self):
        uut = NCSEFGoogleDrive()
        uut.create_shortcut('/Automation/ncsef/by internal id/54484/2022_NCSEF_Participant_Signature_Page.pdf',
                            '/Automation/ncsef/by student')
        return
        targetid = '18-zaJt213NcAS7xy0Il-bhfkidJm1X3V'
        parentid = '1jcV_rVYKHvfg6V50qwSPeSsavc-ovuU2'
        shortcut_metadata = {
            "name": "Shortcut",
            'mimeType': 'application/vnd.google-apps.shortcut',
            "parents": [{"id": parentid}],
            "shortcutDetails": {"targetId": targetid,
                                "targetMimeType": 'application/vnd.google-apps.folder'}
        }
        shortcut = uut.drive.CreateFile(shortcut_metadata)
        shortcut.Upload()
        pprint(shortcut)
        print(f"fileid:   {shortcut.get('id')}")
        print(f"targetId: {shortcut.get('targetId')}")
        print(f"targetMimeType: {shortcut.get('targetMimeType')}")


class NCSEF_prod_TestCases_operation(unittest.TestCase):

    def test_00_login(self):
        uut = STEMWizardAPI(configfile=configfile_prod)
        self.assertTrue(uut.authenticated)
        self.assertEqual(40, len(uut.token))
        self.assertGreaterEqual(len(uut.domain), 4)
        self.assertGreaterEqual(int(uut.region_id), 4000)

    def test_student_xls(self):
        uut = STEMWizardAPI(configfile=configfile_prod)
        filename, df = uut.export_list('student')
        self.assertGreater(len(filename), 27)
        self.assertTrue(os.path.exists(filename))
        self.assertGreaterEqual(df.shape[0], 3, 'fewer students than expected')
        self.assertGreaterEqual(df.shape[1], 33, 'fewer columns than expected')
        print(f"Students: {df.shape[0]}")

    def test_judge_xls(self):
        uut = STEMWizardAPI(configfile=configfile_prod)
        filename, df = uut.export_list('judge')
        print(df)
        self.assertGreater(len(filename), 20)
        self.assertTrue(os.path.exists(filename))
        self.assertGreaterEqual(df.shape[0], 50, 'fewer judges than expected')
        self.assertGreaterEqual(df.shape[1], 26, 'fewer columns than expected')
        print(f"Judges: {df.shape[0]}")

    def test_paymentStatus_xls(self):
        uut = STEMWizardAPI(configfile=configfile_prod)
        filename, df = uut.export_list('paymentStatus')
        # print(df)
        self.assertGreater(len(filename), 20)
        self.assertTrue(os.path.exists(filename))
        self.assertGreaterEqual(df.shape[0], 50, 'fewer judges than expected')
        self.assertGreaterEqual(df.shape[1], 26, 'fewer columns than expected')
        print(f"Judges: {df.shape[0]}")

    def test_volunteer_xls(self):
        uut = STEMWizardAPI(configfile=configfile_prod)
        filename, df = uut.export_list('volunteer')
        self.assertGreater(len(filename), 29)
        self.assertTrue(os.path.exists(filename))
        self.assertGreaterEqual(df.shape[0], 1, 'fewer volunteer than expected')
        self.assertGreaterEqual(df.shape[1], 14, 'fewer columns than expected')
        print(f"Volunteers: {df.shape[0]}")

    def test_student_file_sync(self):
        uut = STEMWizardAPI(configfile=configfile_prod, login_stemwizard=True, login_google=True)
        data = uut.studentSync(download=True, upload=True)


class devtest(unittest.TestCase):

    def test_getJudgesMaterials(self):
        uut = STEMWizardAPI(configfile=configfile_prod, login_stemwizard=True, login_google=False)
        data = uut.get_judges_materials()
        pprint(data)
        write_json_cache(data, 'caches/foo.json')

    def test_getFilesAndForms(self):
        uut = STEMWizardAPI(configfile=configfile_prod, login_stemwizard=True, login_google=False)
        data = uut.get_files_and_forms()
        pprint(data)
        write_json_cache(data, 'caches/foo.json')

    def test_studentSync(self):
        uut = STEMWizardAPI(configfile=configfile_prod, login_stemwizard=True, login_google=False)
        data = uut.studentSync(download=False, upload=False)

    def test_patch_team_filepaths(self):
        uut = STEMWizardAPI(configfile=configfile_prod, login_stemwizard=True, login_google=True)
        data = uut.studentSync(download=True, upload=True)

    def test_shortcut(self):
        from tqdm import tqdm
        uut = STEMWizardAPI(configfile=configfile_prod, login_stemwizard=False, login_google=True)
        from fileutils import read_json_cache
        data = read_json_cache('caches/student_data.json', max_cache_age=9999999)
        print(len(data))
        byp = dict()
        for d in data.values():
            byp[d['Project Number']] = d
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
                            #    def create_shortcut(self, fullpath_link_to, folder_to_put_link_in, title):

                            pass
                            uut.googleapi.create_shortcut(remote_filename, remote_dir, elements[-1])

    def test_c(self):
        uut = STEMWizardAPI(configfile=configfile_prod, login_stemwizard=True, login_google=False)
        uut.set_columns()

    def test_county(self):
        import pandas as pd
        from uszipcode import SearchEngine
        sr = SearchEngine()
        df = pd.read_excel('files/ncsef/student_list.xlsx')
        # df['c'] = df.apply(lambda x: max(len(x['a']), len(x['b'])), axis=1)
        rows = []
        for n, row in df.iterrows():
            if pd.isnull(row['ZIP']):
                row['County'] = ''
            else:
                zip = int(row['ZIP'])
                row['County'] = sr.by_zipcode(zip).county
            rows.append(row)
        df = pd.DataFrame.from_records(rows)
        print(df)
        df.to_excel('student_list.xlsx')


class NCSEF_prod_TestCases(unittest.TestCase):

    def test_student_data(self):
        uut = STEMWizardAPI(configfile=configfile_prod,
                            login_stemwizard=True, login_google=True)

        student_data = uut.studentSync(download=True, upload=True)

    def test_google_sync(self):
        uut = STEMWizardAPI(configfile=configfile_prod,
                            login_stemwizard=False, login_google=True)
        print(uut.googleapi.dump())
        # from fileutils import read_json_cache
        # data = read_json_cache('caches/student_data.json', max_cache_age=9000)
        # uut.sync_to_google(data)


if __name__ == '__main__':
    unittest.main()
