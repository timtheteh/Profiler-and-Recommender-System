# Profiler and Recommender System

### What is the goal of this project?

1. To find a way to profile users based on their search inputs.
2. To find a way to improve the personalised pagerank algorithm results in Neo4j

### Purpose of profiler and recommender system

The purpose is to generate robust and personalised recommendations to users by:

1. Recommending existing documents to users
2. Recommending similar profiles to users
3. Recommending new documents to relevant users only

### Introduction of Graph Database

- Entities: words of phrases that are present in user searches / documents
- Users: they are identified by their ip address in this demo
- Documents: they can represent mindef articles
- Classes: generic nodes which link entities together (for eg. 'Locations' <- choa chu kang, seletar, etc)

### Results

1. Weighed links -> Correctness of recommendation for both recommendation of document and user.
2. Class nodes -> More robust ranking of recommendations for documents, as well as correctness of recommendation for user

Other features:
- Application is flexible to spelling mistakes (for eg. a user mispells 'apple' as 'aple' and assuming 'apple' already exists in the graph database. 'aple' will first be compared to 'apple' via semantic comparison of their respective vectors. If the comparison score is higher than a certain threshold, it will be assumed that the user meant 'apple' instead of 'apel', and a connection between the user and the existing 'apple' node will be formed. Otherwise, a new node 'apel' will be formed.
- Each entity is added to at least one 'class' node.

### Limitations

1. The main limitation of this application so far is that the extraction of entities is done with the help of LLMs (vicuna-7b). LLMs help with more robust entity extractions, but the entities extracted may be unpredictable at times.
2. The way in which the 'HAS' relationship between documents and their intrinsic entities is also unknown at this point. In addition, the way in which the 'IS_SIMILAR_TO' relationship between document entities and the class nodes is also unknown at this point.
3. When the graph becomes larger and larger, the time complexity of this application increases. This is mainly because in order to run the personalised pagerank and node embedding algorithms, a projection of the graph database needs to be done which takes longer as the size of the graph increases. Furthermore, as the size increases, the time complexity of the pagerank and node embeddings increase.
    - This can be circumvented by implementing a periodic pruning of the graph, which will prune users, entities, documents and all the respective relationships after a set period of time (see massPrune.py)
4. Accuracy of which user is recommended to the target user needs more investigation as the answer is not consistent all the time (need to test other parameters in the algorithm, for example randomSeed, embeddingDimension, etc)
   - Maybe can use pagerank instead of node embeddings to recommend users?
  
### Future work

1. Documents: they can represent anything you want to recommend to the user (articles, web links, etc)
2. Links between documents and their entities: these entities may not need to be extracted based on its contents, it can be likes hashtags (descriptions) that users can choose for the document before adding them into the database
3. Right now we are recommending based on user inputs. But in the future, we can also tailor the recommendation based on user feedback of the recommendations. Hence in the future, we can log metrics of user feedback of LLM answers and recommendations and use these feedback to tailor the recommendation further.

### Methodology

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
- Files: loggingToES.py, addingToProfile.py, massUpdateLikesWeights.py, massPrune.py
- **loggingToES**:
  - User's search inputs are logged into Elastic Search (batch queries)
  - These logs contain information about who is the user, what did they search for, the datetime of their query, just to name a few
- **addingToProfile:**
  - Elastic Search is then queried to only retrieve the new queries that have been added.
  - For each query, a 'User' node is created only if the user is a new user.
  - Based on these new queries, the entities are extracted with the help of a LLM (we used vicuna-7b) as well as text matching with a whitelist.
  - Each entity and its links to the user and 'Class' nodes are then created based on a few test cases. 
  - Some checks include:
    - Does this entity already exist?
    - Is this entity aready similar to any existing node in the graph database? And is there already a relationship between the user and this entity?
    - If this is a new node, make sure to connect to at least one 'Class' node. This can be done so by the predefined 'Class' nodes or via cosine similarity (semantic comparisons)
    - Entities: datetimeadded, vector, name
    - 'LIKES' Relationship: freq, rec, weight
    - 'IS_SIMILAR_TO' Relationship: weight
  - At the end of each addition to the graph, each link's recency and weight properties in the graph is again updated.
- **massUpdateLikesWeights.py**
    - whenever this function is called, the weights of each "LIKES" relationship is updated
    - mainly, the frequency and recency properties of each "LIKES" relationship is updated, and consequently the weight of each "LIKES" relationship is updated     
    - beyond a certain shelf-life, the frequency of a "LIKES" relationship will be set to zero -> and hence the weight will be set to zero
- **massPrune.py**
    - this function looks through the whole graph and deletes entities, users, documents and all their respective links if the shelf-life of these nodes and links are exceeded
    - The purpose of this function is to keep the size of the graph as small as needed. 

**Step 3: Recommendation**
- File: recommendation.py
- A projection of the graph database is created. Nodes with no outgoing links are excluded to avoid unncessary 'sinks' in the personalised pagerank algorithm.
- **Document Recommendation**
  - For a personalised recommendation, source nodes are needed to bias the pagerank algorithm
  - These source nodes are the top k (eg. 5) entities which have the strongest links (based on weights) between the user. These top k entities represent the entities which the user is most interested in, and hence the pagerank algorithm will be biased based on these nodes (random jump to these source nodes with probability = 1 - damping_factor)
  - The inbuilt personalised pagerank algoritm in Neo4j is then run based on these source nodes as bias. (https://neo4j.com/docs/graph-data-science/current/algorithms/page-rank/)
  - Nodes with 'Document' label will be filtered and the top N documents will be recommended to the user.
- **User Recommendation**
  - For now, each node in the graph will have a node embedding calculated for it using the inbuilt node2vec algorithm in Neo4j. (https://neo4j.com/docs/graph-data-science/current/machine-learning/node-embeddings/node2vec/)
  - Nodes with 'User' label apart from the user in question will be recommended as the most similar users to be recommended (similar interests).
- **Choosing which user to recommend a document to**
  - Source nodes: entities of documents
  - Run pagerank to get pagerank score of each node
  - The 'User' node with the highest pagerank score is chosen.

# Testing and Results for Document Recommendations

## Test 1: Do weights improve the document recommendation?
### Result: Yes, weighted links improve the correctness of the recommendation by forming a basis for the source nodes in personalised pagerank.

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

## Analysis

The weighted case (Case 1) shows the correct document (Document 5) as the document to be recommended, which reaffirms that weighted links do help with the personalised recommendation.

In the unweighted case (Case 2) where the weights of each relationship is set the same at 100, the document it recommended is Document 20. The reason for this wrong recommendation is because in an unweighted case, the source nodes have little bias to the user as they are chosen at random (since all links are equal), leaving almost equal probability to pick any of the 4 documents (which have the most outgoing links from the pov of the user) as the best document to recommend. In this case, among Document 5, 19, 3 and 20, the document with the highest pagerank score was Document 20, which is the incorrect recommendation.

In addition, the weighted case shows an extremely confident answer in its recommendation. The pagerank score of Document 5 far exceeds that of any other document in the list. This shows that a weighted case does help with providing more menaingful recommendations.

## Test 2: How do 'Class' nodes help with the document recommendation?
### Result: 'Class' nodes improve the ranking of the documents, by forming seemingly unexpected connections between documents, hence forming a more robust 'for-you page' (similar to that of social media platforms)

**CASE 3 & CASE 4:**
- Documents which have more 'locations' entities:
  - Documents 3, 14, 7, 2, 4, 1
- User '127.0.0.1' (likes mainly 'locations'):
  - [cmpb 2, science park 3, rochor river 4, macritchie reservoir 5, changi 6, rochor 2, depot road 1, tekong 3, plab 5, jurong 2] did not search for document 7

**CASE 3:** Documents = 10, Weighted, Classes
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/a7316186-754e-4f1d-8ebe-696625452881)

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/7928fa62-8b31-498d-b9c7-f39f81b6e5fe)

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/d3145393-5b55-4296-ab2f-503eca72e8d5)

