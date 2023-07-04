import json
import math
from graphdatascience import GraphDataScience
import requests
import os
from fastchat.constants import LOGDIR
import neo4j
import fasttext
import datetime

es_url = "https://localhost:9200"
index="test2"
es_username = "elastic"
es_password = "Bpax3twWeqg3Tg*IH6pY"
dbms_username = "neo4j"
dbms_password = "P@ssw0rd"
file_path = "./datetime.txt"
filename = os.path.join(LOGDIR, f"{file_path}")
FASTCHAT_ENDPOINT = "http://127.0.0.1:7861/v1/chat/completions"
graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)
threshold_for_similarity = 0.65
vicuna_temperature = 0
probability_rate = 0.5
class_threshold = 0.35

# Load the downloaded FastText Model
file_path = "/home/grace/grace/vicuna/FastChat/profiler/model.bin"
sentence2vecModel = fasttext.load_model(file_path)

def get_new_documents_user_inputs(timestamp):
    """Gets all documents in the index that were indexed after the specified document ID."""
    query = {
        "size": 20,
        "query": {
            "bool": {
                "must": [
                    {
                        "range": {
                            "datetime": {
                                "gte": timestamp
                            }
                        }
                    }
                ]
            }
        }
    }

    user_queries = {}

    response = requests.get(f"{es_url}/{index}/_search", headers={"Content-Type": "application/json"}, json=query, auth=(f"{es_username}", f"{es_password}"), verify=False)
    response_dict = json.loads(response.content.decode("utf-8")) 

    datetime_list = []

    documents = response_dict['hits']['hits']
    if documents:
        for doc in documents:
            messages = doc['_source']['state']['messages']
            curr_datetime = doc['_source']['datetime']
            datetime_list.append(curr_datetime)
            user_ip_address = doc['_source']['ip']
            for message in messages:
                if message[0] == 'USER':
                    if message[1] not in user_queries:
                        user_queries[message[1]] = [1, curr_datetime, user_ip_address]
                    else:
                        user_queries[message[1]][0] += 1
                        user_queries[message[1]][1] = curr_datetime
                        user_queries[message[1]][2] = user_ip_address
    else:
        return 0

    latest_datetime = max(datetime_list)
    filename = "datetime.txt"
    file_path= os.path.join(LOGDIR, f"{filename}")
    with open(file_path, "w") as file:
        file.write(latest_datetime)    
    print(response_dict['hits']['total']['value'])
    print('latest datetime is: ', latest_datetime)
    return user_queries

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

    Q: Extract the entity or entities in this question in JSON format: "%s".
    A: 
    """%(text)

def create_user_node(node_name):
    with graphDB.session() as session:
        session.run("MERGE (n:User {name: $name}) RETURN n", parameters = {
                "name": node_name,
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

def calculate_weight(freq, rec):
    freq_probability = 1 - math.exp(-probability_rate * freq)
    rec_probability = probability_rate * math.exp(-probability_rate * rec)
    new_probability = freq_probability+rec_probability
    if new_probability > 1:
        return 1
    elif new_probability < 0:
        return 0
    else:
        return new_probability

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
        MATCH (node1:User)-[rel:LIKES]-(node2:Entity) 
        WHERE node1.name = '{user_name}' AND node2.name = '{entity_name}'
        WITH COUNT(rel) > 0 as relationship_exists
        RETURN relationship_exists
        """, parameters={
            "user_name": user_name, 
            "entity_name": entity_name
        })
        record = result.single()
        return record['relationship_exists']   

