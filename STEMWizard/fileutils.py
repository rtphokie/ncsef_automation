import json
import olefile
import pandas as pd
import time
import os
from .logstuff import get_logger

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'}

logger = get_logger('cache_json')


def write_json_cache(cache, cache_filename):
    '''
    writes object to human readable JSON cache, forces to STR when necessary to seamlessly handle date objects
    :param cache: object to cache
    :param cache_filename: filename to use
    :return: nothing
    '''
    fp = open(cache_filename, 'w')
    json.dump(cache, fp, indent=2, default=str)
    fp.close()
    logger.debug(f"wrote to {cache_filename}")


def read_json_cache(cache_filename, max_cache_age=600):
    '''
    reads from specified filename, returns empty dictionary if the file is too old
    :param cache_filename: json filename
    :param max_cache_age: maximum age in seconds
    :return: object (usually a dictionary) read from cache, empty dictionary if file is not found or too old
    '''
    try:
        if os.path.isfile(cache_filename):
            st = os.stat(cache_filename)
            age = (time.time() - st.st_mtime)
        else:
            logger.debug(f"could not read a {cache_filename}")
            age = 999999999999999
        if age < max_cache_age:
            fp = open(cache_filename, 'r')
            cache = json.loads(fp.read())
            fp.close()
            logger.debug(f"read {round(age,1)} min old {cache_filename}")
        else:
            logger.debug(f"{round(age,1)} min old {cache_filename} needs to be recreated")
            cache = {}
    except Exception as e:
        print(e)
        logger.error(e)
        cache = {}
    return cache

#
# def xlsfile_to_df(local_filename):
#     ole = olefile.OleFileIO(local_filename)
#     df = pd.read_excel(ole.openstream('Workbook'), engine='xlrd')
#     return df
#
#
# def safe_rm_file(local_filename):
#     try:
#         os.remove(local_filename)
#     except OSError as e:
#         print(f'failed to remove {local_filename} {e}')
