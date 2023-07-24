import json
import math
import random
from graphdatascience import GraphDataScience
import requests
import os
from fastchat.constants import LOGDIR
import neo4j
import fasttext
import datetime
import massUpdateLikesWeights
import string 
import massPrune

import json
from flask import Flask, app, jsonify, make_response, request
from flask_cors import CORS, cross_origin
import requests
import heapq
from heapq import nlargest
# CORS(app, support_credentials=True)
# app.config['CORS_HEADERS'] = 'Content-Type'

### Databases ###
# Elastic Search -> where logs are retrieved
es_url = "https://localhost:9200"
index="test2"
es_username = "elastic"
es_password = "63jFV0cEXUfJziJ0ZMxL"
# Neo4j graph database
dbms_username = "neo4j"
dbms_password = "P@ssw0rd"
graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)

### Parameters ###
# Parameter 1 (for LLM): LLM temperature -> higher means more variation in answer, set to 0 for most consistent results
vicuna_temperature = 0
# Parameter 2 (to see if entity in question is similar to any existing nodes): change this to have less new nodes in graph. lower -> less new nodes
threshold_for_similarity = 0.9
# Parameter 3 (for weights of LIKES relationship): change this to have gradual/drastic changes in probability of weights
probability_rate = 0.9
# Parameter 4 (to see if entity in question is similar to any class nodes) change this to have node point to more classes
class_threshold = 0.6
# Parameter 5: after this number of days, frequency of query is no longer relevant and consequently, wieght of LIKES relationship is zero.
num_days_before_freq_reset = 10

### Models ###
# LLM Endpoint for generative chat completions / summary / entity extraction
FASTCHAT_ENDPOINT = "http://127.0.0.1:7861/v1/chat/completions"
# Sentence vectoriser (to generate vector embeddings of entities and classes)
file_path = "/home/grace/grace/vicuna/FastChat/profiler/model.bin"
sentence2vecModel = fasttext.load_model(file_path)

### Whitelist ###
# whitelist_file_path = "profiler/newEntityList2.txt"
whitelist_filename = os.path.join("/home/grace/grace/vicuna/FastChat/profiler/newEntityList2.txt")
with open(whitelist_filename, 'r') as f:
    whitelist_string = f.read()
whitelist = whitelist_string.split("\n")
punctuationString = string.punctuation
punctuationList=[*punctuationString]

### Locations List ###
# locations_file_path = "profiler/Locations.txt"
locations_filename = os.path.join("/home/grace/grace/vicuna/FastChat/profiler/Locations.txt")
with open(locations_filename, 'r') as f:
    locations_string = f.read()
locations = locations_string.split("\n")

### Predefined Classes ###
whiteListChunks = [whitelist[x:x+70] for x in range(0, len(whitelist), 70)]
count = 1
predefined_classes = {}
for chunk in whiteListChunks:
    category_name = "Category "+str(count)
    predefined_classes[category_name] = chunk
    count+=1
predefined_classes['Location'] = locations

##########################################################################################################################
### Elastic Search Functions ###
# Retrieve the datetime of the latest query in the logs
file_path = "./datetime.txt"
filename = os.path.join(LOGDIR, f"{file_path}")
# Datetime of the latest query based on the last search is used as the basis to see if there are any new logs
# Elastic search index is queried based on this datetime -> return any logs that have datetime greater than this datetime
# These NEW logs are stored in user_queries
# user_queries -> {query: frequency, datetime of message, user's ip address}
# def get_new_documents_user_inputs(timestamp):
#     """Gets all documents in the index that were indexed after the specified document ID."""
#     query = {
#         "size": 200,
#         "query": {
#             "bool": {
#                 "must": [
#                     {
#                         "range": {
#                             "datetime": {
#                                 "gt": timestamp
#                             }
#                         }
#                     }
#                 ]
#             }
#         }
#     }

#     user_queries = {}

#     response = requests.get(f"{es_url}/{index}/_search", headers={"Content-Type": "application/json"}, json=query, auth=(f"{es_username}", f"{es_password}"), verify=False)
#     response_dict = json.loads(response.content.decode("utf-8")) 

#     datetime_list = []

#     documents = response_dict['hits']['hits']

