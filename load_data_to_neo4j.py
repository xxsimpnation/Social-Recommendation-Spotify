import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import spotipy.util as util
from neo4j import GraphDatabase
import requests

# ------------------------------------ Configuration parameters ------------------------------------ #
client_id = "[ADD YOUR SPOTIFY CLIENT ID HERE]"                   # spotify client ID
client_secret = "[ADD YOUR SPOTIFY CLIENT SECRET HERE]"           # spotify client secret
neo4j_url = "bolt://localhost:7687"                               # url of the neo4j database.
neo4j_username = "neo4j"                                          # neo4j username. defaults to 'neo4j'.
neo4j_password = "[add neo4j password]"                           # neo4j database password


client_cred_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
spotify = spotipy.Spotify(client_credentials_manager = client_cred_manager)

## playlist url (you need to add it manually by copy from spotify app)
main_user = "[add username of main user] "                       # example : "edwin"
users = "[list of username of main_user follow]"                 # example : ["edwin", "sarah", "madeline"]

playlist_uri =  "[list of playlist from users]"

## example
# playlist_uri =  [["https://open.spotify.com/playlist/50t90ViTv50PGoI18PJ5BG?si=36eb3780840c4f30",
#                  "https://open.spotify.com/playlist/7jgWRiir84dnTBACxPgOPg?si=e6ac6f6f944e4ac2",], ## playlist edwin
    
#                 ["https://open.spotify.com/playlist/6jVMfOqT6JNp5fZXpiuknO?si=f75e375bb5254fab", 
#                 "https://open.spotify.com/playlist/1fJLI26W1SpY0mqbmHP6qO?si=7d454c7cefbd4d65"], ##playlist sarah
                
#                  ["https://open.spotify.com/playlist/3bp531OpZzmBMWy8jLjp0v?si=ad80970da7214de0", 
#                 "https://open.spotify.com/playlist/7drvet21I34ixgSxOqkM0r?si=644f784a2d924745"], ## playlist madeline ]


#Get tracks from spotify api
def get_tracks(playlist_user):
    items = {}
    for user_playlist in playlist_user:
        try:
        #Get Url
            get = requests.get(user_playlist)
            # if the request succeeds 
            if get.status_code == 200:
                results = spotify.playlist(user_playlist)['tracks']
                while results['next'] or results['previous'] is None:
                    for track in results["items"]:
                        del track['track']['available_markets']
                        if track['track']['id']:
                            track['track']['artists'] = [artist if type(artist) == str else artist['id'] 
                                                         for artist in track['track']['artists']]
                            track['track']['album'] = track['track']['album'] if type(track['track']['album']) == str else \
                                                        track['track']['album']['id']
                            items[track['track']['id']] = track['track']
                        for field in track['track']:
                            if track is not None and type(track['track'][field]) == dict:
                                track['track'][field] = None
                    if not results['next']:
                        break
                    results = spotify.next(results)
            else:
                pass

        #Exception
        except requests.exceptions.RequestException as e:
            # print URL with Errs
            raise SystemExit(f"{user_playlist}: is Not reachable \nErr: {e}")
            pass
        
    return items
    
    
#Get tracks audio from spotify api    
def get_track_audio_features(tracks, page_size=100):
    page_count = len(tracks) / page_size
    for i in range(int(page_count) + 1):
        ids = list(tracks.keys())[i * page_size:(i + 1) * page_size]
        if len(ids) == 0:
            break
        audio_features = spotify.audio_features(tracks=ids)
        for track_features in audio_features:
            if track_features is None:
                continue
            track_id = track_features['id']
            for feature, value in track_features.items():
                if feature != 'type':
                    tracks[track_id][feature] = value
    return tracks

#Get artist from spotify api 
def get_artist_info(items, page_size=50):
    all_artists = {}
    artist_ids = set()
    for track_id in items.keys():
        for artist_nr in items[track_id]['artists']:
            artist_id = artist_nr
            artist_ids.add(artist_id)

    # after we have a list of all artists, get the details from the API
    page_count = len(artist_ids) / page_size
    for i in range(int(page_count) + 1):
        ids = list(artist_ids)[i * page_size:(i + 1) * page_size]
        results = spotify.artists(ids)
        for artist in results['artists']:
            del artist['images']
            artist['followers'] = artist['followers']['total']
            artist['external_urls'] = None
            all_artists[artist['id']] = artist
    return all_artists

#Get genre from spotify api 
def get_genres(artists):
    genres = set()
    for item in artists:
        for genre in artists[item]['genres']:
            genres.add(genre)
    return genres
    
#Load data to Graph   
def load_graph_using_spotify_api(playlist, user):
    neo4j = create_neo4j_session(url=neo4j_url, user=neo4j_username, password=neo4j_password)
    print("dropping and creating constraints...")
    print(user)
    tracks = get_tracks(playlist)
    
    username = user
    neo4j.run("MERGE (u:User {username: $username });", username = username)
    
    if username == main_user:
        pass
    else:
        neo4j.run("MATCH (u1:User{username: $username}), (u2:User{username: $mainuser}) MERGE (u2)-[:FOLLOWS]->(u1);", 
                  username = username, mainuser=main_user)
        
    tracks = get_track_audio_features(tracks)
    neo4j.run("UNWIND $tracks as track MERGE (t:Track{name: track.name, artists: track.artists }) SET t = track, t.user = $username", username = username, 
              parameters={'tracks': list(tracks.values())})
    
    artists = get_artist_info(tracks)
    neo4j.run("UNWIND $artists as artist MERGE (a:Artist{id: artist.id}) SET a = artist",
              parameters={'artists': list(artists.values())})

    genres = get_genres(artists)
    neo4j.run("UNWIND $genres as genre MERGE (g:Genre{name: genre})",
              parameters={'genres': list(genres)})

    neo4j.run("MATCH (u:User), (t:Track{user: u.username}) MERGE (u)-[:LISTEN]->(t);")
    neo4j.run("MATCH (t:Track) UNWIND t.artists as artist MATCH (a:Artist{id: artist}) MERGE (t)-[:HAS_ARTIST]->(a)")
    neo4j.run("MATCH (a:Artist) UNWIND a.genres as genre MATCH (g:Genre{name: genre}) MERGE (a)-[:HAS_GENRE]->(g)")
    
 #Create neo4j Session
 def create_neo4j_session(url, user, password):
    driver = GraphDatabase.driver(url, auth=(user, password))
    return driver.session()
    
 #loop data for every user and playlist
 for (user, playlist_user) in zip(users, playlist_uri) :
    load_graph_using_spotify_api(playlist_user, user)
