import fasttext
import neo4j

dbms_username = "neo4j"
dbms_password = "P@ssw0rd"

graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)

classes = ["Animals", "Air Force", "Navy", "Army", "Military Vehicles", "Global Politics", "South-East Asia"]

class_vectors = {}
file_path = "/home/grace/grace/vicuna/FastChat/profiler/model.bin"
sentence2vecModel = fasttext.load_model(file_path)
for class_node in classes:
    vector = sentence2vecModel.get_sentence_vector(class_node)
    class_vectors[class_node] = vector

for class_node, vector in class_vectors.items():
    with graphDB.session() as session:
        session.run("""
        MERGE (n:Class {name: $name}) 
        SET n.vector = $vector
        RETURN n
        """, 
        parameters = {
            "name": class_node,
            "vector": vector
        })