#     if documents:
#         for doc in documents:
#             messages = doc['_source']['state']['messages']
#             curr_datetime = doc['_source']['datetime']
#             datetime_list.append(curr_datetime)
#             user_ip_address = doc['_source']['ip']
#             for message in messages:
#                 if message[0] == 'USER':
#                     if message[1] not in user_queries:
#                         user_queries[message[1]] = [1, curr_datetime, user_ip_address]
#                     else:
#                         user_queries[message[1]][0] += 1
#                         user_queries[message[1]][1] = curr_datetime
#                         user_queries[message[1]][2] = user_ip_address
#     else:
#         return 0

#     latest_datetime = max(datetime_list)
#     filename = "datetime.txt"
#     file_path= os.path.join(LOGDIR, f"{filename}")
#     with open(file_path, "w") as file:
#         file.write(latest_datetime)    
#     print(response_dict['hits']['total']['value'])
#     print('latest datetime is: ', latest_datetime)
#     return user_queries

def get_conv_log_filename():
    t = datetime.datetime.now()
    name = os.path.join("/home/grace/grace/vicuna/FastChat/", f"{t.year}-{t.month:02d}-{t.day:02d}-conv.json")
    return name

def get_latest_log_data():
    user_queries = {}
    with open(get_conv_log_filename(), 'r') as fout:
        for line in fout:
            pass
        last_line = line
    json_object = json.loads(last_line)
    curr_datetime = json_object['datetime']
    user_ip_address = json_object['ip']
    messages = json_object['state']['messages']
    for message in messages:
        if message[0] == 'USER':
            if message[1] not in user_queries:
                user_queries[message[1]] = [1, curr_datetime, user_ip_address]
            else:
                user_queries[message[1]][0] += 1
                user_queries[message[1]][1] = curr_datetime
                user_queries[message[1]][2] = user_ip_address
    return user_queries

##########################################################################################################################
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
    Q: Extract the entity or entities in this question in JSON format: "How much is an iphone?"
    A: {
        “entities”: ["iphone"]
    }

    Q: Extract the entity or entities in this question in JSON format: "Singapore is a small island nation in South-East Asia."
    A: {
        “entities”: ["Singapore", "South-East Asia"]
    }

    Q: Extract the entity or entities in this question in JSON format: "Why is China and the USA in a trade war?"
    A: {
        “entities”: ["China", "USA", "trade war"]
    }

    Q: Extract the entity or entities in this question in JSON format: "How many teams are there in the NBA?"
    A: {
        “entities”: ["NBA"]
    }

    Q: Extract the entity or entities in this question in JSON format: "What are the most pressing concerns in the world today?"
    A: {
        “entities”: ["World Conflicts"]
    }

    Q: Extract the entity or entities in this question in JSON format: "Given the tumultuous political climate between China and Taiwan, how likely is it that China launches an offensive attack on Taiwan?"
    A: {
        “entities”: ["China", "Taiwan", "Global politics", "War"]
    }

    Q: Extract the entity or entities in this question in JSON format : "What is the weather for today? Should I bring an umbrella?".
    A: {
        “entities”: ["Weather", "Umbrella"]
    }

    Q: Extract the entity or entities in this question in JSON format: "Hi what is a turtle?".
    A: {
        “entities”: ["Turtle"]
    }

    Q: Extract the entity or entities in this question in JSON format: "What are paces?".
    A: {
        “entities”: ["Paces"]
    }

    Q: Extract the entity or entities in this question in JSON format: "%s".
    A: 
    """%(text)

##########################################################################################################################
### Node Creations ####
# node with 'User' label is created. Its only property is its name
# In our demo case, the name is the user's ip address eg. '127.0.0.1'
def create_user_node(node_name, datetimeadded):
    with graphDB.session() as session:
        session.run("""
        MERGE (n:User {name: $name}) 
        SET n.datetimeadded = $datetimeadded
        RETURN n
        """, parameters = {
            "name": node_name,
            "datetimeadded": datetimeadded
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

##########################################################################################################################
### Graph checks ###
def check_existence_entity(entity_name):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (u:Entity {name: $entity_name})
        WITH COUNT(u) > 0  as node_exists
        RETURN node_exists
        """, parameters={
            "entity_name": entity_name
        })
        record = result.single()
        return record['node_exists']    

