![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/4a106138-1568-4d5b-aa9e-43610e2dfb72)![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/2aa59cbf-bb96-4b5e-8d57-b6aa18cf6398)# Profiler and Recommender System

### What is the goal of this project?

1. To find a way to profile users based on their search inputs.
2. To find a way to improve the personalised pagerank algorithm results in Neo4j

### Methodology

**Solution**
To improve the results of the personalised pagerank algorithm, the graph database is manipulated:
1. User profiles in the graph database are enhanced by connecting users to the entities they searched for.
2. Each relationship in the graph is weighted. In particular, the 'LIKES' relationship between users and their entities are constantly updated based on the frequency of the query, and the recency of the query. 
3. 'Class' nodes are added to make the paths between documents and other documents, and documents to users, more connected. 

**Step 1: Initialising the Graph Database**
- Files: addPredefinedClasses.py, addingDocuments.py
- **addPredefinedClasses**:
  - This file initialises the graph database with predefined 'Class' nodes.
  - These are 'Class' nodes which act as generic nodes from which large groups of entities can be connected to.
- **addingDocuments**:
  - This file initialises the graph database with mock 'Document' nodes.
  - These nodes represent documents which will eventually be uploaded into the graph database.
  - Each document is randomly generated based on a list of keywords (a whitelist or domain specific keywords).
  - These documents will then have their entities extracted out (by means of text matching).
  - This is how the respective 'Document' nodes and their respective 'Entity' nodes are linked (via a 'HAS' relationship). The weight of each 'HAS' relationship is randomly assigned between 0.3 and 0.9.
  - These entities are also assigned to their predefined 'Class' nodes (via a 'IS_SIMILAR_TO' relationship. Likewise, the weight of each 'IS_SIMILAR_TO' relationship is randomly assigned between 0.3 and 0.9.

**Step 2: Logging and Adding Entities to Enhance a User's Profile**
- Files: loggingToES.py, addingToProfile.py
- **loggingToES**:
  - User's search inputs are logged into Elastic Search (batch queries)
  - These logs contain information about who is the user, what did they search for, the datetime of their query, just to name a few
- **addingToProfile:**
  - Elastic Search is then queried to only retrieve the new queries that have been added.
  - For each query, a 'User' node is created only if the user is a new user.
  - Based on these new queries, the entities are extracted with the help of a LLM (we used vicuna-7b) as well as text matching with a whitelist.
  - Each entity and its links to the user and 'Class' nodes are then created based on a few test cases. 
  - Some check include:
    - Does this entity already exist?
    - Is this entity aready similar to any existing node in the graph database? And is there already a relationship between the user and this entity?
    - If this is a new node, make sure to connect to at least one 'Class' node. This can be done so by the predefined 'Class' nodes or via cosine similarity (semantic comparisons)
    - Entities: datetimeadded, vector, name
    - 'LIKES' Relationship: freq, rec, weight
    - 'IS_SIMILAR_TO' Relationship: weight
  - At the end of each addition to the graph, each link's recency and weight properties in the graph is again updated.

**Step 3: Recommendation**
- File: recommendation.py
- A projection of the graph database is created. Nodes with no outgoing links are excluded to avoid unncessary 'sinks' in the personalised pagerank algorithm.
- **Document Recommendation**
  - For a personalised recommendation, source nodes are needed to bias the pagerank algorithm
  - These source nodes are the top k (eg. 5) entities which have the strongest links (based on weights) between the user. These top k entities represent the entities which the user is most interested in, and hence the pagerank algorithm will be biased based on these nodes (random jump to these source nodes with probability = 1 - damping_factor)
  - The inbuilt personalised pagerank algoritm in Neo4j is then run based on these source nodes as bias.
  - Nodes with 'Document' label will be filtered and the top N documents will be recommended to the user.
- **User Recommendation**
  - For now, each node in the graph will have a node embedding calculated for it using the inbuilt node2vec algorithm in Neo4j. (https://neo4j.com/docs/graph-data-science/current/machine-learning/node-embeddings/node2vec/)
  - Nodes with 'User' label apart from the user in question will be recommended as the most similar users to be recommended (similar interests).

# Testing and Results for Document Recommendations

### Test 1: Do weights improve the document recommendation?
### Result: Yes, weighted likes improve the correctness of the recommendation by forming a basis for the source nodes in personalised pagerank.

**CASE 1 & CASE 2:**

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/55b6ade1-6493-4aab-8b48-811bc3c77eb3)

- User '127.0.0.1':
    - Likes document 5 alot: [wave 10 times, airbase 10 times, tengah airbase 10 times, mob plan 5 times]
    - Likes as many entities in document 19 as in document 5, but the weights are different: [pulau 1 time, rand 1 time, stockpile 1 time, tekong 1 time]
    - Likes as many entities in document 3 as in document 5, but the weights are different: [hartford 1 time, fuel 1 time, fcu 1 time, petrol 1 time]
    - Likes as many entities in document 20 as in document 5, but the weights are different: [network 1 time, sf 1 time, network ids 1 time, ids 1 time]
    - Likes document 2 decently: [reserve 2 times, helicon 2 times]
    - Likes document 10 decently: [satcom 2 times, gstb 2 times]
    - Likes document 13 minimally: [executive 1 time]

**CASE 1:** Documents = 20, Weighted, Classes (Base Case)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/bc55e348-a5e1-4982-a10c-3dae65ee74e6)