**ORDER:**

**Same:** 3, 19 **Different:** 6, 9, 4, 13, 1, 14, 2, 16, 7, 11, 18, 20, 10, 8, 12, 17, 15, 5

**CASE 4:** Documents = 10, Weighted, No Classes
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/f1346d95-d153-44e1-bb9a-b24d1909bfb9)

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/498d032a-7578-4a4d-aace-2578e39ec865)

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/8f38dd9e-3e5a-4079-a684-8ff71c0c3a42)

**ORDER:**

**Same:** 3, 19 **Different:** 13, 6, 9, 4, 14, 10, 2, 12, 16, 18, 1, 20, 11. **Zeros:** 15, 17, 5, 7, 8

## Analysis

As can be seen, there is indeed a difference in the ranking of the pageranks, this will matter when we select the top N documents to show to the user. 

'Class' nodes help to recommend documents which might not necessarily have the overlapping entities with the user, but are still possibly of interest to the user as they are connected by similar classes. For example, document A may have [helicopter, tank, fighter jet] as its entities which are connected to the 'Class' node 'Military Vehicles', and document B may have overlapping entities with the user such as [transport plane, tonner, ambulance]. Because these entities are also connected to 'Military Vehicles', although the user may not have necessarily searched for 'helicopter', 'tank' or 'fighter jet', Document A can still be recommended to the user, albeit lower in ranking than Document B. 

In the case where there are no 'Class' nodes, potential documents such as Document 7 can be totally excluded in the top N documents to recommend as the pagerank score for such documents can even be 0, which is undesirable.

