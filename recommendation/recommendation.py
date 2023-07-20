import neo4j
from numpy import dot
from numpy.linalg import norm
import time
from heapq import nlargest

dbms_username = "neo4j"
dbms_password = "P@ssw0rd"
graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)
user_name = "127.0.0.1"
graph_name = "test"
testEntitiesToReduce = ["population", "Malaysia", "South-East Asia"]
testEntitiesToBoost = ["Singapore", "World Conflicts"]

def graphExists(graphName):
    with graphDB.session() as session:
        result = session.run(
            'CALL gds.graph.exists($graphName)'
        ,graphName=graphName)
        exists = [ (record['exists']) for record in result]
        return exists[0]

def getAllExistingGraphs():
    with graphDB.session() as session:
        result = session.run(
            'CALL gds.graph.list()'
        )
        graphList = [ (record['graphName']) for record in result]
        print(graphList)
        return graphList

def createPageRankGraph(graphName):
    deleteAllExistingGraphs()
    ''' create cypher graph for page rank'''
    print('creating pageRank cypher graph: ', graphName)
    with graphDB.session() as session:
        result = session.run(
        '''
        CALL gds.graph.project.cypher(
            $graphName,
            'MATCH (n) OPTIONAL MATCH (n)-[]-() WITH n, COUNT(*) AS outgoingCount WHERE outgoingCount > 0 RETURN id(n) AS id',
            'MATCH (s)-[r]-(t) RETURN id(s) AS source, id(t) AS target, COALESCE(r.weight,0) AS weight'
            );
        ''', graphName=graphName)
        print(result.data())

def getUserInterestsAsSourceNodes(user_name):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (user:User {name: $user_name})
        MATCH (user)-[r1:LIKES]-(ent:Entity)
        RETURN id(ent), r1.weight
        """, parameters={
            "user_name": user_name
        })
        records = result.data()
        id_weights = {}
        for record in records:
            id_weights[record['id(ent)']] = record['r1.weight']
        print("id weights are here: ", id_weights)
        top_ids = nlargest(5, id_weights, key=id_weights.get)
        print("top_ids are here: ", top_ids)
        return top_ids

def getDocumentEntities(doc_name):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (user:Document {name: $doc_name})
        MATCH (user)-[r1:HAS]-(ent:Entity)
        RETURN ent.name
        """, parameters={
            "doc_name": doc_name
        })
        records = result.data()
        list_ids = []
        for record in records:
            list_ids.append(record['ent.name'])
        return list_ids

def getDocumentEntityIds(doc_name):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (user:Document {name: $doc_name})
        MATCH (user)-[r1:HAS]-(ent:Entity)
        RETURN id(ent), ent.name
        """, parameters={
            "doc_name": doc_name
        })
        records = result.data()
        list_ids = []
        for record in records:
            list_ids.append(record['id(ent)'])
        return list_ids

def getUserEntities(user_name):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (user:User {name: $user_name})
        MATCH (user)-[r1:LIKES]-(ent:Entity)
        RETURN ent.name
        """, parameters={
            "user_name": user_name
        })
        records = result.data()
        list_ids = []
        for record in records:
            list_ids.append(record['ent.name'])
        return list_ids

def personalisedPageRank(user_name, graph_name, dampingFactor, typeOfNodeToRecommend, sourceNodes):
    with graphDB.session() as session:
        result = session.run(           
        """
        MATCH (user:User {name: $user_name})
        CALL gds.pageRank.stream($graph_name, {
            maxIterations: 20,
            dampingFactor: $dampingFactor,
            sourceNodes: $sourceNodes,
            relationshipWeightProperty: 'weight'
        })
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).name AS name, labels(gds.util.asNode(nodeId)) AS label, score, nodeId
        ORDER BY score DESC, name ASC
        """, graph_name=graph_name, user_name=user_name, sourceNodes=sourceNodes, dampingFactor=dampingFactor)
        
        records = result.data()
        print('list of all records: ', records, '\n')
        relevant_records = {}
        recommendations = {}
        total_score = 0
        for record in records:
            total_score += record['score']
            if record['score'] > 0:
                relevant_records[record['nodeId']] = [record['name'], record['label'], record['score']]
            if record['label'][0] == typeOfNodeToRecommend:
                recommendations[record['nodeId']] = [record['name'], record['score']]
        print('the scores sum to: ', total_score, '\n')
        print('number of relevant results: ', len(relevant_records), '\n')
        print('relevant results: ', relevant_records, '\n')
        print('recommendations are: ', recommendations, '\n')
        if recommendations[list(recommendations.keys())[0]][1] != 0.0:
            return recommendations[list(recommendations.keys())[0]][0]
        else:
            return None