**CASE 2:** Documents = 20, All weights = 100, Classes
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/524554a1-b213-4fde-a891-e3edc16dd59b)

### Analysis

The weighted case (Case 1) shows the correct document (Document 5) as the document to be recommended, which reaffirms that weighted links do help with the personalised recommendation.

In the unweighted case (Case 2) where the weights of each relationship is set the same at 100, the document it recommended is Document 20. The reason for this wrong recommendation is because in an unweighted case, the source nodes have little bias to the user as they are chosen at random (since all links are equal), leaving almost equal probability to pick any of the 4 documents (which have the most outgoing links from the pov of the user) as the best document to recommend. In this case, among Document 5, 19, 3 and 20, the document with the highest pagerank score was Document 20, which is the incorrect recommendation.

In addition, the weighted case shows an extremely confident answer in its recommendation. The pagerank score of Document 5 far exceeds that of any other document in the list. This shows that a weighted case does help with providing more menaingful recommendations.

### Test 2: How do 'Class' nodes help with the document recommendation?
### Result: 'Class' nodes improve the ranking of the documents, by forming seemingly unexpected connections between documents, hence forming a more robust 'for-you page' (similar to that of social media platforms)

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/63017060-da31-40c1-a908-7973b79328d8)

**CASE 3 & CASE 4:**
- Documents which have more 'locations' entities:
  - Documents 3, 14, 7, 2, 4, 1
- User '127.0.0.1' (likes mainly 'locations'):
  - [cmpb 2, science park 3, rochor river 4, macritchie reservoir 5, changi 6, rochor 2, depot road 1, tekong 3, plab 5, jurong 2]

**CASE 3:** Documents = 20, Weighted, Classes
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/a5c2f2c2-d79d-44f6-9a0d-ead92aa444e6)

**ORDER:**

**SAME:** 3, 19 **Different:** 6, 9, 4, 13, 1, 14, 2, 16, 7, 11, 18, 20, 10, 8, 12, 17, 15, 5

**CASE 4:** Documents = 20, Weighted, No Classes
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/8a623480-e027-4fe9-a00d-f3513993f544)

**ORDER:**

**Same:** 3, 19 **Different:** 13, 6, 9, 4, 14, 10, 2, 12, 16, 18, 1, 20, 11. **Zeros:** 15, 17, 5, 7, 8

### Analysis

As can be seen, there is indeed a difference in the ranking of the pageranks, this will matter when we select the top N documents to show to the user. 

'Class' nodes help to recommend documents which might not necessarily have the overlapping entities with the user, but are still possibly of interest to the user as they are connected by similar classes. For example, document A may have [helicopter, tank, fighter jet] as its entities which are connected to the 'Class' node 'Military Vehicles', and document B may have overlapping entities with the user such as [transport plane, tonner, ambulance]. Because these entities are also connected to 'Military Vehicles', although the user may not have necessarily searched for 'helicopter', 'tank' or 'fighter jet', Document A can still be recommended to the user, albeit lower in ranking than Document B. 