## Test 3: How about incorporating both weighted links and 'Class' nodes? Do they together improve the recommendation?
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

## Analysis

**Correctness:** It can be seen that Case 5 (weighted, classes) is more correct as its best recommendation was correct. 

**Order of recommendation:** The top recommendations in Case 6 (unweighted, no classes) is isolated only to the documents which have entities that the user explicitly searched for. On the other hand, the top recommendations in Case 5 (weighted, classes) are more varied, though most of them are documents with entities that the user explicitly searched for. For example, it recommended document 17 as the 4th best recommendation. Document 17 does not share any common entities with what the user searched for. However, because it has entities that are connected to classes (eg. Category 6, Locations, etc) common to documents 15, 13 etc, it is ranked higher as it is deemed as more "similar" to the top documents. 

## Conclusion for Document Recommendation

In conclusion, weighted connections and the inclusion of generic class nodes do help with the recommendation of documents in 2 ways. FIrstly, weighted connections help with the correctness of the recommendation. Secondly, class nodes help with the robustness of the recommendation.

# Testing and Results for User Recommendations 

## Test 1: How does the weight of the links affect which user is recommended to the target user?
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

## Analysis 
Only the weighted case gave the right expected answer. 

## Test 2: How does the inclusion of "Class" nodes affect which user gets recommended to the target user?
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

## Analysis 

The user recommended to 127.0.0.1 is correct in Case 4, but it is not consistently the case. The reason is that the node embeddings change with time as the weights change (because the recency changes). However, this is still a better case than Case 5, where the user recommended is consistently wrong. 

# Testing how does the size of the graph affect the recommendation of documents and users.

## Result: It does not affect the accuracy of the recommendation, but it does increase the time complexity.

**CASE 6:** Number of documents = 10, Users = 5, Weighted, Classes

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/2956750b-0fdb-4fc2-b0cc-d01e7751a81c)

- User '127.0.0.1' likes 'Locations' and 'Document 2' alot: [jurong 5 times, tekong 5 times, tekong island 5 times, jurong camp 5 times]
- User '10.0.0.1' also likes 'Locations' alot: [ecp 5 times, changi bay 5 times, bukit timah 5 times, orchard 5 times]
- User '11.0.0.1' likes same things as '10.0.0.1' but less strongly: [ecp 1 time, changi bay 1 time, bukit timah 1 time, orchard 1 time]
- User '12.0.0.1' also likes 'Locations', but only decently: [changi 3 times, kallang 3 times]
- User '13.0.0.1' also likes 'Locations', but only decently: [changi 1 time, kallang 1 time, ecp 1 time]

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/207b7d50-7651-4814-85c1-d26b25a85265)

**Recommended document:** Document 2 (Correct)

**Recommended user:** User 10.0.0.1 (quite consistently correct)

**Time to project graph:** 24ms

**Time to recommend document:** 12ms

**Time to assign node embeddings:** 167ms

**Time to recommend another user:** 3ms

**CASE 7:** Number of documents = 100, Users = 5, Weighted, Classes

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/b1f7fc7d-869e-4d53-b452-9817fc281f28)

- User '127.0.0.1' likes 'Locations' and 'Document 22' alot: [clementi 5 times, keat hong camp 5 times, cmpb 5 times, orchard 5 times]
- User '10.0.0.1' also likes 'Locations' alot: [orchard 5 times, orchard road 5 times, gleneagles 5 times, jurong island 5 times]
- User '11.0.0.1' likes same things as '10.0.0.1' but less strongly: [orchard 1 time, orchard road 1 time, gleneagles 1 time, jurong island 1 time]
- User '12.0.0.1' also likes 'Locations', but only decently: [tekong island 3 times, geylang 3 times]
- User '13.0.0.1' also likes 'Locations', but only decently: [tuas 1 time, ecp 1 time, gombak 1 time]

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/dcad1cd4-8aa0-411d-bd0e-4618297470d5)

**Recommended document:** Document 22 (Correct)

**Recommended user:** User 10.0.0.1 (quite consistently correct)

**Time to project graph:** 40ms

**Time to recommend document:** 35ms

**Time to assign node embeddings:** 1102ms

**Time to recommend another user:** 5ms

## Analysis 
- In both cases (10 documents vs 100 documents), the document recommendation (document 2 in case 6, document 22 in case 7) and the user recommendation are correct (10.0.0.1).
- However, the time complexity in Case 7 is significantly longer, especially when the nodes are assigned the embedding vectors.
- Hence, to avoid long runtimes, the graph database should be pruned periodically.

# Bonus Feature: Choosing which user to recommend a document to

Reusing the same test case above (test case 7):

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/0e7ff58c-5d37-46ff-9b43-21035a80e826)

The correct user is chosen to recommend document 22 to: 127.0.0.1.
