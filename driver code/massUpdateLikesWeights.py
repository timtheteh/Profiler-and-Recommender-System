import datetime
import math
import neo4j

dbms_username = "neo4j"
dbms_password = "P@ssw0rd"
probability_rate = 0.5

graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)

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

def get_relationship_freq_id_rec_datetime():
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

# print(get_relationship_freq_id())

def update_relationship_properties(id, rec, weight):
    with graphDB.session() as session:
        session.run("""
            MATCH (node1:User)-[rel:LIKES]-(node2:Entity) 
            WHERE id(rel) = $id
            SET rel.rec = $rec, rel.weight = $weight
            """, parameters = {
                "id": id,
                "rec": rec, 
                "weight": weight
            })

for id, properties in get_relationship_freq_id_rec_datetime().items():
    freq, datetimeadded = properties[0], properties[1]

    datetime_object = datetime.datetime.strptime(datetimeadded, "%Y-%m-%dT%H:%M:%S")
    now = datetime.datetime.now()
    time_delta = now - datetime_object
    rec = (time_delta.total_seconds())/(24*60*60)

    weight = calculate_weight(freq=freq, rec=rec)

    update_relationship_properties(id=id, rec=rec, weight=weight)


