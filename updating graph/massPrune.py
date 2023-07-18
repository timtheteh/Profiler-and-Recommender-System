import datetime
import math
import neo4j

dbms_username = "neo4j"
dbms_password = "P@ssw0rd"
probability_rate = 0.5
shelf_life = 10
graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)

class massPrune:

    def __init__(self):
        pass

    ### Getting all things in graph 
    def get_likes_relationship_freq_id_datetime(self):
        with graphDB.session() as session:
            result = session.run("""
            MATCH (node1:User)-[rel:LIKES]-(node2:Entity) 
            RETURN rel.freq, id(rel), node2.datetimeadded
            """)
            records = result.data()
            new_records = {}
            for record in records:
                new_records[record['id(rel)']] = [record['rel.freq'], record['node2.datetimeadded']]
            return new_records

    def getAllEntities(self):
        with graphDB.session() as session:
            result = session.run("""
            MATCH (n:Entity)
            RETURN n.name, n.datetimeadded
            """)
            records = result.data()
            ans = {}
            for record in records:
                ans[record['n.name']] = record['n.datetimeadded']
            return ans
    
    def getAllDocuments(self):
        with graphDB.session() as session:
            result = session.run("""
            MATCH (n:Document)
            RETURN n.name, n.datetimeadded
            """)
            records = result.data()
            ans = {}
            for record in records:
                ans[record['n.name']] = record['n.datetimeadded']
            return ans
    
    def getAllUsers(self):
        with graphDB.session() as session:
            result = session.run("""
            MATCH (n:User)
            RETURN n.name, n.datetimeadded
            """)
            records = result.data()
            ans = {}
            for record in records:
                ans[record['n.name']] = record['n.datetimeadded']
            return ans
    
    def getAllLikesLinks(self):
        with graphDB.session() as session:
            result = session.run("""
            MATCH (n:User)-[r1:LIKES]-(e:Entity)
            RETURN id(r1), r1.weight
            """)
            records = result.data()
            ans = {}
            for record in records:
                ans[record['id(r1)']] = record['r1.weight']
            return ans
    
    ### Deleting stuff in graph
    def detachDeleteEntity(self, entity_name):
        with graphDB.session() as session:
            session.run("""
            MATCH (n:Entity {name: $entity_name})
            DETACH DELETE (n)
            """, entity_name=entity_name)

    def detachDeleteDocument(self, doc_name):
        with graphDB.session() as session:
            session.run("""
            MATCH (n:Document {name: $doc_name})
            DETACH DELETE (n)
            """, doc_name=doc_name)
    
    def detachDeleteUser(self, user_name):
        with graphDB.session() as session:
            session.run("""
            MATCH (n:User {name: $user_name})
            DETACH DELETE (n)
            """, user_name=user_name)
    
    def removeLikeLink(self, link_id):
        with graphDB.session() as session:
            session.run("""
            MATCH (n:User)-[r1:LIKES {id: $link_id}]-(e:Entity)
            DELETE r1
            """, link_id=link_id)

    ### Mass actions    
    def massPruneGraph(self):
        ### Assume that the cut-off shelf-life of each entity/document is 10 days
        ### Detach delete any entities if the datetimeadded is too far away
        all_entities_datetime = self.getAllEntities()
        now = datetime.datetime.now()
        for entity, dt in all_entities_datetime.items():
            datetime_object = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")
            time_delta = now - datetime_object
            time_delta_days = (time_delta.total_seconds())/(24*60*60)
            if time_delta_days >= shelf_life:
                self.detachDeleteEntity(entity)
        ### Detach delete any documents if the datetimeadded is too far away
        all_documents_datetime = self.getAllDocuments()
        for document, dt in all_documents_datetime.items():
            datetime_object = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")
            time_delta = now - datetime_object
            time_delta_days = (time_delta.total_seconds())/(24*60*60)
            if time_delta_days >= shelf_life:
                self.detachDeleteDocument(document)
        ### Remove any "LIKES" relationships if its weight is negligible.
        all_likes_weights = self.getAllLikesLinks()
        for id, weight in all_likes_weights.items():
            if weight < 0.001:
                self.removeLikeLink(link_id=id)
        ### Detach delete any users if the datetimeadded is too far away
        all_users_datetime = self.getAllUsers()
        for user, dt in all_users_datetime.items():
            datetime_object = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")
            time_delta = now - datetime_object
            time_delta_days = (time_delta.total_seconds())/(24*60*60)
            if time_delta_days >= shelf_life:
                self.detachDeleteUser(user)
