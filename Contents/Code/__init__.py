import time
import datetime
from grooveshark import Grooveshark

################################################################################
TITLE          = 'Grooveshark'
ART            = 'art-default.jpg'
ICON           = 'icon-default.png'
SEARCH_ICON    = 'icon-search.png'
PREFS_ICON     = 'icon-prefs.png'
PREFIX         = '/music/grooveshark'
shark          = None

def toInt(s):
    try:
        return int(s)
    except ValueError:
        return int(float(s))

def sortInt(s):
    if s == None or s == '0' or s == '1901':
        return 10000
    return int(s)

################################################################################
def Start():
    DirectoryObject.thumb  = R(ICON)
    ObjectContainer.art    = R(ART)
    ObjectContainer.title1 = TITLE

################################################################################
@handler(PREFIX, TITLE, art=ART, thumb=ICON)
def Main():
    global shark
    if shark == None:
        shark = Grooveshark()

    oc = ObjectContainer(title2=TITLE)

    if Prefs['username'] and Prefs['password']:
        shark.authenticateUser(Prefs['username'], Prefs['password'])
        if shark.isAuthenticated():
            oc.add(DirectoryObject(key=Callback(Collection), title=L('Collection')))
            oc.add(DirectoryObject(key=Callback(Favorites), title=L('Favorites')))
            oc.add(DirectoryObject(key=Callback(Playlists), title=L('Playlists')))
            oc.add(DirectoryObject(key=Callback(Followers), title=L('Followers')))

    oc.add(DirectoryObject(key=Callback(Genres), title=L('Genres')))
    oc.add(DirectoryObject(key=Callback(Broadcasts), title=L('Broadcasts')))
    oc.add(DirectoryObject(key=Callback(Popular), title=L('Popular')))
    oc.add(InputDirectoryObject(key=Callback(Search), title=L('Search'), prompt=L('Search for'), thumb=R(SEARCH_ICON)))
    oc.add(PrefsObject(title=L('Preferences'), thumb=R(PREFS_ICON)))
    return oc

################################################################################
@route(PREFIX + '/collection', page=int)
def Collection(page=0, id=None):
    oc = ObjectContainer(title2=L('Collection'))

    library = shark.userGetSongsInLibrary(page, id)
    for song in sorted(library['Songs'], key = lambda x: (x.get('ArtistName', None), x.get('AlbumName', None), sortInt(x.get('TrackNum')))):
        oc.add(CreateTrackObject(song=song))

    if library['hasMore'] == True:
        oc.add(NextPageObject(key=Callback(Collection, page=page+1, id=id)))

    return oc

################################################################################
@route(PREFIX + '/favorites')
def Favorites(id=None):
    oc = ObjectContainer(title2=L('Favorites'))

    favorites = shark.getFavorites('Songs', id)
    for song in sorted(favorites, key = lambda x: (x.get('ArtistName', None), x.get('AlbumName', None), sortInt(x.get('TrackNum')))):
        oc.add(CreateTrackObject(song=song))

    return oc

################################################################################
@route(PREFIX + '/playlists', song=dict)
def Playlists(id=None, song=None):
    oc = ObjectContainer(title2=L('Playlists'))

    playlists = shark.userGetPlaylists(id)
    for playlist in playlists['Playlists']:
        # This block is for normal selection of playlists
        if song == None:
            do = DirectoryObject(key = Callback(PlaylistsSubMenu, title=playlist['Name'], id=playlist['PlaylistID']), title=playlist['Name'])
            if 'Picture' in playlist and playlist['Picture'] != None:
                do.thumb = shark.playlist_base_url + '200_' + playlist['Picture']
            else:
                do.thumb = shark.no_album_url

            oc.add(do)
        # This block is for when a song is being added to a playlist
        else:
            oc.add(DirectoryObject(key=Callback(AddToCollection, song=song, type=2, playlistId=playlist['PlaylistID']), title=playlist['Name']))


    return oc

