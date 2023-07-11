import os
import string
import fasttext
import neo4j

from fastchat.constants import LOGDIR

### Databases ###
dbms_username = "neo4j"
dbms_password = "P@ssw0rd"
graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)
### Models ###
file_path = "/home/grace/grace/vicuna/FastChat/profiler/model.bin"
sentence2vecModel = fasttext.load_model(file_path)
### Whitelist ###
whitelist_file_path = "profiler/newEntityList2.txt"
whitelist_filename = os.path.join(LOGDIR, f"{whitelist_file_path}")
with open(whitelist_filename, 'r') as f:
    whitelist_string = f.read()
whitelist = whitelist_string.split("\n")
punctuationString = string.punctuation
punctuationList=[*punctuationString]
### Locations List ###
locations_file_path = "profiler/Locations.txt"
locations_filename = os.path.join(LOGDIR, f"{locations_file_path}")
with open(locations_filename, 'r') as f:
    locations_string = f.read()
locations = locations_string.split("\n")

### Create predefined "Class" nodes based on whitelist ###
# the first 70 whitelist terms will belong to Category 1, and so on 
whiteListChunks = [whitelist[x:x+70] for x in range(0, len(whitelist), 70)]
count = 1
predefined_classes = []
for chunk in whiteListChunks:
    category_name = "Category "+str(count)
    predefined_classes.append(category_name)
    count+=1
predefined_classes.append("Locations")

### Create generic predefined "Class" nodes ###
### Change this only ###
generic_classes = ["Animals", "Air Force", "Navy", "Army", "Military Vehicles", "Global Politics", "South-East Asia"]
predefined_classes+=generic_classes

### Driver code ###
# 1. collect the vector embedding for each class node
# 2. run cypher qeury to create these class nodes
class_vectors = {}
for class_node in predefined_classes:
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
