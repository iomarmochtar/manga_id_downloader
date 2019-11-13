__author__ = ('Imam Omar Mochtar', 'iomarmochtar@gmail.com')

# testing
import gevent.monkey
gevent.monkey.patch_all()
import gevent
from gevent.pool import Pool 

from mangaiddwn import MangaDownloader

class ConcurrentDwn(MangaDownloader):

    def _imgdwn(self, url, total, img_container):
        img_container.append( self.download(url) )
        self.log('Download progress {}/{}'.format( len(img_container), total ) )

    def download_image_adapter(self, urls, img_container):	
        pool = Pool(self.args.concurrent)
        for url in urls:
            pool.spawn(self._imgdwn, url, len(urls), img_container)
        pool.join()    

    def cmd_parser(self):
        parser = MangaDownloader.cmd_parser(self)
        parser.add_argument('-n', '--concurrent', 
            help='Jumlah concurrent connection ketika mengunduh',
            type=int,
            default=10,
            action='store'
            )
        return parser

if __name__ == '__main__':
    ConcurrentDwn().main()
