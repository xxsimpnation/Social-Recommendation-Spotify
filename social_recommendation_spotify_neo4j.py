from neo4j import GraphDatabase
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity

# ------------------------------------ Configuration parameters ------------------------------------ #
client_id = "[ADD YOUR SPOTIFY CLIENT ID HERE]"                   # spotify client ID
client_secret = "[ADD YOUR SPOTIFY CLIENT SECRET HERE]"           # spotify client secret
neo4j_url = "bolt://localhost:7687"                               # url of the neo4j database.
neo4j_username = "neo4j"                                          # neo4j username. defaults to 'neo4j'.
neo4j_password = "[add neo4j password]"                           # neo4j database password

# create session neo4j
def create_neo4j_session(url, user, password):
    driver = GraphDatabase.driver(url, auth=(user, password))
    return driver.session()
neo4j = create_neo4j_session(url=neo4j_url, user=neo4j_username, password=neo4j_password)

main_user = "[username]"                                         # username who want to give the recommendation
followinguser = []

neighbours = """
            MATCH (u1:User)-[:LISTEN]->(t:Track)<-[:LISTEN]-(u2:User)<-[:FOLLOWS]-(u1:User)
            WHERE u1 <> u2
            AND u1.username = $mainuser
            WITH u1, u2, COUNT(DISTINCT t) as intersection_count

            MATCH (u:User)-[:LISTEN]->(t:Track)
            WHERE u in [u1, u2]
            WITH u1, u2, intersection_count, COUNT(DISTINCT t) as union_count

            WITH u1, u2, intersection_count, union_count, (intersection_count*1.0/union_count) as jaccard_index

            ORDER BY jaccard_index DESC, u2.username
            WITH u1, COLLECT([u2.username, jaccard_index, intersection_count, union_count])[0..5] as neighbours

            RETURN u1.username as user, neighbours"""

recos = {}           
result = neo4j.run(neighbours, mainuser = main_user)
for item in result:
    recos[item[0]] = item[1]
    
# print the most similarity user base on user who main_user follows
# for i in recos:
#     print(recos[i])

for i in recos[main_user]:
    followinguser.append(i[0]) 
 
# get list main_user song which have same genre to similarity_user song
def tracks_mainuser(followinguser):
    tracks_user = """
        MATCH (u1:User)-[:LISTEN]->(t:Track)<-[:LISTEN]-(u2:User), (t:Track)-[:HAS_ARTIST]->(a:Artist)-[:HAS_GENRE]->(g1:Genre)
        WHERE u1 <> u2
        AND u1.username = $mainuser AND u2.username = $followinguser
        WITH g1.name as genre, u2 as username

        MATCH (u3:User)-[:LISTEN]->(t1:Track)-[:HAS_ARTIST]->(a:Artist)-[:HAS_GENRE]->(g:Genre)
        WHERE g.name in genre AND u3.username = $mainuser
        RETURN distinct t1.id as track_id, t1.name as track_name, t1.acousticness as acousticness, t1.danceability as danceability,
            t1.energy as energy, t1.liveness as liveness, t1.loudness as loudness, t1.speechiness as speechiness, 
            t1.tempo as tempo
                        """

    tracks = pd.DataFrame([dict(_) for _ in neo4j.run(tracks_user, mainuser = main_user, followinguser = followinguser)])
    return tracks

# get list similarity_user song which have same genre to main_user song
def tracks_followinguser(followinguser):
    tracks_recom = """
        MATCH (u1:User)-[:LISTEN]->(t:Track)<-[:LISTEN]-(u2:User), (t:Track)-[:HAS_ARTIST]->(a:Artist)-[:HAS_GENRE]->(g1:Genre)
        WHERE u1 <> u2
        AND u1.username = $mainuser AND u2.username = $followinguser
        WITH g1.name as genre, u2 as username

        MATCH (u3:User)-[:LISTEN]->(t1:Track)-[:HAS_ARTIST]->(a:Artist)-[:HAS_GENRE]->(g:Genre)
        WHERE g.name in genre AND u3.username = $followinguser
        RETURN distinct t1.id as track_id, t1.name as track_name, t1.acousticness as acousticness, t1.danceability as danceability,
            t1.energy as energy, t1.liveness as liveness, t1.loudness as loudness, t1.speechiness as speechiness, 
            t1.tempo as tempo
                        """

    tracks = pd.DataFrame([dict(_) for _ in neo4j.run(tracks_recom, mainuser = main_user, followinguser = followinguser)])
    return tracks

# get similarity score base on dataset
def create_similarity_score(df1,df2):
  
    assert list(df1.columns[2:]) == list(df2.columns[2:])
    features = list(df1.columns[2:])
    df_features1,df_features2 = df1[features],df2[features]
    
    # using minmaxscaler
    scaler = MinMaxScaler() 
    df_features_scaled1,df_features_scaled2 = scaler.fit_transform(df_features1),scaler.fit_transform(df_features2)
    
    cosine_sim = cosine_similarity(df_features_scaled1, df_features_scaled2)
    return cosine_sim
  
# get top 30 recommendation from every similarity_user
def recommendation(playlist_user, recoms):
    similarity_score = create_similarity_score(playlist_user,recoms)
    similarity = []
    for i in similarity_score:
        kambing = np.amax(i)
        similarity.append(kambing)

    final_recomms = recoms.iloc[[np.argmax(i) for i in similarity_score]]
    final_recomms.insert(loc=9, column="similarity", value=similarity)
    final_recomms = final_recomms.drop_duplicates(subset=['track_id'], keep="last")

    final_recomms = final_recomms[~final_recomms["track_name"].isin(playlist_user["track_name"])]
    final_recomms.reset_index(drop = True, inplace = True)

    final_recomms = final_recomms.sort_values(by='similarity', ascending=False).head(30)
    final_recomms.reset_index(drop = True, inplace = True)
    return final_recomms

# get the final recommendation
final_recomms = pd.DataFrame(columns=['track_id', 'track_name','acousticness','danceability','energy','liveness','loudness', 'speechiness', 'tempo', 'similarity'])
final_recomms

for user in followinguser:
    tracks_user = tracks_mainuser(user)
    tracks_folluser = tracks_followinguser(user)
    recomms = recommendation(tracks_user, tracks_folluser)
    final_recomms = pd.concat([final_recomms, recomms], axis=0, ignore_index=True)
    
final_recomms = final_recomms.drop_duplicates(subset=['track_id'], keep="last")
final_recomms = final_recomms.sort_values(by='similarity', ascending=False).head(30)
final_recomms.reset_index(drop = True, inplace = True)
final_recomms
