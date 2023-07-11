import datetime
import json
import os
import random
import string
import neo4j
import requests
from fastchat.constants import LOGDIR
import fasttext

class_threshold = 0.7
### Databases ###
dbms_username = "neo4j"
dbms_password = "P@ssw0rd"
graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)
### Models ###
file_path = "/home/grace/grace/vicuna/FastChat/profiler/model.bin"
sentence2vecModel = fasttext.load_model(file_path)
FASTCHAT_ENDPOINT = "http://127.0.0.1:7861/v1/chat/completions"
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

def create_document_node(doc_name):
    with graphDB.session() as session:
        session.run("MERGE (n:Document {name: $name}) RETURN n", parameters = {
                "name": doc_name,
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

### LLM Functions ###
# Vicuna is used to extract the entities in a query
def getVicunaAnswer(prompt_template, temperature):
    vicuna_response = requests.post(url=FASTCHAT_ENDPOINT, json={
        "model": "vicuna-7b",
        "messages": [
                {
                    "role": "user",
                    "content": prompt_template
                }
            ],
        "temperature" : temperature
    })
    response_dict = json.loads(vicuna_response.content.decode("utf-8")) 
    answer = response_dict["choices"][0]["message"]["content"]
    return answer

# The prompt to Vicuna is crafted to try to get the intended result from vicuna
# Intended result from this prompt: { "entities": ['entity1', 'entity2']}
def createPrompt(text):
    return """
    Q: Form a coherent sentence based on these phrases: ["dog", "cat"]. Leave any acronyms as they are and leave all text in lower case. Return the answer in JSON format.
    A: {
        “text”: "The dog chased the cat down the street."
    }

    Q: Form a coherent sentence based on these phrases: ["surveillance", "medical", "msc"]. Leave any acronyms as they are and leave all text in lower case. Return the answer in JSON format. 
    A: {
        “text”: "He is an msc who conducts surveillance for the medical team."
    }

    Q: Form a coherent sentence based on these phrases: %s. Leave any acronyms as they are and leave all text in lower case. Return the answer in JSON format.
    A: 
    """%(text)

def get_random_keywords(n):
    return str(random.sample(whitelist, n))

def get_most_similar_class_nodes(entity_name):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (ent1:Entity {name: $entity_name}),(ent2:Class)
        WHERE ent1 <> ent2
        WITH ent1, ent2, gds.similarity.cosine(ent1.vector,ent2.vector) as similarity
        RETURN ent2.name, similarity ORDER BY similarity DESC LIMIT 5
        """, parameters={
            "entity_name": entity_name,
        })
        records = result.data()
        new_records = {}
        for record in records:
            new_records[record['ent2.name']] = record['similarity']
        return new_records

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

list_vicuna_answers = []
for i in range(5):
    random_keywords = get_random_keywords(5)
    print("random keywords are here: ", random_keywords)
    prompt = createPrompt(random_keywords)
    vicuna_answer = getVicunaAnswer(prompt_template=prompt, temperature=0)
    json_answer = json.loads(vicuna_answer)
    list_vicuna_answers.append(json_answer['text'])

print("list of vicuna answers: ", list_vicuna_answers, '\n')

count = 1
list_of_texts = {}
for ans in list_vicuna_answers:
    new_key = "document "+str(count)
    list_of_texts[new_key] = ans
    count += 1

print("list of documents and their texts: ", list_of_texts, '\n')

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
        

print("Document names and their entities: ", textName_entities, '\n')

for document, entity_list in textName_entities.items():
    create_document_node(document) 
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    for entity in entity_list:
        entity = entity.lower()
        entityVector = sentence2vecModel.get_sentence_vector(entity)
        create_entity_node(entity_name=entity, vector=entityVector, datetime=now)
        create_link_document_entity(doc_name=document, entity_name=entity, weight=0.7)
        for predefined_class, list_of_entities in predefined_classes.items():
            if entity in list_of_entities:
                create_link_entity_class(entity_name=entity, most_similar_class_name=predefined_class, most_similar_class_score=0.7)
            else:
                continue
        # Create link between entity and class via cosine similarity
        most_similar_class_nodes = get_most_similar_class_nodes(entity_name=entity)
        best_class_node = list(most_similar_class_nodes)[0]
        best_class_node_score = list(most_similar_class_nodes.values())[0]
        create_link_entity_class(entity_name=entity, most_similar_class_name=best_class_node, most_similar_class_score=best_class_node_score)
        for class_node, score in most_similar_class_nodes.items():
            if score > class_threshold:
                create_link_entity_class(entity_name=entity, most_similar_class_name=class_node, most_similar_class_score=score)
