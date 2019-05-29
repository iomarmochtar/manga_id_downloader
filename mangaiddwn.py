__author__ = ('Imam Omar Mochtar', 'iomarmochtar@gmail.com')

import re
import os
import ssl
import sys
import zipfile
from argparse import ArgumentParser

try:
    from urllib.request import Request, urlopen, HTTPError  # Python 3
    raw_input = input
except ImportError:
    from urllib2 import Request, urlopen, HTTPError  # Python 2

# abaikan self sign certificate 
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


class MangaDownloader(object):
    
    base_url = 'https://www.komikgue.com/manga'
    user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0'
    img_re = re.compile(r'<img\s+class=["\']img-responsive["\'].*?src=["\'](.*?)["\']')
    index_name = 'index.html'
    root_folder = 'mangas'

    process_chapter = None
    manga = None
    begin = None
    end = None
    is_latest = False
    base_dir = None

    def __init__(self, manga, chapter_begin=None, 
            chapter_end=None, destination=None, is_latest=False):
        self.manga = manga
        self.begin = chapter_begin
        self.end = chapter_end
        self.is_latest = is_latest
        self.base_dir = os.path.join(
                os.getcwd() if not destination else destination,
                self.root_folder 
                )

        if not os.path.isdir(self.base_dir):
            os.mkdir(self.base_dir)

        os.chdir(self.base_dir)

    def get_chapter_url(self):
        chapter_uri = self.chapters[int(self.process_chapter)]
        return os.path.join(
                    self.base_url,
                    self.manga,
                    chapter_uri,
                    '1'
                )

    def download(self, url, dwn_file=None, base_dir=None):
        if not dwn_file:
            dwn_file = os.path.basename(url)

        if base_dir:
            dwn_file = os.path.join(base_dir, dwn_file)

        request = Request(url, headers={'User-Agent': self.user_agent})
        contents = urlopen(request)

        with open(dwn_file, 'wb') as f:
            f.write(contents.read())
        return dwn_file

    def get_images(self):
        images = []
        for line in open(self.index_name, 'r').readlines():
            line = line.strip()
            match = self.img_re.search(line)
            if not match:
                continue
            images.append(match.group(1))

        return images

    def log(self, txt):
        chapter = ':{}'.format(self.process_chapter) if self.process_chapter else ''
        print('[{}{}] {}'.format(self.manga, chapter, txt))

    __chapters = {}
    @property
    def chapters(self):
        # listing chapters pada manga yang dipilih
        if self.__chapters:
            return self.__chapters
        chapter_listing_page = os.path.join(self.base_url, self.manga)
        self.log('Download halaman home page manga')
        try:
            self.download(chapter_listing_page, self.index_name)
        except HTTPError:
            self.log_err('Manga tidak ditemukan')

        manga_dir = os.path.join(self.base_dir, self.manga)
        if not os.path.isdir(manga_dir):
            os.mkdir(manga_dir)

        text = open(self.index_name, 'r').read()

        regex = r'{}\/(\d+)[\'"]'.format(self.manga)
        chapters = re.findall(regex, text)
        leading_zero_re = re.compile('^0+')
        def clean(num):
            cleaned = leading_zero_re.sub('', num) 
            return (int(cleaned), num)

        self.__chapters = dict(map(clean, chapters))
        return self.__chapters

    @classmethod
    def log_err(self, txt, err_code=1):
        print('[Error] {}'.format(txt))
        sys.exit(err_code)

    def download_chapter(self, chapter):
        self.process_chapter = str(chapter)

        manga_dir = os.path.join(self.base_dir, self.manga)

        archive_file = '{}_{}.zip'.format(chapter, self.manga)
        archive_path = os.path.join(manga_dir, archive_file)

        if os.path.isfile(archive_path):
            self.log('Manga archive sudah tersedia => {}'.format(archive_path))
            return

        if chapter not in self.chapters:
            self.log('Tidak tersedia')
            return

        self.log('Scrapping gambar situs referensi')
        chapter_url = self.get_chapter_url()
        try:
            self.download(chapter_url, self.index_name)
        except HTTPError:
            self.log('Halaman tidak ditemukan {}'.format(chapter_url))
            return

        image_urls = self.get_images()

        if not image_urls:
            self.log('Tidak ada gambar yang ditemukan pada => {}'.format(chapter_url))
            return
       
        os.chdir(manga_dir)
        images = []
        for image_url in image_urls:
            images.append( self.download(image_url) )
            self.log('Download progress {}/{}'.format(len(images), len(image_urls)))

        zipf = zipfile.ZipFile(archive_file, 'w')
        for image in images:
            zipf.write(image)
            os.remove(image)

        os.chdir(self.base_dir)
        self.log('Selesai => {}'.format(archive_path))

    def main(self):

        if self.is_latest:
            chapters = self.chapters
            latest = sorted(chapters.keys())[-1]
            self.download_chapter(latest)

        # 1 chapter
        elif self.begin and not self.end:
            self.download_chapter(self.begin)

        # dengan range
        elif self.begin and self.end:
            for chapter in range(self.begin, self.end+1):
                self.download_chapter(chapter)

        # semua chapter yang ada
        elif not self.begin and not self.end:
            for chapter in self.chapters.keys():
                self.download_chapter(chapter)

        if os.path.isfile(self.index_name):
            os.remove(self.index_name)

if __name__ == '__main__':
    parser = ArgumentParser(description='Manga terjemahan indonesia downloader')
    parser.add_argument('-m', '--manga', help='Nama manga', action='store', required=True)
    parser.add_argument('-c', '--chapter', help='Chapter yang akan di download', action='store')
    parser.add_argument('-y', '--yes', 
            help='Otomatis memilih yes/y jika ada konfirmasi', action='store_true', default=False)
    parser.add_argument('-l', '--latest', 
            help='Akan mengunduh chapter terbaru saja', action='store_true', default=False)
    parser.add_argument('-d', '--destination', 
            help='Destinasi folder', action='store')

    args = parser.parse_args()
    chapter_begin = args.chapter 
    chapter_end = None 
    manga = args.manga
    separator = ':'
    is_latest = args.latest 

    if is_latest and args.chapter:
        MangaDownloader.log_err('Tidak bisa digabungkan dengan antara download chapter dengan spesifik chapter')

    # jika set chapter dengan range 
    if chapter_begin and not chapter_begin.isdigit():
        if chapter_begin.find(separator) == -1:
            MangaDownloader.log_err('Gunakan {} sebagai separator'.format(separator))

        breaks = chapter_begin.split(separator)
        if len(breaks) != 2:
            MangaDownloader.log_err('Hanya gunakan satu separator untuk pemisah')

        chapter_begin, chapter_end = [ int(x) for x in breaks ]
        if chapter_begin > chapter_end:
            MangaDownloader.log_err('Chapter awal lebih besar !!!')
    elif chapter_begin:
        chapter_begin = int(chapter_begin)

    if not chapter_begin and not chapter_end and not args.yes and not is_latest:
        while True:
            prompt = raw_input('Anda akan menunduh semua chapter untuk manga {} ? (y/n)'.format(args.manga))
            prompt_l = prompt.lower()
            if prompt_l == 'y':
                break
            elif prompt_l == 'n':
                sys.exit(0)
            else:
                print('Opsi tidak dikenali => {}'.format(prompt))

    MangaDownloader(manga, chapter_begin, chapter_end, args.destination, is_latest).main()