################################################################################
@route(PREFIX + '/followers')
def Followers():
    oc = ObjectContainer(title2=L('Followers'))
    users = shark.getFavorites('Users')
    for user in users:
        name = '{0} {1}'.format(user['FName'], user['LName'])
        thumb = shark.users_base_url + user['Picture']
        oc.add(DirectoryObject(key=Callback(FollowersSubMenu, id=user['UserID'], name=name), title=name, thumb=thumb))

    return oc

################################################################################
@route(PREFIX + '/genres')
def Genres():
    oc = ObjectContainer(title2=L('Genres'))

    tags = shark.getTopLevelTags()
    for tag in tags:
        oc.add(DirectoryObject(key = Callback(GenreSubMenu, title=tag['Tag'], id=tag['TagID']), title=tag['Tag']))

    return oc

################################################################################
@route(PREFIX + '/broadcasts')
def Broadcasts():
    oc = ObjectContainer(title2=L('Broadcasts'))

    broadcasts = shark.getTopBroadcastsCombined()
    for key, value in sorted(broadcasts.iteritems(), key = lambda x: ('subscribers_count' in x[1], x[1].get('subscribers_count')), reverse = True):
        if 'n' in value and 's' in value:
            if 'active' in value['s']:
                if 'b' in value['s']['active']:
                    if 'tk' in value['s']['active']['b'] and value['s']['active']['b']['tk']:
                        song = {'SongID': value['s']['active']['b']['tk'],
                                'ArtistName': value['n'],
                                'Name': value['s']['active']['b']['sN'] + ' by ' + value['s']['active']['b']['arN'],
                                'BroadcastId': key.split(':')[1],
                                'CoverArtFilename': shark.no_user_url,
                                'EstimateDuration': None}

                        if 'i' in value and value['i'] != None:
                            song['CoverArtFilename'] = shark.broadcast_base_url + value['i']
                        elif 'users' in value and len(value['users']) > 0 and 'Picture' in value['users'][0] and value['users'][0]['Picture'] != None:
                            song['CoverArtFilename'] = shark.users_base_url + value['users'][0]['Picture']

                        oc.add(CreateTrackObject(song=song))

    return oc

################################################################################
@route(PREFIX + '/popular')
def Popular():
    oc = ObjectContainer(title2=L('Popular'))
    oc.add(DirectoryObject(key = Callback(PopularSubMenu, title=L('Popular Today'), type='daily'), title=L('Popular Today')))
    oc.add(DirectoryObject(key = Callback(PopularSubMenu, title=L('Popular This Week'), type='weekly'), title=L('Popular This Week')))
    oc.add(DirectoryObject(key = Callback(PopularSubMenu, title=L('Popular This Month'), type='monthly'), title=L('Popular This Month')))
    return oc

################################################################################
@route(PREFIX + '/playlistssubmenu')
def PlaylistsSubMenu(title, id):
    oc = ObjectContainer(title2=title)

    songs = shark.playlistGetSongs(id)
    for song in songs['Songs']:
            oc.add(CreateTrackObject(song=song))

    return oc

################################################################################
@route(PREFIX + '/genresubmenu')
def GenreSubMenu(title, id):
    oc = ObjectContainer(title2=title)
    oc.add(DirectoryObject(key = Callback(GenrePlayMenu, title=title, id=id), title=L('Play') + ' ' + title))
    oc.add(DirectoryObject(key = Callback(GenrePlayMenu, title=L('Related Genres') + ': ' + title, id=id, type='related'), title=L('Related Genres')))
    return oc

################################################################################
@route(PREFIX + '/genreplaymenu')
def GenrePlayMenu(title, id, type=None):
    oc = ObjectContainer(title2=title)

    info = shark.getPageInfoByIDType(id)
    if type == 'related':
        for song in info['Data']['RelatedTags']:
            oc.add(DirectoryObject(key = Callback(GenrePlayMenu, title=song['TagName'], id=song['TagID']), title=L('Play') + ' ' + song['TagName']))

    else:
        for song in info['Data']['Songs']:
            oc.add(CreateTrackObject(song=song))

    return oc

################################################################################
@route(PREFIX + '/popularsubmenu')
def PopularSubMenu(title, type):
    oc = ObjectContainer(title2=title)

    songs = shark.popularGetSongs(type)
    for song in songs['Songs']:
        oc.add(CreateTrackObject(song=song))

    return oc

