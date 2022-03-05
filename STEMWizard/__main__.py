from . import STEMWizardAPI
if __name__ == '__main__':
    configfile_prod = 'stemwizardapi_ncsef.yaml'
    uut = STEMWizardAPI(configfile=configfile_prod, login_stemwizard=True, login_google=True)
    for listname in ['student', 'judge', 'volunteer']
        filename, df = uut.export_list(listname)
    student_data = uut.studentSync()