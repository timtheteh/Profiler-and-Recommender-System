import datetime
import json
import os
import random
import string
import neo4j
import requests
from fastchat.constants import LOGDIR
import fasttext

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
        if (phrase+" ") in textContent and textContent.find(phrase) == 0:
            textName_entities[textName].append(phrase)
            continue
        elif (phrase+" ") in textContent:
            for punctuation in punctuationList:
                if (punctuation+phrase+" ") in textContent:
                    textName_entities[textName].append(phrase)
            continue
        elif (" "+phrase) in textContent and textContent.rfind(phrase)+len(phrase)-1 == len(textContent)-1:
            textName_entities[textName].append(phrase)
            continue
        elif (" "+phrase) in textContent:
            for punctuation in punctuationList:
                if (" "+phrase+punctuation) in textContent:
                    textName_entities[textName].append(phrase)
            continue
        elif (" "+phrase+" ") in textContent:
            textName_entities[textName].append(phrase)
            continue

print("Document names and their entities: ", textName_entities, '\n')

# for document, entity_list in textName_entities.items():
#     create_document_node(document) #creates a user node only if it does not already exist
#     now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
#     for entity in entity_list:
#         entityVector = sentence2vecModel.get_sentence_vector(entity)
#         create_entity_node(entity_name=entity, vector=entityVector, datetime=now)
#         create_link_document_entity(doc_name=document, entity_name=entity, weight=0.7)