def check_existence_relationship(user_name, entity_name):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (node1:User {name: $user_name})-[rel:LIKES]-(node2:Entity {name: $entity_name}) 
        WITH COUNT(rel) > 0 as relationship_exists
        RETURN relationship_exists
        """, parameters={
            "user_name": user_name, 
            "entity_name": entity_name
        })
        record = result.single()
        return record['relationship_exists'] 

def check_if_num_entities_is_more_than_one():
    with graphDB.session() as session:
        result = session.run("""
        MATCH (u:Entity)
        WITH COUNT(u) > 1  as more_than_one_exists
        RETURN more_than_one_exists
        """)
        record = result.single()
        return record['more_than_one_exists'] 

##########################################################################################################################
### Node Functions ###
def get_relationship_freq(user_name, entity_name):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (node1:User {name: $user_name})-[rel:LIKES]-(node2:Entity {name: $entity_name}) 
        RETURN rel.freq
        """, parameters={
            "user_name": user_name, 
            "entity_name": entity_name
        })
        record = result.single()
        return record['rel.freq']

def delete_entity_node(entity_name):
    with graphDB.session() as session:
        session.run(""" 
        MATCH (ent1:Entity {name: $entity_name})
        DETACH DELETE ent1
        """, parameters={
            "entity_name": entity_name
        })

def update_entity_datetimeadded(entity_name, datetimeadded):
    with graphDB.session() as session:
        session.run("""
            MATCH (node2:Entity {name: $entity_name}) 
            SET node2.datetimeadded = $datetimeadded
            """, parameters = {
                "entity_name": entity_name,
                "datetimeadded": datetimeadded
            })
        
##########################################################################################################################
### Relationship Functions###
def calculate_weight(freq, rec):
    freq_probability = 1 - math.exp(-probability_rate * freq/2)
    # print('freq_probability: ', freq_probability)
    rec_probability = math.exp(-probability_rate * rec)
    # print("rec probability: ", rec_probability)
    if freq_probability < 0.1 or rec_probability < math.exp(-probability_rate * num_days_before_freq_reset): 
        return 0
    else:
        new_probability = (freq_probability+rec_probability)/2
        if new_probability > 1:
            return 1
        elif new_probability < 0:
            return 0
        else:
            return new_probability

# Update the LIKES relationship 
def update_relationship_properties(user_name, entity_name, freq, rec, weight):
    with graphDB.session() as session:
        session.run("""
            MATCH (node1:User {name: $user_name})-[rel:LIKES]-(node2:Entity {name: $entity_name}) 
            SET rel.freq = $freq, rel.rec = $rec, rel.weight = $weight
            """, parameters = {
                "user_name": user_name,
                "entity_name": entity_name,
                "freq": freq,
                "rec": rec, 
                "weight": weight
            })

# Create LIKE relationship (from user -> entity)
def create_link_user_entity(user_name, entity_name, freq, rec, weight):
    with graphDB.session() as session:
        session.run("""
            MATCH (node1:User {name: $user_name})
            MATCH (node2:Entity {name: $entity_name})
            MERGE (node1)-[rel:LIKES]-(node2) 
            SET rel.freq = $freq, rel.rec = $rec, rel.weight = $weight
            """, parameters = {
                "user_name": user_name,
                "entity_name": entity_name,
                "freq": freq,
                "rec": rec, 
                "weight": weight
            })

# new relationship (from entity -> user)
# to make users as the new 'sinks' in the graph
# this new link is called "IS_AN_INTEREST_OF"
def create_link_entity_user(user_name, entity_name, freq, rec, weight):
    with graphDB.session() as session:
        session.run("""
            MATCH (node1:User {name: $user_name})
            MATCH (node2:Entity {name: $entity_name})
            MERGE (node1)<-[rel:IS_AN_INTEREST_OF]-(node2) 
            SET rel.freq = $freq, rel.rec = $rec, rel.weight = $weight
            """, parameters = {
                "user_name": user_name,
                "entity_name": entity_name,
                "freq": freq,
                "rec": rec, 
                "weight": weight
            })

# Create IS_SIMILAR_TO relationship (from entity -> class)
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

# new relationship (from class -> entity)
# to avoid 'Class' nodes from being sinks
# this new link is called "EXAMPLE"
def create_link_class_entity(entity_name, most_similar_class_name, most_similar_class_score):
    with graphDB.session() as session:
        session.run("""
        MATCH (ent1:Entity {name: $entity_name})
        MATCH (class:Class {name: $class_name})
        MERGE (ent1)<-[r1:EXAMPLE]-(class)
        SET r1.weight = $similarity_score
        """, parameters={
            "entity_name": entity_name,
            "class_name": most_similar_class_name,
            "similarity_score": most_similar_class_score
        })