################################################################################
@route(PREFIX + '/followerssubmenu')
def FollowersSubMenu(id, name):
    oc = ObjectContainer(title2=name)
    oc.add(DirectoryObject(key=Callback(Collection, id=id), title=L('Collection')))
    oc.add(DirectoryObject(key=Callback(Favorites, id=id), title=L('Favorites')))
    oc.add(DirectoryObject(key=Callback(Playlists, id=id), title=L('Playlists')))
    return oc

################################################################################
@route(PREFIX + '/search')
def Search(query):
    oc = ObjectContainer(title2=L('Search Results'))

    results = shark.getResultsFromSearch(query)
    for key, values in results['result'].iteritems():
        if key == 'Artists':
            for artist in values:
                artistObj = DirectoryObject(
                    key=Callback(ShowArtistOptions, name=artist['Name'], id=artist['ArtistID']),
                    title=artist['Name'],
                    summary=L('Artist')
                )

                if 'CoverArtFilename' in artist and artist['CoverArtFilename'] != None and ''.join(artist['CoverArtFilename'].split()) != '':
                    artistObj.thumb=shark.artist_base_url + artist['CoverArtFilename']
                else:
                    artistObj.thumb=shark.no_artist_url

                oc.add(artistObj)

        elif key == 'Songs':
            for song in values:
                if 'Name' in song:
                    title = song['Name']
                elif 'SongName' in song:
                    title = song['SongName']
                else:
                    title = L('No title provided')

                do = DirectoryObject(
                    key=Callback(AddItemMenu, title=title, song=song),
                    title=title,
                    summary=L('Song')
                )

                if 'CoverArtFilename' in song and song['CoverArtFilename'] != None and ''.join(song['CoverArtFilename'].split()) != '':
                    if song['CoverArtFilename'].startswith('http'):
                        do.thumb = song['CoverArtFilename']
                    else:
                        do.thumb = shark.album_base_url + song['CoverArtFilename']
                else:
                    do.thumb = shark.no_album_url

                oc.add(do)

        elif key == 'Albums':
            for album in values:
                albumObj = DirectoryObject(
                    key=Callback(ShowAlbumOptions, name=album['AlbumName'], id=album['AlbumID']),
                    title=album['AlbumName'],
                    summary=L('Album')
                )

                if 'CoverArtFilename' in album and album['CoverArtFilename'] != None and ''.join(album['CoverArtFilename'].split()) != '':
                    albumObj.thumb=shark.album_base_url + album['CoverArtFilename']
                else:
                    albumObj.thumb=shark.no_album_url

                oc.add(albumObj)

    return oc

################################################################################
@route(PREFIX + '/additemmenu', song=dict)
def AddItemMenu(title, song):
    oc = ObjectContainer(title2='%s %s' % (L('Options for'), title))
    oc.add(CreateTrackObject(song=song))
    oc.add(DirectoryObject(key=Callback(AddToCollection, song=song, type=0), title='%s %s' % (L('Add to'), L('Collection'))))
    oc.add(DirectoryObject(key=Callback(AddToCollection, song=song, type=1), title='%s %s' % (L('Add to'), L('Favorites'))))
    oc.add(DirectoryObject(key=Callback(Playlists, song=song), title='%s %s' % (L('Add to'), L('Playlists'))))

    return oc

################################################################################
@route(PREFIX + '/addtocollection', song=dict, type=int)
def AddToCollection(song, type, playlistId=None):
    data = [{
        "songID": song.get('SongID', 0),
        "songName": song.get('SongName', ''),
        "albumID": song.get('AlbumID', ''),
        "albumName": song.get('AlbumName', ''),
        "artistID": song.get('ArtistID', 0),
        "artistName": song.get('ArtistName', ''),
        "artFilename": song.get('ArtistCoverArtFilename', ''),
        "track": song.get('TrackNum', 0),
        "isVerified": song.get('IsVerified', 0)
    }]

    if type == 0:
        shark.userAddSongsToLibrary(data)
    elif type == 1:
        shark.favorite(data)
    elif type == 2:
        shark.playlistAddSongToExistingEx(playlistId, data)

    return ObjectContainer(header=L('Adding Song'), message=L('Adding Success'))

