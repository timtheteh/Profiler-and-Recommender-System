import fasttext
import neo4j

# phrase = "dog park"
# # tokens = fasttext.tokenize(phrase)

# # Get the vector representation of the phrase
# vector = sentence2vecModel.get_sentence_vector(phrase)

# # Print the vector representation of the phrase
# print(vector)

# similarity = sentence2vecModel.get_similarity(phrase, "cat park")

# print("similarity is: ", similarity)

# import datetime

# string = "2023-06-28T09:15:54"

# datetime_object = datetime.datetime.strptime(string, "%Y-%m-%dT%H:%M:%S")

# now = datetime.datetime.now()

# time_delta = now - datetime_object

# total_seconds = time_delta.total_seconds()

# print("time delta: ", time_delta)
# print("in seconds: ", total_seconds)

# Add Class Nodes

dbms_username = "neo4j"
dbms_password = "P@ssw0rd"


graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)
# with graphDB.session() as session:
#     relationship_exists = session.run("""
#         MATCH (node1:User)-[rel:LIKES]-(node2:Entity) 
#         WHERE node1.name = '{user_name}' AND node2.name = '{entity_name}'
#         RETURN rel.freq
#         """.format(user_name="127.0.0.1", entity_name="Singapore"))
    
#     print(relationship_exists.data())
    
#     if len(relationship_exists.data()) > 0:
#         print('hi')
#         for result in relationship_exists:
#             print(result)

# def check_existence_entity(entity_name):
#     with graphDB.session() as session:
#         result = session.run("""
#         MATCH (u:Entity {name: $entity_name})
#         WITH COUNT(u) > 0  as node_exists
#         RETURN node_exists
#         """, parameters={
#             "entity_name": entity_name
#         })
#         record = result.single()
#         print(record)
#         return record['node_exists']  

# print(check_existence_entity("Singapore Navy"))

# def check_existence_relationship(user_name, entity_name):
#     with graphDB.session() as session:
#         result = session.run("""
#         MATCH (node1:User)-[rel:LIKES]-(node2:Entity) 
#         WHERE node1.name = '{user_name}' AND node2.name = '{entity_name}'
#         WITH COUNT(rel) > 0 as relationship_exists
#         RETURN relationship_exists
#         """, parameters={
#             "user_name": user_name, 
#             "entity_name": entity_name
#         })
#         record = result.single()
#         return record['relationship_exists']   

# print(check_existence_relationship(user_name="127.0.0.1", entity_name="Singapore Navy"))

# def get_most_similar_class_node(entity_name, threshold):
#     with graphDB.session() as session:
#         result = session.run("""
#         MATCH (ent1:Entity {name: $entity_name}),(ent2:Class)
#         WHERE ent1 <> ent2
#         WITH ent1, ent2, gds.similarity.cosine(ent1.vector,ent2.vector) as similarity
#         RETURN ent2.name, similarity ORDER BY similarity DESC LIMIT 1
#         """, parameters={
#             "entity_name": entity_name,
#             "threshold": threshold,
#         })
#         record = result.single()
#         ans = [record['ent2.name'], record['similarity']]
#         return ans

# print(get_most_similar_class_node(entity_name="Singapore Navy", threshold=0.6))

# def delete_entity_node(entity_name):
#     with graphDB.session() as session:
#         session.run(""" 
#         MATCH (ent1:Entity {name: $entity_name})
#         DETACH DELETE ent1
#         """, parameters={
#             "entity_name": entity_name
#         })

def create_link_entity_class(entity_name, most_similar_class_name, most_similar_class_score):
    with graphDB.session() as session:
        session.run("""
        MATCH (ent1:Entity {name: $entity_name})
        MATCH (class:Class {name: $class_name})
        MERGE (ent1)-[r1:IS_SIMILAR_TO]-(class)
        SET r1.weight = $similarity_score
        """, parameters={
            "entity_name": entity_name,
            "class_name": most_similar_class_name,
            "similarity_score": most_similar_class_score
        })

def get_most_similar_class_node(entity_name, threshold):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (ent1:Entity {name: $entity_name}),(ent2:Class)
        WHERE ent1 <> ent2
        WITH ent1, ent2, gds.similarity.cosine(ent1.vector,ent2.vector) as similarity
        RETURN ent2.name, similarity ORDER BY similarity DESC LIMIT 3
        """, parameters={
            "entity_name": entity_name,
        })
        records = result.data()
        new_records = {}
        for record in records:
            if record['similarity'] > threshold:
                new_records[record['ent2.name']] = record['similarity']
        return new_records

entity_name = "Singapore Navy"
threshold = 0.28
print(get_most_similar_class_node(entity_name=entity_name, threshold=threshold))
# most_similar_class_node_name, most_similar_class_node_score = most_similar_class_node[0], most_similar_class_node[1]
# create_link_entity_class(entity_name=entity_name, most_similar_class_name=most_similar_class_node_name, most_similar_class_score=most_similar_class_node_score)
