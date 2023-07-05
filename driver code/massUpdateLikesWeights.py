import datetime
import math
import neo4j

dbms_username = "neo4j"
dbms_password = "P@ssw0rd"
probability_rate = 0.5
num_days_before_freq_reset = 10
graphDB = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=(f"{dbms_username}", f"{dbms_password}"), encrypted=False)

class massUpdate:

    def __init__(self):
        pass

    def calculate_weight(self, freq, rec):
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

    def get_relationship_freq_id_rec_datetime(self):
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

    def update_all_relationship_properties(self, freq, id, rec, weight):
        with graphDB.session() as session:
            session.run("""
                MATCH (node1:User)-[rel:LIKES]-(node2:Entity) 
                WHERE id(rel) = $id
                SET rel.rec = $rec, rel.weight = $weight, rel.freq = $freq
                """, parameters = {
                    "id": id,
                    "rec": rec, 
                    "weight": weight,
                    "freq": freq
                })
    
    def update_all_similar_relationship_properties(self):
        with graphDB.session() as session:
            session.run("""
            MATCH (node1:Entity)-[rel:IS_SIMILAR_TO]-(node2:Class) 
            WITH node1, node2, rel, gds.similarity.cosine(node1.vector,node2.vector) as similarity
            SET rel.weight = similarity
            """)
    
    def reverseDirectionOfAllLinks(self):
        with graphDB.session() as session:
            session.run("""
                MATCH (u:User)-[rel:LIKES]-(e:Entity)
                CALL apoc.refactor.invert(rel)
                yield input, output
                RETURN input, output
                """)
        with graphDB.session() as session:
            session.run("""
                MATCH (e:Entity)-[rel2:IS_SIMILAR_TO]-(c:Class)
                CALL apoc.refactor.invert(rel2)
                yield input, output
                RETURN input, output
                """)

    def massUpdateGraphRelationships(self):
        for id, properties in self.get_relationship_freq_id_rec_datetime().items():
            freq, datetimeadded = properties[0], properties[1]

            datetime_object = datetime.datetime.strptime(datetimeadded, "%Y-%m-%dT%H:%M:%S")
            now = datetime.datetime.now()
            time_delta = now - datetime_object
            rec = (time_delta.total_seconds())/(24*60*60)

            # if recency is more than 10 days, 
            # reset freq to be 0, and then calculate the new_weight
            if rec > num_days_before_freq_reset*24*60*60:
                freq = 0
                weight = self.calculate_weight(freq=freq, rec=rec)
                self.update_all_relationship_properties(freq=freq, id=id, rec=rec, weight=weight)
            # else, the frequency of the search is still relevant
            else:
                weight = self.calculate_weight(freq=freq, rec=rec)
                self.update_all_relationship_properties(freq=freq, id=id, rec=rec, weight=weight)

x = massUpdate()
# x.massUpdateGraphRelationships()
# x.update_all_similar_relationship_properties()
x.reverseDirectionOfAllLinks()