################################################################################
@route(PREFIX + '/showartistoptions')
def ShowArtistOptions(name, id):
    oc = ObjectContainer(title2=name)

    albums = shark.artistGetAllAlbums(id)
    for album in sorted(albums['albums'], key = lambda x: sortInt(x.get('Year'))):
        albumObj = DirectoryObject(
            key=Callback(ShowAlbumOptions, name=album['Name'], id=album['AlbumID']),
            title=album['Name']
        )

        if 'CoverArtFilename' in album and album['CoverArtFilename'] != None and ''.join(album['CoverArtFilename'].split()) != '':
            albumObj.thumb=shark.album_base_url + album['CoverArtFilename']
        else:
            albumObj.thumb=shark.no_album_url

        oc.add(albumObj)

    return oc

################################################################################
@route(PREFIX + '/showalbumoptions')
def ShowAlbumOptions(name, id):
    oc = ObjectContainer(title2=name)

    songs = shark.albumGetAllSongs(id)
    for song in sorted(songs, key = lambda x: sortInt(x.get('TrackNum'))):
        oc.add(CreateTrackObject(song=song))

    return oc

################################################################################
@route(PREFIX + '/createtrackobject', song=dict)
def CreateTrackObject(song, include_container=False):
    media_obj = MediaObject(
        audio_codec = AudioCodec.MP3,
        container = 'mp3'
    )
    track_obj = TrackObject(
        key = Callback(CreateTrackObject, song=song, include_container=True),
        rating_key = song['SongID']
    )

    if 'Name' in song:
        track_obj.title = song['Name']
    elif 'SongName' in song:
        track_obj.title = song['SongName']
    else:
        track_obj.title = L('No title provided')

    if 'BroadcastId' in song:
        media_obj.add(PartObject(key = Callback(GetBroadcastURL, id=song['BroadcastId'], ext='mp3')))
    else:
        media_obj.add(PartObject(key = Callback(GetStreamURL, id=song['SongID'], ext='mp3')))

    if 'ArtistName' in song and song['ArtistName'] != None:
        track_obj.artist = song['ArtistName']

    if 'AlbumName' in song and song['AlbumName'] != None:
        track_obj.album = song['AlbumName']

    if 'TrackNum' in song and song['TrackNum'] != None:
        track_obj.index = int(song['TrackNum'])

    if 'EstimateDuration' in song and song['EstimateDuration'] != None:
        track_obj.duration = toInt(song['EstimateDuration']) * 1000

    if 'CoverArtFilename' in song and song['CoverArtFilename'] != None and ''.join(song['CoverArtFilename'].split()) != '':
        if song['CoverArtFilename'].startswith('http'):
            track_obj.thumb = song['CoverArtFilename']
        else:
            track_obj.thumb = shark.album_base_url + song['CoverArtFilename']
    else:
        track_obj.thumb = shark.no_album_url

    track_obj.add(media_obj)

    if include_container:
        return ObjectContainer(objects=[track_obj])
    else:
        return track_obj

################################################################################
@route(PREFIX + '/getstreamurl.mp3')
def GetStreamURL(id):
    url, server, key = shark.getStreamKeyFromSongIDEx(id)
    if url:
        Thread.Create(MarkSongs, id=id, server=server, key=key)
        return Redirect(url)
    else:
        return Redirect('')

################################################################################
@route(PREFIX + '/getbroadcasturl.mp3')
def GetBroadcastURL(id):
    url = shark.getMobileBroadcastURL(id, Prefs['broadcast_quality'])

    if url == None:
        url = shark.getMobileBroadcastURL(id, Prefs['broadcast_quality'])

    return Redirect(url)

########################## Thread Function #####################################
def MarkSongs(id, server, key):
    shark.markSongDownloadedEx(id, server, key)
    time.sleep(2)

    shark.markSongQueueSongPlayed(id, server, key)
    time.sleep(30)

    shark.markStreamKeyOver30Seconds(id, server, key)
    time.sleep(30)

    shark.markSongComplete(id, server, key)
    return