def get_relationship_freq(user_name, entity_name):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (node1:User)-[rel:LIKES]-(node2:Entity) 
        WHERE node1.name = '{user_name}' AND node2.name = '{entity_name}'
        RETURN rel.freq
        """, parameters={
            "user_name": user_name, 
            "entity_name": entity_name
        })
        record = result.single()
        return record['rel_freq']

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

# LIKE relationship
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

def delete_entity_node(entity_name):
    with graphDB.session() as session:
        session.run(""" 
        MATCH (ent1:Entity {name: $entity_name})
        DETACH DELETE ent1
        """, parameters={
            "entity_name": entity_name
        })

# IS_SIMILAR_TO relationship
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

def check_if_num_entities_is_one(entity_name):
    with graphDB.session() as session:
        result = session.run("""
        MATCH (u:Entity {name: $entity_name})
        WITH COUNT(u) > 1  as more_than_one_exists
        RETURN node_exists
        """, parameters={
            "entity_name": entity_name
        })
        record = result.single()
        return record['more_than_one_exists'] 

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

# this function adds entities and their corresponding relationship links with users
def conditionally_add_entity_node(entity_name, user_name, freq, rec, threshold, dateaddedorupdated):
    if check_existence_entity(entity_name): 
        # if the relationship between this node already exists, we will have to update the 
        # properties of the link between the entity in question and the user
        if check_existence_relationship(user_name=user_name, entity_name=entity_name):
            count = get_relationship_freq(user_name=user_name, entity_name=entity_name)
            new_count = count + freq
            weight = calculate_weight(new_count, rec)
            update_relationship_properties(user_name=user_name, entity_name=entity_name, freq=new_count, rec=rec, weight=weight)
        # else, if the entity already exists but there is no relationship between user and entity
        # form a link with the desired properties (count, days, weight)
        else:
            weight = calculate_weight(freq, rec)
            create_link_user_entity(user_name=user_name, entity_name=entity_name, freq=freq, rec=rec, weight=weight)
    else:  # if the entity does not exist
        # 1. calculate the vector for the entity
        entityVector = sentence2vecModel.get_sentence_vector(entity_name)
        # 2. create the entity node temporarily (with the vector property)
        create_entity_node(entity_name, entityVector, datetime=dateaddedorupdated)
        # 3. Do an apoc cosine similarity search to find the most similar "entity" node
        if not check_if_num_entities_is_one:
            most_similar_node = get_most_similar_entity_node(entity_name=entity_name)
            most_similar_node_name, most_similar_node_score = most_similar_node[0], most_similar_node[1]
            # 4. If the similarity < threshold, this means that entity in question is unique
            # leave the created node alone and form a link between user and the entity in question
            if most_similar_node_score < threshold:
                weight = calculate_weight(freq, rec)
                create_link_user_entity(user_name=user_name, entity_name=entity_name, freq=new_count, rec=rec, weight=weight)
                # 4i. Do an apoc cosine similarity sarch with all the predefined "class" label nodes 
                # and form a "similar" relationship between them
                # every node MUST BELONG TO A CLASS
                most_similar_class_nodes = get_most_similar_class_nodes(entity_name=entity_name)
                best_class_node = list(most_similar_class_nodes)[0]
                best_class_node_score = list(most_similar_class_nodes.values())[0]
                create_link_entity_class(entity_name=entity_name, most_similar_class_name=best_class_node, most_similar_class_score=best_class_node_score)
                for class_node, score in most_similar_class_nodes.items():
                    if score > class_threshold:
                        create_link_entity_class(entity_name=entity_name, most_similar_class_name=class_node, most_similar_class_score=score)
            else:
                # 5. Else if the similarity > threshold, form a link between user and the most similar node
                # 5i. Delete the created entity node in question
                # if the relationship between this node already exists, we will have to update the 
                # properties of the link between the entity in question and the user
                if check_existence_relationship(user_name=user_name, entity_name=most_similar_node_name):
                    count = get_relationship_freq(user_name=user_name, entity_name=most_similar_node_name)
                    new_count = count + freq
                    weight = calculate_weight(new_count, rec)
                    update_relationship_properties(user_name=user_name, entity_name=most_similar_node_name, freq=new_count, rec=rec, weight=weight)
                # else, if the entity already exists but there is no relationship between user and entity
                # form a link with the desired properties (count, days, weight)
                else:
                    weight = calculate_weight(freq, rec)
                    create_link_user_entity(user_name=user_name, entity_name=most_similar_node_name, freq=freq, rec=rec, weight=weight)
                delete_entity_node(entity_name=entity_name)
        else:
            weight = calculate_weight(freq, rec)
            create_link_user_entity(user_name=user_name, entity_name=entity_name, freq=freq, rec=rec, weight=weight)
            most_similar_class_nodes = get_most_similar_class_nodes(entity_name=entity_name)
            best_class_node = list(most_similar_class_nodes)[0]
            best_class_node_score = list(most_similar_class_nodes.values())[0]
            create_link_entity_class(entity_name=entity_name, most_similar_class_name=best_class_node, most_similar_class_score=best_class_node_score)
            for class_node, score in most_similar_class_nodes.items():
                print("class_node: ", class_node, " score: ", score)
                if score > class_threshold:
                    create_link_entity_class(entity_name=entity_name, most_similar_class_name=class_node, most_similar_class_score=score)

#### Driver code ####
# Get all NEW user_queries in dictionary -> {query: [count, datetime, ip_addr]}
with open(filename, 'r') as f:
    datetimefromfile = f.read()
user_queries = get_new_documents_user_inputs(datetimefromfile)
print("User queries: ", user_queries)

entities = {}
for query in user_queries.keys():
    user_ip_address = user_queries[query][2]

    freq = user_queries[query][0]
    
    datetime_from_query = user_queries[query][1]
    datetime_object = datetime.datetime.strptime(datetime_from_query, "%Y-%m-%dT%H:%M:%S")
    now = datetime.datetime.now()
    time_delta = now - datetime_object
    rec = (time_delta.total_seconds())/(24*60*60)

    prompt = createPrompt(query)
    vicuna_answer = getVicunaAnswer(prompt, vicuna_temperature)
    print(vicuna_answer)

    json_answer = json.loads(vicuna_answer)
    print("json answer: ", json_answer)
    entities_from_answer = json_answer["entities"] #this is a list
    for ent in entities_from_answer:
        entities[ent] = [freq, rec, user_ip_address, datetime_from_query]

print(entities)

for entity, entity_properties in entities.items():
    freq, rec, user, dateaddedorupdated = entity_properties[0], entity_properties[1], entity_properties[2], entity_properties[3]
    create_user_node(user) #creates a user node only if it does not already exist
    conditionally_add_entity_node(entity_name=entity, user_name=user, freq=freq, rec=rec, threshold=threshold_for_similarity, dateaddedorupdated=dateaddedorupdated)