In the case where there are no 'Class' nodes, potential documents such as Document 7 can be totally excluded in the top N documents to recommend as the pagerank score for such documents can even be 0, which is undesirable.

### Test 3: How about incorporating both weighted links and 'Class' nodes? Do they together improve the recommendation?
### Result: Yes. They help with the correctness and robustness of the recommendation(s)

**CASE 5 & CASE 6:**
- User '127.0.0.1':
    - Likes document 15 alot: [authentication 10, paces 10, maju camp 10, sysops 10]
    - Likes as many entities in document 5 as in document 15, but the weights are different: [flavian 1, rochor 1, dump truck 1, himars 1]
    - Likes as many entities in document 12 as in document 15, but the weights are different: [osc 1, s-net 1, fbt 1 time, gdn 1 time]
    - Likes as many entities in document 8 as in document 15, but the weights are different: [myoasis 1, orchard road 1, west coast pier 1 time, counter 1]
    - Likes as many entities in document 11 as in document 15, but the weights are different: [emart 1, emergency 1, keylogger 1, gombak 1]
    - Likes document 13 decently: [hfo 2 times, msm 2 times]
    - Likes document 2 decently: [spyware 2 times, sentosa 2 times]
    - Likes document 3 minimally: [singtel 1 time]

**CASE 5:** Documents = 20, Weighted, Classes (Base Case)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/428a9e2c-2cf9-4d26-ae75-469ac6a0e768)

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/57844f35-fcf3-4d22-83f6-faf4b4833b8b)

**Best Recommendation:** Document 15 (Correct)

**Order of recommendation:** 15, 13, 8, 17, 11, 12, 6, 20, 5, 19, 2, 16, 18, 4, 7, 1, 14, 10, 3, 9

**CASE 6:** Documents = 20, All weights = 100, No Classes
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/b39611e8-74b7-4073-9725-f48ee47d71a7)

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/63feba9e-9f36-456e-ba2e-8a2e482e0295)

**Best Recommendation:** Document 8 (Wrong)

**Order of recommendation:** 8, 12, 15, 11, 5, 20, 13, 2, 3, 6, 10, 7, 16, 17. **Zeros:** 1, 14, 18, 19, 4, 9 

### Analysis

**Correctness:** It can be seen that Case 5 (weighted, classes) is more correct as its best recommendation was correct. 

**Order of recommendation:** The top recommendations in Case 6 (unweighted, no classes) is isolated only to the documents which have entities that the user explicitly searched for. On the other hand, the top recommendations in Case 5 (weighted, classes) are more varied, though most of them are documents with entities that the user explicitly searched for. For example, it recommended document 17 as the 4th best recommendation. Document 17 does not share any common entities with what the user searched for. However, because it has entities that are connected to classes (eg. Category 6, Locations, etc) common to documents 15, 13 etc, it is ranked higher as it is deemed as more "similar" to the top documents. 

### Conclusion of Document Recommendation

In conclusion, weighted connections and the inclusion of generic class nodes do help with the recommendation of documents in 2 ways. FIrstly, weighted connections help with the correctness of the recommendation. Secondly, class nodes help with the robustness of the recommendation.

# Testing and Results for User Recommendations 

### Test 1: How does the weight of the links affect which user is recommended to the target user?
### Result: Weighted gives the most accurate answer.

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/4dc93b83-bdc6-43cf-947e-2707f81a3f94)

- User '127.0.0.1' likes 'Locations' alot: [Simpang 10 times, tengah air base 10 times, depot road 10 times]
- User '10.0.0.1' also likes 'Locations' alot: [jurong 10 times, dieppe barracks 10 times, depot road camp 10 times]
- User '11.0.0.1' likes same things as '10.0.0.1' but less strongly: [jurong 1 times, dieppe barracks 1 times, depot road camp 1 times]
- User '12.0.0.1' also likes 'Locations', but only decently: [novena 5 times, serangoon 5 times, jurong 5 times]
- User '13.0.0.1' also likes 'Locations', but only decently: [serangoon 1 time, thomson medical centre 1 time, seletar 1 time]
- User '14.0.0.1' also likes 'Locations', but only minimally, and also likes Category 2: [seletar 1 time, dorset 3 times, csr 3 times]
- User '15.0.0.1' likes something else completey (Category 2): [comms 5 times, cyber 5 times, eacmt 5 times]