def personalisedPageRankDocToUser(doc_name, graph_name, dampingFactor, typeOfNodeToRecommend, sourceNodes):
    with graphDB.session() as session:
        result = session.run(           
        """
        MATCH (d:Document {name: $doc_name})
        CALL gds.pageRank.stream($graph_name, {
            maxIterations: 20,
            dampingFactor: $dampingFactor,
            sourceNodes: $sourceNodes,
            relationshipWeightProperty: 'weight'
        })
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).name AS name, labels(gds.util.asNode(nodeId)) AS label, score, nodeId
        ORDER BY score DESC, name ASC
        """, graph_name=graph_name, doc_name=doc_name, sourceNodes=sourceNodes, dampingFactor=dampingFactor)
        
        records = result.data()
        print('list of all records: ', records, '\n')
        relevant_records = {}
        recommendations = {}
        total_score = 0
        for record in records:
            total_score += record['score']
            if record['score'] > 0:
                relevant_records[record['nodeId']] = [record['name'], record['label'], record['score']]
            if record['label'][0] == typeOfNodeToRecommend:
                recommendations[record['nodeId']] = [record['name'], record['score']]
        if recommendations[list(recommendations.keys())[0]][1] != 0.0:
            return recommendations[list(recommendations.keys())[0]][0]
        else:
            return None

def testWeights(user_name, testEntitiesToReduce, testEntitiesToBoost):
    for ent in testEntitiesToReduce:
        with graphDB.session() as session:
            session.run("""
            MATCH (node1:User {name: $user_name})
            MATCH (node2:Entity {name: $entity_name})
            MATCH (node1)-[rel:LIKES]-(node2) 
            SET rel.weight = $weight
            """, parameters={
                "user_name": user_name,
                "entity_name": ent,
                "weight": 0
            })
        with graphDB.session() as session:
            session.run("""
            MATCH (node2:Entity {name: $entity_name})
            MATCH (node2)-[rel2:IS_SIMILAR_TO]-() 
            SET rel2.weight = $weight
            """, parameters={
                "entity_name": ent,
                "weight": 0
            })
    for ent in testEntitiesToBoost:
        with graphDB.session() as session:
            session.run("""
            MATCH (node1:User {name: $user_name})
            MATCH (node2:Entity {name: $entity_name})
            MATCH (node1)-[rel:LIKES]-(node2) 
            SET rel.weight = $weight
            """, parameters={
                "user_name": user_name,
                "entity_name": ent,
                "weight": 1
            })
        with graphDB.session() as session:
            session.run("""
            MATCH (node2:Entity {name: $entity_name})
            MATCH (node2)-[rel2:IS_SIMILAR_TO]-() 
            SET rel2.weight = $weight
            """, parameters={
                "entity_name": ent,
                "weight": 1
            })

def getAllExistingGraphs():
    with graphDB.session() as session:
        result = session.run(
            'CALL gds.graph.list()'
        )
        graphList = [ (record['graphName']) for record in result]
        return graphList

def deleteAllExistingGraphs():
    existingGraphs = getAllExistingGraphs()
    with graphDB.session() as session:
        for graphName in existingGraphs:
            session.run('CALL gds.graph.drop($graphName)',graphName=graphName)

def assignGraphEmbeddings(graphName):
    with graphDB.session() as session:
        result = session.run("""
        CALL gds.beta.node2vec.stream(
            $graphName,
            {
                relationshipWeightProperty: 'weight'
            }
        )
        YIELD nodeId, embedding
        RETURN nodeId, embedding
        """, graphName=graphName)
        records = result.data()
        return records

def getUserEmbedding(user_name, graphEmbeddings):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (user:User {name: $user_name})
        RETURN id(user)
        """, parameters={
            "user_name": user_name
        })
        record = result.single()
        user_id = record['id(user)']
        user_embedding = None
        for node in graphEmbeddings:
            if node['nodeId'] == user_id:
                user_embedding = node['embedding']
        return user_embedding

def getOtherUsersIds(user_name):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (user1:User {name: $user_name}),(user2:User)
        WHERE user1 <> user2
        RETURN id(user2)
        """, parameters={
            "user_name": user_name,
        })
        records = result.data()
        return records