##########################################################################################################################
### Similarity Functions ###
# returns the entity node that the entity in question is more similar to {'entity': score}
def get_most_similar_entity_node(entity_name):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (ent1:Entity {name: $entity_name}),(ent2:Entity)
        WHERE ent1 <> ent2
        WITH ent1, ent2, gds.similarity.cosine(ent1.vector,ent2.vector) as similarity
        RETURN ent2.name, similarity ORDER BY similarity DESC LIMIT 1
        """, parameters={
            "entity_name": entity_name
        })
        record = result.single()
        ans = [record['ent2.name'], record['similarity']]
        return ans

# returns the class node(s) that the entity in question is more similar to {'class': score}
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

##########################################################################################################################
# Main function to add entities 
### Test Case 1 ###
# 1. A node of the same name as the entity in question (EIQ) already exists
# 2. There is an existing LIKES relationship between this node and the user
# Action: update this relationship's properties (freq, rec, weight) based on logs
# and update the datetimeadded of the entity

### Test Case 2 ###
# 1. A node of the same name as the entity in question (EIQ) already exists
# 2. There is NO existing LIKES relationship between this node and the user
# Action: form a new LIKES relationship between user and the entity 
# and give its properties (freq, rec, weight) based on logs
# and update the datetimeadded of the entity

### Test Case 3 ###
# 1. A node of the same name as the entity in question (EIQ) DOES NOT already exist 
# Action: create the EIQ first with its corresponding vector embedding and datetimeadded
# and create link between entity and class via predefined relationships if entity is in the predefined list
# 2. Find the most similar existing entity node in the graph and its similarity score
# 3. Similarity score is < threshold_for_similarity (not similar to any existing node)
# Action: form a new LIKES relationship between user and EIQ 
# and find the most similar 'Class' node(s) to link it to

### Test Case 4 ###
# 1. A node of the same name as the entity in question (EIQ) DOES NOT already exist 
# Action: create the EIQ first with its corresponding vector embedding and datetimeadded
# 2. Find the most similar existing entity node in the graph and its similarity score
# 3. Similarity score is > threshold_for_similarity (there is already a node similar to EIQ)
# 4. A relationship between user and this node already exists
# Action: update this relationship's properties (freq, rec, weight) based on logs
# and delete the EIQ

### Test Case 5 ###
# 1. A node of the same name as the entity in question (EIQ) DOES NOT already exist 
# Action: create the EIQ first with its corresponding vector embedding and datetimeadded
# 2. Find the most similar existing entity node in the graph and its similarity score
# 3. Similarity score is > threshold_for_similarity (there is already a node similar to EIQ)
# 4. A relationship between user and this node DOES NOT already exist
# Action: form a new LIKES relationship between user and the entity 
# and give its properties (freq, rec, weight) based on logs
# and delete the EIQ

### Test Case 6 ### Base Case ###
# 1. A node of the same name as the entity in question (EIQ) DOES NOT already exist 
# Action: create the EIQ first with its corresponding vector embedding and datetimeadded
# 2. EIQ is the only entity node in graph
# Action: form a new LIKES relationship between user and the entity 
# and give its properties (freq, rec, weight) based on logs
# and link EIQ to the correct classes
def conditionally_add_entity_node(entity_name, user_name, freq, rec, threshold, dateaddedorupdated):
    entity_name = entity_name.lower()
    if check_existence_entity(entity_name): 
        ### Test Case 1 ###
        update_entity_datetimeadded(entity_name=entity_name, datetimeadded=dateaddedorupdated)
        if check_existence_relationship(user_name=user_name, entity_name=entity_name):
            count = get_relationship_freq(user_name=user_name, entity_name=entity_name)
            new_count = count + freq
            weight = calculate_weight(new_count, rec)
            update_relationship_properties(user_name=user_name, entity_name=entity_name, freq=new_count, rec=rec, weight=weight)
        ### Test Case 2 ###
        else:
            weight = calculate_weight(freq, rec)
            create_link_user_entity(user_name=user_name, entity_name=entity_name, freq=freq, rec=rec, weight=weight)
    else:  
        entityVector = sentence2vecModel.get_sentence_vector(entity_name)
        create_entity_node(entity_name, entityVector, datetime=dateaddedorupdated)
        if check_if_num_entities_is_more_than_one():
            most_similar_node = get_most_similar_entity_node(entity_name=entity_name)
            most_similar_node_name, most_similar_node_score = most_similar_node[0], most_similar_node[1]
            ### Test Case 3 ###
            if most_similar_node_score < threshold:
                weight = calculate_weight(freq, rec)
                create_link_user_entity(user_name=user_name, entity_name=entity_name, freq=freq, rec=rec, weight=weight)
                # Create link between entity and class via predefined relationships if entity is in the predefined list
                for predefined_class, list_of_entities in predefined_classes.items():
                    if entity_name in list_of_entities:
                        print("\nentity belongs to: ", predefined_class, '\n')
                        create_link_entity_class(entity_name=entity_name, most_similar_class_name=predefined_class, most_similar_class_score=random.uniform(0.3, 0.9))
                    else:
                        continue
                # Create link between entity and class via cosine similarity
                most_similar_class_nodes = get_most_similar_class_nodes(entity_name=entity_name)
                best_class_node, best_class_node_score = None, None
                if len(most_similar_class_nodes) > 0:
                    best_class_node = list(most_similar_class_nodes)[0]
                    best_class_node_score = list(most_similar_class_nodes.values())[0]
                    create_link_entity_class(entity_name=entity_name, most_similar_class_name=best_class_node, most_similar_class_score=best_class_node_score)
                    for class_node, score in most_similar_class_nodes.items():
                        if score > class_threshold:
                            create_link_entity_class(entity_name=entity_name, most_similar_class_name=class_node, most_similar_class_score=score)
            else:
                ### Test Case 4 ###
                if check_existence_relationship(user_name=user_name, entity_name=most_similar_node_name):
                    count = get_relationship_freq(user_name=user_name, entity_name=most_similar_node_name)
                    new_count = count + freq
                    weight = calculate_weight(new_count, rec)
                    update_relationship_properties(user_name=user_name, entity_name=most_similar_node_name, freq=new_count, rec=rec, weight=weight)
                ### Test Case 5 ###
                else:
                    weight = calculate_weight(freq, rec)
                    create_link_user_entity(user_name=user_name, entity_name=most_similar_node_name, freq=freq, rec=rec, weight=weight)
                delete_entity_node(entity_name=entity_name)
        else:
            print('hi i am here @!!!!!')
            weight = calculate_weight(freq, rec)
            create_link_user_entity(user_name=user_name, entity_name=entity_name, freq=freq, rec=rec, weight=weight)
            # Create link between entity and class via predefined relationships if entity is in the predefined list
            for predefined_class, list_of_entities in predefined_classes.items():
                print("hi i am here: ", predefined_class)
                if entity_name in list_of_entities:
                    print('hi')
                    create_link_entity_class(entity_name=entity_name, most_similar_class_name=predefined_class, most_similar_class_score=random.uniform(0.3, 0.9))
                    print('bye')
                else:
                    continue
            # Create link between entity and class via cosine similarity
            most_similar_class_nodes = get_most_similar_class_nodes(entity_name=entity_name)
            best_class_node = list(most_similar_class_nodes)[0]
            best_class_node_score = list(most_similar_class_nodes.values())[0]
            create_link_entity_class(entity_name=entity_name, most_similar_class_name=best_class_node, most_similar_class_score=best_class_node_score)
            for class_node, score in most_similar_class_nodes.items():
                if score > class_threshold:
                    create_link_entity_class(entity_name=entity_name, most_similar_class_name=class_node, most_similar_class_score=score)


import neo4j
from numpy import dot
from numpy.linalg import norm
import time
from heapq import nlargest

user_name = "127.0.0.1"
graph_name = "test"

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

def getDocumentContents(doc_name):
    with graphDB.session() as session:
        result = session.run("""
            MATCH (d:Document {name: $doc_name})
            RETURN d.content
            """, parameters = {
                "doc_name": doc_name
            })
        record = result.single()
        return record['d.content']

def getAllDocuments():
    doc_names_list = []
    with graphDB.session() as session:
        result = session.run("""
            MATCH (d:Document)
            RETURN d.name
            """)
        records = result.data()
        for record in records:
            doc_name = record['d.name']
            doc_names_list.append(doc_name)
        return doc_names_list

##########################################################################################################################
#### Driver code ####
# Get all NEW user_queries in dictionary -> {query: [count, datetime, ip_addr]}
app = Flask(__name__)
CORS(app)

@app.route('/addToProfile', methods=['POST'])
def addToProfile():
    # with open(filename, 'r') as f:
    #     datetimefromfile = f.read()
    user_queries = get_latest_log_data()
    print("User queries: ", user_queries)
    # if there are user_queries, 
    # 1. extract entities from each query
    # 2. add the entities into graph with the name, datetimeadded and vector
    # 3. add the relationships (user-entity, entity-class) with the properties: freq, rec, weight
    # 4. update all the relationships weights based on current time
    if user_queries:
        entities = {}
        for query in user_queries.keys():
            # Get the necessary properties from logs: user_ip_address, freq, datetime_from_query, rec
            user_ip_address = user_queries[query][2]
            freq = user_queries[query][0]
            datetime_from_query = user_queries[query][1]
            datetime_object = datetime.datetime.strptime(datetime_from_query, "%Y-%m-%dT%H:%M:%S")
            now = datetime.datetime.now()
            time_delta = now - datetime_object
            rec = (time_delta.total_seconds())/(24*60*60) 

            # Get specific entities from query using whitelist
            query = query.lower()
            entities_from_answer = []
            for phrase in whitelist:
                if (" "+phrase+" ") in query:
                    entities_from_answer.append(phrase)
                    continue
                elif (phrase+" ") in query and query.find(phrase) == 0:
                    entities_from_answer.append(phrase)
                    continue
                elif (phrase+" ") in query:
                    for punctuation in punctuationList:
                        if (punctuation+phrase+" ") in query:
                            entities_from_answer.append(phrase)
                            break
                    continue
                elif (" "+phrase) in query and query.rfind(phrase)+len(phrase)-1 == len(query)-1:
                    entities_from_answer.append(phrase)
                    continue
                elif (" "+phrase) in query:
                    for punctuation in punctuationList:
                        if (" "+phrase+punctuation) in query:
                            entities_from_answer.append(phrase)
                            break
                    continue
                
            # Get SG locations from query using whitelist
            for loc in locations:
                if (" "+loc+" ") in query:
                    entities_from_answer.append(loc)
                    continue
                elif (loc+" ") in query and query.find(loc) == 0:
                    entities_from_answer.append(loc)
                    continue
                elif (loc+" ") in query:
                    for punctuation in punctuationList:
                        if (punctuation+loc+" ") in query:
                            entities_from_answer.append(loc)
                            break
                    continue
                elif (" "+loc) in query and query.rfind(loc)+len(loc)-1 == len(query)-1:
                    entities_from_answer.append(loc)
                    continue
                elif (" "+loc) in query:
                    for punctuation in punctuationList:
                        if (" "+loc+punctuation) in query:
                            entities_from_answer.append(loc)
                            print("\npunctuation part!!!\n")
                            break
                    continue
                
            # Get generic entities from query using vicuna
            prompt = createPrompt(query)
            vicuna_answer = getVicunaAnswer(prompt, vicuna_temperature)
            print(vicuna_answer)
            json_answer = json.loads(vicuna_answer)
            print("json answer: ", json_answer)
            entities_from_vicuna = json_answer["entities"]
            for ent in entities_from_vicuna:
                if ent.lower() not in entities_from_answer:
                    entities_from_answer.append(ent)

            for ent in entities_from_answer:
                entities[ent] = [freq, rec, user_ip_address, datetime_from_query]
        print("entities are here: ", entities)
        for entity, entity_properties in entities.items():
            print("the entity i am adding is: ", entity)
            freq, rec, user, dateaddedorupdated = entity_properties[0], entity_properties[1], entity_properties[2], entity_properties[3]
            create_user_node(user, datetimeadded=dateaddedorupdated) #creates a user node only if it does not already exist
            conditionally_add_entity_node(entity_name=entity, user_name=user, freq=freq, rec=rec, threshold=threshold_for_similarity, dateaddedorupdated=dateaddedorupdated)
            print('i have done the adding')
    else:
        print("No new user queries!")
    # # after adding entities, do one run of mass update of relationships
    x = massUpdateLikesWeights.massUpdate()
    x.massUpdateGraphLikesRelationships()

    y = massPrune.massPrune()
    y.massPruneGraph()

    return 'hi'

@app.route('/recommendDocumentandUser', methods=['GET'])
def recommendDocument():
    # # massUpdateAllRelationshipsToZero()
    # ### Pagerank algorithm ###
    # start_time = time.time()
    createPageRankGraph(graphName=graph_name)
    # timeToProjectGraph = time.time() - start_time

    sourceNodes = getUserInterestsAsSourceNodes(user_name=user_name)
    # print(sourceNodes, '\n')
    # start_time = time.time()
    recommendedDocument = personalisedPageRank(user_name=user_name, graph_name=graph_name, dampingFactor=0.85, typeOfNodeToRecommend='Document', sourceNodes=sourceNodes)
    # timeToRecommendDocument = time.time() - start_time
    if recommendedDocument:
        documentEntities = getDocumentEntities(recommendedDocument)
        print("Based on your interests, you might be interested in this document: ", recommendedDocument, ". It contains the following entities which might be of interest to you: ", documentEntities, ".\n")
    else:
        print("Sorry, it seems like none of the documents in the database are suitable to be recommeneded to you.\n")

    # ### Recommend similar users ###
    # start_time = time.time()
    graphEmbeddings = assignGraphEmbeddings(graphName=graph_name)
    # timeToAssignEmbeddings = time.time() - start_time
    user_embedding = getUserEmbedding(user_name=user_name, graphEmbeddings=graphEmbeddings)
    otherUsersIds = getOtherUsersIds(user_name=user_name)
    # timeToRecommendUser = 0
    if len(otherUsersIds) == 0:
        print("No other users to recommend!")
    else:
    #     start_time = time.time()
        otherUsersEmbeddings = {}
        for i in otherUsersIds:
            otherUserId = i['id(user2)']
            for j in graphEmbeddings:
                if j['nodeId'] == otherUserId:
                    otherUserEmbedding = j['embedding']
                    if not all(v == 0 for v in otherUserEmbedding):
                        otherUsersEmbeddings[otherUserId] = otherUserEmbedding
    #     # print("\n", otherUsersEmbeddings, "\n")
        otherUsersEmbeddingSimilarityScores = {}
        for id, embedding in otherUsersEmbeddings.items():
            cos_sim = dot(user_embedding, embedding)/(norm(embedding)*norm(user_embedding))
            otherUsersEmbeddingSimilarityScores[id] = cos_sim
    #     # print("other users embedding sim scores: ", otherUsersEmbeddingSimilarityScores, "\n")
    #     justToPrint = {}
    #     for u, score in otherUsersEmbeddingSimilarityScores.items():
    #         userName = getUserNameFromId(u)
    #         justToPrint[userName] = score
    #     print("other users: ", justToPrint, "\n")
        bestUser = None
        if len(otherUsersEmbeddings) != 0:
            # print("other users recommendations: ", otherUsersEmbeddingSimilarityScores, '\n')
            bestUserId = max(otherUsersEmbeddingSimilarityScores, key=otherUsersEmbeddingSimilarityScores.get)
            bestUser = getUserNameFromId(bestUserId)
            print("The profile that seems the most similar to your profile is: ", bestUser, '\n')
            # timeToRecommendUser = time.time() - start_time
        else:
            print("Sorry, it seems that there are no users that are similar to you.")

    document_contents = getDocumentContents(recommendedDocument)
    
    if recommendedDocument and bestUser:
        return '''
        Recommended document: %s
        Recommended user: %s

        Here are the contents of the document:

        %s
        '''%(recommendedDocument, bestUser, document_contents)
    elif recommendedDocument and not bestUser:
        return """
        Recommended document: %s
        Recommended user: Sorry there doesn't seem to be a similar user to you.
        
        Here are the contents of the document:
        """%(recommendedDocument, document_contents)

@app.route('/chooseBestUserToRecNewDocTo', methods=['GET'])
def chooseUserToRecommendNewDocumentTo():
    ### Choose which user to show document to ###
    new_document = request.data.decode("utf-8")
    source_nodes2 = getDocumentEntityIds(doc_name=new_document)
    print(source_nodes2, '\n')
    recommendedUser = personalisedPageRankDocToUser(doc_name=new_document, graph_name=graph_name, dampingFactor=0.85, typeOfNodeToRecommend='User', sourceNodes=source_nodes2)
    if recommendedUser:
        userEntities = getUserEntities(recommendedUser)
        print("The best user to show ", new_document, " to is: ", recommendedUser, ". This user likes the following overlapping entities: ", userEntities, ".\n")
        return recommendedUser
    else:
        print("Sorry, it seems like there is no appropriate user to show ", new_document, " to.\n")
        return "No User"

if __name__ == '__main__':
    app.run(debug=True, port=8001)
