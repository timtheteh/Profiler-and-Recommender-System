import neo4j

dbms_username = "neo4j"
dbms_password = "P@ssw0rd"

graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)

def get_recommendation(user_name):
    with graphDB.session() as session:
        session.run("""
        MATCH (user:User {name: {name: $user_name})
        CALL gds.pageRank.stream('myGraph', {
            maxIterations: 20,
            dampingFactor: 0.85,
            sourceNodes: [siteA]
        })
        YIELD nodeId, score
        RETURN gds.util.asNode(nodeId).name AS name, score
        ORDER BY score DESC, name ASC
        """)
