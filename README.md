# Social-Recommendation-Spotify

Social influence Recommendation Music Spotify using Graph Database (Neo4j)
by this code, we want to make recommendation to user base on who user follows (Social Influence). Its validate to user have a connection each other. Using jaccard coefficient and cosine similarity base on audio properties (acousticness, dancability etc)

the script is set up to be a complete end-to-end tool for organizing your music:
1. Get data from spotify api and load it on Neo4j
2. Make dataset and list of recommendation

Quick setup

In here, you specify the parameters needed to connect to your spotify account using the Spotify API:

`client_id = "[ADD YOUR SPOTIFY CLIENT ID HERE]"   ` 
`client_secret = "[ADD YOUR SPOTIFY CLIENT SECRET HERE]"`

Steps :
1. You need the Spotify developer dashboard to obtain a client id/secret. You can access it here: https://developer.spotify.com/dashboard/login. Next, create an app to obtain a client_id and a client_secret.
2. Your public playlist_uri can be found using the spotify application. Right click a playlist, select 'Share' and click 'Copy Spotify URI'. Your URI will have the following format: https://open.spotify.com/playlist/XXXXXXXXXXXXXXXXXX
3. Set up your Neo4j connection in
```
neo4j_url = "bolt://localhost:7687"
neo4j_username = "neo4j"
neo4j_password = "[add neo4j password]"
```
4. Install python dependencies
