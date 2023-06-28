import json
import requests
import os
from fastchat.constants import LOGDIR
import neo4j
import fasttext

es_url = "https://localhost:9200"
index="test2"
es_username = "elastic"
es_password = "Bpax3twWeqg3Tg*IH6pY"
dbms_username = "neo4j"
dbms_password = "P@ssw0rd"
file_path = "datetime.txt"
filename = os.path.join(LOGDIR, f"{file_path}")
FASTCHAT_ENDPOINT = "http://127.0.0.1:7861/v1/chat/completions"
graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)

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
        “entities”: [iphone]
    }

    Q: Extract the entity or entities in this question in JSON format: "Singapore is a small island nation in South-East Asia."
    A: {
        “entities”: [Singapore, South-East Asia]
    }

    Q: Extract the entity or entities in this question in JSON format: "Why is China and the USA in a trade war?"
    A: {
        “entities”: [China, USA, trade war]
    }

    Q: Extract the entity or entities in this question in JSON format: "How many teams are there in the NBA?"
    A: {
        “entities”: [NBA]
    }

    Q: Extract the entity or entities in this question in JSON format: "What are the most pressing concerns in the world today?"
    A: {
        “entities”: [World Conflicts]
    }

    Q: Extract the entity or entities in this question in JSON format: "Given the tumultuous political climate between China and Taiwan, how likely is it that China launches an offensive attack on Taiwan?"
    A: {
        “entities”: [China, Taiwan, Global politics, War]
    }

    Q: Extract the entity or entities in this question in JSON format : "What is the weather for today? Should I bring an umbrella?".
    A: {
        “entities”: [Weather, Umbrella]
    }

    Q: Extract the entity or entities in this question in JSON format: "Hi what is a turtle?".
    A: {
        “entities”: [Turtle]
    }

    Q: Extract the entity or entities in this question in JSON format: "%s".
    A: 
    """%(text)

def create_user_node(node_name):
    with graphDB.session() as session:
        session.run("MERGE (n:User {name: $name}) RETURN n", parameters = {
                "name": node_name,
            })

def calculate_weight(freq, rec):
    return 

# this function adds entities and their corresponding relationship links with users
def conditionally_add_entity_node(entity_name, user_name):
    with graphDB.session() as session:
        # first check if the entity in question already exists in the graph
        entity_exists = session.run("""
            MATCH (n {name: $name}) 
            RETURN n
            """, parameters = {
                "name": entity_name,
            })
        relationship_exists = session.run("""
            MATCH (node1:User {name: $user_name})-[rel:LIKES]-(node2:Entity {name: $entity_name}) 
            RETURN rel.count
            """, parameters = {
                "user_name": user_name,
                "entity_name": entity_name
            })
        # if entity already exists, this means that the entity that the user searched for is 
        # already a generic node (eg. Airforce planes). These nodes already preprocessed,
        # meaning they are already connected with the "class" label nodes
        if entity_exists: 
            # if the relationship between this node already exists, we will have update the 
            # properties of the link between the entity in question and the user
            if relationship_exists:
                new_count = relationship_exists['rel.count']
                new_count += 1
                weight = getWeight(new_count, days=0)
                session.run("""
                MATCH (node1:User {name: $user_name})-[rel:LIKES]-(node2:Entity {name: $entity_name}) 
                SET rel.count = $new_count, rel.days = $days, rel.weight = $weight
                RETURN rel.count
                """, parameters = {
                    "user_name": user_name,
                    "entity_name": entity_name,
                    "new_count": new_count,
                    "days": 0, 
                    "weight": weight
                })
            # else, if the entity already exists but there is no relationship between user and entity
            # form a link with the desired properties (count, days, weight)
        # if the entity does not exist
        # 1. calculate the vector for the entity
        # 2. create the entity node temporarily (with a vector property)
        # 3. Do an apoc cosine similarity search to find the most similar "entity" node
        # 4. If the similarity < threshold, leave the created node alone
            # 4i. Do an apoc cosine cimilarity sarch with all the predefined "class" label nodes 
                # and form a "similar" relationship between them
        # 5. Else if the similarity > threshold, form a link between user and the most similar node
            # 5i. Delete the created entity node in question

        result = session.run("MERGE (n:Entity {name: $name}) RETURN n", name=entity_name)
        print(result.single())

# Get all NEW user_queries in dictionary -> {query: [count, datetime, ip_addr]}
with open(filename, 'r') as f:
    datetimefromfile = f.read()
user_queries = get_new_documents_user_inputs(datetimefromfile)
print("User queries: ", user_queries)

entities = {}
for query in user_queries.keys():
    user_ip_address = user_queries[query][2]
    create_user_node(user_ip_address) #creates a user node only if it does not already exist
    
    freq = user_queries[query][0]
    rec = today - user_queries[query][1]

    prompt = createPrompt(query)
    temperature = 0
    vicuna_answer = getVicunaAnswer(prompt, temperature)

    json_answer = json.loads(vicuna_answer)
    entities_from_answer = json_answer["entities"] #this is a list
    for ent in entities_from_answer:
        entities[ent] = [freq, rec, user_ip_address]



print("List of entities: ", entities)
    













# for ent in entities:
#     create_entity_node(ent)

# with graphDB.session() as session:
#     results = session.run("MATCH (n:Entity) RETURN n.name")
#     for record in results:
#         print(record['n.name'])







