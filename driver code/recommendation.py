import neo4j

dbms_username = "neo4j"
dbms_password = "P@ssw0rd"

graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)

def getAllExistingGraphs():
    with graphDB.session() as session:
        result = session.run(
            'CALL gds.graph.list()'
        )
        graphList = [ (record['graphName']) for record in result]
        print(graphList)
        return graphList

def createPageRankGraph(graphName):
    ''' create cypher graph for page rank'''
    print('creating pageRank cypher graph: ', graphName)
    with graphDB.session() as session:
        result = session.run(
        '''
        CALL gds.graph.project.cypher(
            $graphName,
            'MATCH (n) RETURN id(n) AS id',
            'MATCH (s)-[r]-(t) RETURN id(s) AS source, id(t) AS target, COALESCE(r.weight,0) AS weight'
            );
        ''', graphName=graphName)
        print(result.data())

def personalisedPageRank(user_name, graph_name):
    with graphDB.session() as session:
        result = session.run(           
        """
        MATCH (user:User {name: $user_name})
        CALL gds.pageRank.stream($graph_name, {
            maxIterations: 20,
            dampingFactor: 0.85,
            sourceNodes: [user],
            relationshipWeightProperty: 'weight'
        })
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).name AS name, labels(gds.util.asNode(nodeId)) AS label, score
        ORDER BY score DESC, name ASC
        """, graph_name=graph_name, user_name=user_name)
        
        records = result.data()
        print(records)
        recommendations = {}
        total_score = 0
        for record in records:
            total_score += record['score']
            if record['label'][0] == 'Class':
                recommendations[record['name']] = record['score']
        print('the scores sum to: ', total_score)
        print(recommendations)

user_name = "127.0.0.1"
graph_name = "test"

# createPageRankGraph(graphName=graph_name)
personalisedPageRank(user_name=user_name, graph_name=graph_name)
# getAllExistingGraphs()