**CASE 1:** Number of documents = 10, Users = 7, Classes, Weighted
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/11805193-79e5-45aa-848f-fdd9d9e1e426)

Recommended user to '127.0.0.1': '10.0.0.1' (Correct)

**CASE 2:** Number of documents = 10, Users = 7, Classes, Unweighted (Weight = 0)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/b1943607-89e8-4dd2-9f63-91886f2b096c)

Recommended user to '127.0.0.1': '12.0.0.1' (Incorrect)

**CASE 3:** Number of documents = 10, Users = 7, Classes, Same weight (Weight = 100)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/dd392227-c690-4c20-a895-9a3a388a17ac)

Recommended user to '127.0.0.1': '11.0.0.1' (Incorrect)

### Analysis 
Only the weighted case gave the right expected answer. 

### Test 2: How does the inclusion of "Class" nodes affect which user gets recommended to the target user?
### Result: Without class nodes, the recommended user is consistently wrong.

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/1004ecb9-6383-45f5-ae0e-d0a3176cc6d2)

- User '127.0.0.1' likes 'Locations' alot: [pasir laba camp 10 times, dieppe barracks 10 times, upper seletar reservoir 10 times]
- User '10.0.0.1' also likes 'Locations' alot: [pioneer road 10 times, selarang ring road 10 times, pulau ubin 10 times]
- User '11.0.0.1' likes same things as '10.0.0.1' but less strongly: [pioneer road 1 times, selarang ring road 1 times, pulau ubin 1 times]
- User '12.0.0.1' also likes 'Locations', but only decently: [seletar 5 times, sembawang 5 times]
- User '13.0.0.1' also likes 'Locations', but only decently: [mandai 1 time, jurong east 1 time, ladang camp 1 time]
- User '14.0.0.1' also likes 'Locations', but only minimally, and also likes Category 2: [seletar 1 time, dsta 3 times, drone 3 times]
- User '15.0.0.1' likes something else completey (Category 2): [drone 5 times, cyber 5 times, cyber-attack 5 times]

**CASE 4:** Number of documents = 10, Users = 7, Weighted, Classes

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/08647663-5356-4e3f-9d41-9c9572be0126)

Best user recommended: 10.0.0.1 (correct), though not very consistent

**CASE 5:** Number of documents = 10, Users = 7, Weighted, No Classes

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/5d465878-e2e7-4a55-a6e4-08d69049440e)

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/85a07d92-31b9-4233-aa04-5ed88cbb389d)

Best user recommended: 14.0.0.1 (consistently wrong)

### Analysis 

The user recommended to 127.0.0.1 is correct in Case 4, but it is not consistently the case. The reason is that the node embeddings change with time as the weights change (because the recency changes). However, this is still a better case than Case 5, where the user recommended is consistly wrong. 

### Size of graph

**CASE 6:** Number of documents = 10, Users = 5, Weighted, Classes
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/c61b4d25-a685-4836-ab0a-99cbd611d7c4)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/2bc66953-2b21-4e32-baa7-32c78cf84fee)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/581f6930-2c49-4a61-9781-fea3dce9ad1b)

**CASE 7:** Number of documents = 100, Users = 5, Weighted, Classes

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/578ddc2f-adb6-419f-8571-7cd211856cba)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/74441f6e-af47-42d7-828e-b26bbe1b6e06)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/74a90207-57c8-42a9-bbb1-81d78bed8038)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/fdb084cb-81f9-4441-96f1-592a84e89b2a)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/d0ecea8e-32d6-47da-a821-369fe2867082)

### Analysis 
- In both cases (5 documents vs 100 documents), the user recommendation is correct (11.0.0.1).
- However, the durations to project the graph, to assign the graph embeddings and to ultimately recommend a user were all longer in the case where there was 100 documents vs 5 documents.
