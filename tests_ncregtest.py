

class NCRegTestTestCases(unittest.TestCase):

    def test_setcolumns(self):
        # results are not really testable in this context, so looking for exceptions here
        uut = STEMWizardAPI(configfile=configfile)
        for listname in ['judge', 'student', 'volunteer']:
            uut.set_columns(listname=listname)

    def test_login(self):
        uut = STEMWizardAPI(configfile=configfile)
        self.assertTrue(uut.authenticated)
        self.assertEqual(40, len(uut.token))
        self.assertGreaterEqual(len(uut.domain), 4)
        self.assertGreaterEqual(int(uut.region_id), 4000)

    def test_student_xls(self):
        uut = STEMWizardAPI(configfile=configfile)
        filename, df = uut.export_list('student')
        print(filename)
        self.assertGreater(len(filename), 30)
        self.assertTrue(os.path.exists(filename))
        self.assertGreaterEqual(df.shape[0], 3, 'fewer students than expected')
        self.assertGreaterEqual(df.shape[1], 33, 'fewer columns than expected')

    def test_judge_xls_prod(self):
        uut = STEMWizardAPI(configfile=configfile_prod)
        filename, df = uut.export_list('judge')
        # print(df)
        self.assertGreater(len(filename), 20)
        self.assertTrue(os.path.exists(filename))
        self.assertGreaterEqual(df.shape[0], 1, 'fewer judges than expected')
        self.assertGreaterEqual(df.shape[1], 26, 'fewer columns than expected')

    def test_judge_xls(self):
        uut = STEMWizardAPI(configfile=configfile)
        filename, df = uut.export_list('judge')
        print(df)
        # self.assertGreater(len(filename), 30)
        # self.assertTrue(os.path.exists(filename))
        # self.assertGreaterEqual(df.shape[0], 1, 'fewer judges than expected')
        # self.assertGreaterEqual(df.shape[1], 26, 'fewer columns than expected')

    def test_volunteer_xls(self):
        uut = STEMWizardAPI(configfile=configfile)
        filename, df = uut.export_list('volunteer')
        self.assertGreater(len(filename), 30)
        self.assertTrue(os.path.exists(filename))
        self.assertGreaterEqual(df.shape[0], 1, 'fewer volunteer than expected')
        self.assertGreaterEqual(df.shape[1], 14, 'fewer columns than expected')

    def test_student_data(self):
        uut = STEMWizardAPI(configfile=configfile)

        data = uut.getStudentData_by_category(fileinfo=True, download=True)
        pprint(data)
        return
        for id, node in data.items():
            uut.googleapi.create_folder(f"/Automation/{uut.domain}/by internal id/{id}")
            for formname, formdata in node['files'].items():
                uut.googleapi.create_folder(f"/Automation/{uut.domain}/by internal id/{id}/{formname}")
                # print(formname, formdata['file_name'])
                localpath = f"files/{id}/{formname}/{formdata['file_name']}"
                remotepath = f"/Automation/{uut.domain}/by internal id/{id}/{formname}/{formdata['file_name']}"
                uut.googleapi.create_file(localpath, remotepath)

            # uut.googleapi.create_file()
        self.assertGreaterEqual(len(data), 3)
        self.assertGreaterEqual(len(data[list(data.keys())[0]]['files']), 5)

    def test_file_detail(self):
        uut = STEMWizardAPI(configfile=configfile)
        data = uut._student_file_detail(53240, 61630)
        self.assertGreaterEqual(len(data), 3)

    def test_export(self):
        uut = STEMWizardAPI(configfile=configfile)
        filename, df = uut.export_list(listname='judge')

