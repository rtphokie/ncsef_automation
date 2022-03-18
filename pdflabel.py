import copy
import glob
import io
import unittest
from os.path import exists
import os

from PyPDF2 import PdfFileWriter, PdfFileReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from tqdm import tqdm


def main(title, path):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.drawString(can._pagesize[0] * .45, can._pagesize[1] * .98, title)
    can.save()

    packet.seek(0)
    new_pdf = PdfFileReader(packet)

    try:
        existing_pdf = PdfFileReader(open(path, "rb"))
        page = existing_pdf.getPage(0)
        page.mergePage(new_pdf.getPage(0))
    except:
        page = None
    return page


class MyTestCase(unittest.TestCase):
    def test_something(self):
        output = PdfFileWriter()
        page1 = main('JR-MAT-004', 'files/ncsef/JR/MAT/JR-MAT-004/JR-MAT-004_Abstract.pdf')
        output.addPage(page1)
        page2 = main('JR-MAT-005', 'files/ncsef/JR/MAT/JR-MAT-005/JR-MAT-005_Abstract.pdf')
        output.addPage(page2)

        outputStream = open(f"dest.pdf", "wb")
        output.write(outputStream)
        outputStream.close()

    def test_foo(self):
        prevcat = None
        alloutput= PdfFileWriter()
        # for name in tqdm(sorted(glob.glob('files/ncsef/*/*/*/*Abst*'))):
        for name in tqdm(sorted(glob.glob('files/ncsef/SR/EES/*/*Abst*'))):
            _, _, div, cat, proj, filename = name.split('/')
            fn = f"all_abstracts_{div}_{cat}.pdf"
            if prevcat != cat:
                output = PdfFileWriter()
            prevcat = cat
            page = main(proj, name)
            if page is not None:
                try:
                    output.addPage(page)
                    alloutput.addPage(page)
                    outputStream = open(f"tmp.pdf", "wb")
                    output.write(outputStream)
                    outputStream.close()
                    os.rename('tmp.pdf', fn)
                except Exception as e:
                    print(f'skipping {filename} {e}')
        outputStream = open(f"all_abstracts.pdf", "wb")
        alloutput.write(outputStream)
        outputStream.close()
        print(fn)


if __name__ == '__main__':
    pass