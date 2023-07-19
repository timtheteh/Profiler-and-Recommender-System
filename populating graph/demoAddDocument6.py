import datetime
import os
import random
import string
import neo4j
from fastchat.constants import LOGDIR
import fasttext

### Models ###
file_path = "/home/grace/grace/vicuna/FastChat/profiler/model.bin"
sentence2vecModel = fasttext.load_model(file_path)
### Databases ###
dbms_username = "neo4j"
dbms_password = "P@ssw0rd"
graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)
### Whitelist ###
whitelist_file_path = "profiler/newEntityList2.txt"
whitelist_filename = os.path.join(LOGDIR, f"{whitelist_file_path}")
punctuationString = string.punctuation
punctuationList=[*punctuationString]
with open(whitelist_filename, 'r') as f:
    whitelist_string = f.read()
whitelist = whitelist_string.split("\n")
### Locations List ###
locations_file_path = "profiler/Locations.txt"
locations_filename = os.path.join(LOGDIR, f"{locations_file_path}")
with open(locations_filename, 'r') as f:
    locations_string = f.read()
locations = locations_string.split("\n")
whitelist += locations
### Predefined Classes ###
whiteListChunks = [whitelist[x:x+70] for x in range(0, len(whitelist), 70)]
count = 1
predefined_classes = {}
for chunk in whiteListChunks:
    category_name = "Category "+str(count)
    predefined_classes[category_name] = chunk
    count+=1
predefined_classes['Locations'] = locations

list_of_texts = {'document 6': 'The ITMS team used UHF radios to log the S-Net data from Fort Canning Reservoir.'}

def create_document_node(doc_name, datetimeadded):
    with graphDB.session() as session:
        session.run("""
        MERGE (n:Document {name: $name}) 
        SET n.datetimeadded = $datetimeadded
        RETURN n
        """, parameters = {
            "name": doc_name,
            "datetimeadded": datetimeadded
        })

def create_link_document_entity(doc_name, entity_name, weight):
    with graphDB.session() as session:
        session.run("""
            MATCH (node1:Document {name: $doc_name})
            MATCH (node2:Entity {name: $entity_name})
            MERGE (node1)-[rel:HAS]-(node2) 
            SET rel.weight = $weight
            """, parameters = {
                "doc_name": doc_name,
                "entity_name": entity_name,
                "weight": weight
            })

def create_entity_node(entity_name, vector, datetime):
    with graphDB.session() as session:
        session.run("""
        MERGE (n:Entity {name: $name}) 
        SET n.vector = $vector, n.datetimeadded = $datetime
        RETURN n
        """, 
        parameters = {
            "name": entity_name,
            "vector": vector,
            "datetime": datetime
        })

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

## Driver code ###
textName_entities = {}
for textName, textContent in list_of_texts.items():
    textName_entities[textName] = []
    textContent = textContent.lower()
    for phrase in whitelist:
        if (" "+phrase+" ") in textContent:
            textName_entities[textName].append(phrase)
            continue
        elif (phrase+" ") in textContent and textContent.find(phrase) == 0:
            textName_entities[textName].append(phrase)
            continue
        elif (phrase+" ") in textContent:
            for punctuation in punctuationList:
                if (punctuation+phrase+" ") in textContent:
                    textName_entities[textName].append(phrase)
                    break
            continue
        elif (" "+phrase) in textContent and textContent.rfind(phrase)+len(phrase)-1 == len(textContent)-1:
            textName_entities[textName].append(phrase)
            continue
        elif (" "+phrase) in textContent:
            for punctuation in punctuationList:
                if (" "+phrase+punctuation) in textContent:
                    textName_entities[textName].append(phrase)
                    break
            continue

for document, entity_list in textName_entities.items():
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    create_document_node(document, datetimeadded=now)
    for entity in entity_list:
        entity = entity.lower()
        entityVector = sentence2vecModel.get_sentence_vector(entity)
        create_entity_node(entity_name=entity, vector=entityVector, datetime=now)
        create_link_document_entity(doc_name=document, entity_name=entity, weight=random.uniform(0.3, 0.9))
        for predefined_class, list_of_entities in predefined_classes.items():
            if entity in list_of_entities:
                create_link_entity_class(entity_name=entity, most_similar_class_name=predefined_class, most_similar_class_score=random.uniform(0.3, 0.9))
            else:
                continue