def getUserNameFromId(user_id):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (u:User)
        WHERE id(u) = $user_id
        RETURN u.name
        """, user_id=user_id)
        record = result.single()
        return record['u.name']

def massUpdateAllRelationshipsToZero():
    with graphDB.session() as session:
        session.run("""
            MATCH (s)-[r]-(t) 
            SET r.weight = $weight
            """, parameters = {
                "weight": 100
            })

# massUpdateAllRelationshipsToZero()
### Pagerank algorithm ###
start_time = time.time()
createPageRankGraph(graphName=graph_name)
timeToProjectGraph = time.time() - start_time

sourceNodes = getUserInterestsAsSourceNodes(user_name=user_name)
print(sourceNodes, '\n')
start_time = time.time()
recommendedDocument = personalisedPageRank(user_name=user_name, graph_name=graph_name, dampingFactor=0.85, typeOfNodeToRecommend='Document')
timeToRecommendDocument = time.time() - start_time
if recommendedDocument:
    documentEntities = getDocumentEntities(recommendedDocument)
    print("Based on your interests, you might be interested in this document: ", recommendedDocument, ". It contains the following entities which might be of interest to you: ", documentEntities, ".\n")
else:
    print("Sorry, it seems like none of the documents in the database are suitable to be recommeneded to you.\n")

### Recommend similar users ###
start_time = time.time()
graphEmbeddings = assignGraphEmbeddings(graphName=graph_name)
timeToAssignEmbeddings = time.time() - start_time
user_embedding = getUserEmbedding(user_name=user_name, graphEmbeddings=graphEmbeddings)
otherUsersIds = getOtherUsersIds(user_name=user_name)
timeToRecommendUser = 0
if len(otherUsersIds) == 0:
    print("No other users to recommend!")
else:
    start_time = time.time()
    otherUsersEmbeddings = {}
    for i in otherUsersIds:
        otherUserId = i['id(user2)']
        for j in graphEmbeddings:
            if j['nodeId'] == otherUserId:
                otherUserEmbedding = j['embedding']
                if not all(v == 0 for v in otherUserEmbedding):
                    otherUsersEmbeddings[otherUserId] = otherUserEmbedding
    # print("\n", otherUsersEmbeddings, "\n")
    otherUsersEmbeddingSimilarityScores = {}
    for id, embedding in otherUsersEmbeddings.items():
        cos_sim = dot(user_embedding, embedding)/(norm(embedding)*norm(user_embedding))
        otherUsersEmbeddingSimilarityScores[id] = cos_sim
    # print("other users embedding sim scores: ", otherUsersEmbeddingSimilarityScores, "\n")
    justToPrint = {}
    for u, score in otherUsersEmbeddingSimilarityScores.items():
        userName = getUserNameFromId(u)
        justToPrint[userName] = score
    print("other users: ", justToPrint, "\n")
    if len(otherUsersEmbeddings) != 0:
        # print("other users recommendations: ", otherUsersEmbeddingSimilarityScores, '\n')
        bestUserId = max(otherUsersEmbeddingSimilarityScores, key=otherUsersEmbeddingSimilarityScores.get)
        bestUser = getUserNameFromId(bestUserId)
        print("The profile that seems the most similar to your profile is: ", bestUser, '\n')
        timeToRecommendUser = time.time() - start_time
    else:
        print("Sorry, it seems that there are no users that are similar to you.")

### Choose which user to show document to ###
new_document = "document 6"
source_nodes2 = getDocumentEntityIds(doc_name=new_document)
print(source_nodes2, '\n')
start_time = time.time()
recommendedUser = personalisedPageRankDocToUser(doc_name=new_document, graph_name=graph_name, dampingFactor=0.85, typeOfNodeToRecommend='User', sourceNodes=source_nodes2)
timeToRecommendAnotherUser = time.time() - start_time
if recommendedUser:
    userEntities = getUserEntities(recommendedUser)
    print("The best user to show ", new_document, " to is: ", recommendedUser, ". This user likes the following overlapping entities: ", userEntities, ".\n")
else:
    print("Sorry, it seems like there is no appropriate user to show ", new_document, " to.\n")

print("""
      Stats: 
      Time to project graph: %s
      Time to recommend graph: %s
      Time to assign embeddings to graph: %s
      Time to recommend another user: %s
      Time to choose user to recommend document to: %s
      """%(timeToProjectGraph, timeToRecommendDocument, timeToAssignEmbeddings, timeToRecommendUser, timeToRecommendAnotherUser))

