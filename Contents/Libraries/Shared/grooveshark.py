import sys
import httplib
import StringIO
import hashlib
import uuid
import random
import gzip
import time
if sys.version_info[1] >= 6: import json
else: import simplejson as json

class Grooveshark(object):
    def __init__(self):
        self.username           = ''
        self.password           = ''
        self.token              = None
        self.queue              = None
        self.token_timeout      = 1200
        self.user_id            = 0
        self.time               = 0
        self.user               = str(uuid.uuid4())
        self.session            = hashlib.md5(self.user.encode('utf-8')).hexdigest()
        self.secret             = hashlib.md5(self.session.encode('utf-8')).hexdigest()
        self.url                = 'grooveshark.com'
        self.stream_url         = 'http://%s/stream.php?streamKey=%s'
        self.artist_base_url    = 'http://images.gs-cdn.net/static/artists/'
        self.album_base_url     = 'http://images.gs-cdn.net/static/albums/'
        self.playlist_base_url  = 'http://images.gs-cdn.net/static/playlists/'
        self.broadcast_base_url = 'http://images.gs-cdn.net/static/broadcasts/'
        self.users_base_url     = 'http://images.gs-cdn.net/static/users/'
        self.no_artist_url      = 'http://images.gs-cdn.net/static/artists/500_artist.png'
        self.no_album_url       = 'http://images.gs-cdn.net/static/albums/500_album.png'
        self.no_user_url        = 'http://images.gs-cdn.net/static/users/500_user.png'
        self.country            = {'ID': 221, 'CC1': 0, 'CC2': 0, 'CC3': 0, 'CC4': 0, 'DMA': 0, 'IPR': 0}
        self.header             = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; rv:9.0.1) Gecko/20100101 Firefox/9.0.1',
                                   'Referer':'http://%s' % (self.url),
                                   'Accept-Encoding': 'gzip',
                                   'Content-Type': 'application/json'}
        self.clients            = {'htmlshark':  {'version': '20130520', 'token': 'nuggetsOfBaller'},
                                   'jsqueue':    {'version': '20130520', 'token': 'chickenFingers'},
                                   'mobileshark':{'version': '20120830', 'token': 'gooeyFlubber'}}
        self._initiateQueue()

    def _initiateQueue(self):
        self.queue = self._request('initiateQueue', None, 'jsqueue')

    def _header(self, method, client='htmlshark'):
        headers = {'privacy': 0,
                   'uuid': self.user,
                   'clientRevision': self.clients[client]['version'],
                   'session': self.session,
                   'client': client,
                   'country': self.country}

        if method != 'getCommunicationToken':
            headers['token'] = self._getCommunicationToken(method, client)

        return headers

    def _request(self, method, parameters, client='htmlshark'):
        p = {'parameters': parameters, 'header': self._header(method, client), 'method': method}
        conn = httplib.HTTPSConnection(self.url)
        conn.request('POST', '/more.php?' + method, json.JSONEncoder().encode(p), self.header)
        result = json.JSONDecoder().decode(gzip.GzipFile(fileobj=(StringIO.StringIO(conn.getresponse().read()))).read())
        if 'result' in result:
            return result['result']
        else:
            return result

    def _getCommunicationToken(self, method='getCommunicationToken', client='htmlshark'):
        if time.time() - self.time > self.token_timeout:
            self.time = time.time()
            self.token = self._request('getCommunicationToken', {'secretKey': self.secret})

        random_value = ''.join([random.choice('0123456789abcdef') for i in range(6)])
        return random_value + hashlib.sha1('%s:%s:%s:%s' % (method, self.token, self.clients[client]['token'], random_value)).hexdigest()

    def isAuthenticated(self):
        if self.user_id > 0:
            return True
        else:
            return False

    def authenticateUser(self, username, password):
        self.username = username
        self.password = password
        self.user_id = self._request('authenticateUser', {'username': self.username, 'password': self.password})['userID']

    def userGetSongsInLibrary(self, page=0, user=None):
        user = self.user_id if user == None else user
        return self._request('userGetSongsInLibrary', {'page': page, 'userID': user})

    def getFavorites(self, ofWhat='Songs', user=None):
        user = self.user_id if user == None else user
        return self._request('getFavorites', {'userID': user, 'ofWhat': ofWhat})

    def userGetPlaylists(self, user=None):
        user = self.user_id if user == None else user
        return self._request('userGetPlaylists', {'userID': user})

    def playlistGetSongs(self, id):
        return self._request('playlistGetSongs', {'playlistID': id})

    def getTopLevelTags(self):
        return self._request('getTopLevelTags', {})

    def popularGetSongs(self, type='daily'):
        return self._request('popularGetSongs', {'type': type})

    def getPageInfoByIDType(self, id, tag='tag'):
        return self._request('getPageInfoByIDType', {'id': id, 'type': tag})

    def getTopBroadcastsCombined(self):
        return self._request('getTopBroadcastsCombined', {})

    def getAutocompleteEx(self, query):
        parameters = {'query': query,
                      'type': 'combined'}

        return self._request('getAutocompleteEx', parameters)

    def getResultsFromSearch(self, query):
        parameters = {'query' : query,
                      'type' : ['Songs', 'Artists', 'Albums'],
                      'guts' : 0,
                      'ppOverride' : False}

        return self._request('getResultsFromSearch', parameters)

    def albumGetAllSongs(self, id):
        return self._request('albumGetAllSongs', {'albumID': id})

    def artistGetAllAlbums(self, id):
        return self._request('artistGetAllAlbums', {'artistID': id})

    def getStreamKeyFromSongIDEx(self, id):
        parameters = {'mobile': False,
                      'prefetch': False,
                      'songID': id,
                      'type': 32,
                      'country': self.country}

        data = self._request('getStreamKeyFromSongIDEx', parameters, 'jsqueue')
        if len(data) > 0:
            return self.stream_url % (data['ip'], data['streamKey']), data['streamServerID'], data['streamKey']
        return '','',''

    def getMobileBroadcastURL(self, id, hq=False):
        data = self._request('getMobileBroadcastURL', {'broadcastID': id}, 'mobileshark')
        q = '' if hq else '&cl=552960000'
        if data != False:
            return data['url'].replace('\\', '') + '?sid=' + data['key'] + q

    def userAddSongsToLibrary(self, songs):
        return self._request('userAddSongsToLibrary', {'songs': songs})

    def favorite(self, song):
        return self._request('favorite', {'what': 'Song', 'ID': song[0]['songID'], "details": song[0]})

    def playlistAddSongToExistingEx(self, playlistId, song):
        return self._request('playlistAddSongToExistingEx', {'playlistID': playlistId, 'songID': song[0]['songID'], "song": song[0]})

    def markSongDownloadedEx(self, id, streamServerID, streamKey):
        parameters = {'songID': id,
                      'streamServerID': streamServerID,
                      'streamKey': streamKey}

        return self._request('markSongDownloadedEx', parameters, 'jsqueue')

    def markSongQueueSongPlayed(self, id, streamServerID, streamKey):
        parameters = {'songID' : id,
                      'songQueueSongID' : 1,
                      'streamKey' : streamKey,
                      'songQueueID' : self.queue,
                      'streamServerID' : streamServerID}

        return self._request('markSongQueueSongPlayed', parameters, 'jsqueue')

    def markStreamKeyOver30Seconds(self, id, streamServerID, streamKey):
        parameters = {'songQueueID': self.queue,
                      'songID': id,
                      'streamServerID': streamServerID,
                      'songQueueSongID': 1,
                      'streamKey': streamKey}

        return self._request('markStreamKeyOver30Seconds', parameters, 'jsqueue')

    def markSongComplete(self, id, streamServerID, streamKey):
        parameters = {'songID': id,
                      'streamServerID': streamServerID,
                      'streamKey': streamKey}

        return self._request('markSongComplete', parameters, 'jsqueue')