# Profiler and Recommender System

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
  - For now, each node in the graph will have a node embedding calculated for it using the inbuilt fastRP algorithm in Neo4j.
  - Nodes with 'User' label apart from the user in question will be recommended as the most similar users to be recommended (similar interests).

# Initial Experiments

### Weighted vs Unweighted vs All same weight
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/c61b4d25-a685-4836-ab0a-99cbd611d7c4)

1. Weighted case
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/2bc66953-2b21-4e32-baa7-32c78cf84fee)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/581f6930-2c49-4a61-9781-fea3dce9ad1b)

2. Unweighted case (weight = 0)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/8f92be35-0474-4bde-92dd-ae201045fce6)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/131a6adc-9ad8-42da-bc2a-1ad8e67b47f0)

No documents are recommended as the pagerank scores for each document node is 0.0.

No users are recommended because the embeddings of each other user node is 0.0.

3. Same weight (weight = 1)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/bddf5ce6-5137-44b3-a136-61a56dd47863)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/82c4e2a9-ac1c-4ff2-bf15-9f4c5bcfada2)

Although the document recommended is the same as the weighted case, its pagerank score is lower.

### Classes vs No Classes
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/db4d360a-0c30-4ce4-a851-da7e1c141403)

1. No Classes (Weighted)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/b318c777-0abc-4740-a55e-74a5e3492a92)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/00495747-3cff-41fb-adea-4043ee39c7ec)

2. No Classes (Weight = 1)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/2971492d-c0e9-46e7-bebc-be5cd28c34bd)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/4a1bffca-ec99-43ea-ab1b-533b9a9570b7)

### Size of graph

1. Number of documents = 100; Classes; Weighted

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/578ddc2f-adb6-419f-8571-7cd211856cba)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/74441f6e-af47-42d7-828e-b26bbe1b6e06)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/74a90207-57c8-42a9-bbb1-81d78bed8038)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/fdb084cb-81f9-4441-96f1-592a84e89b2a)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/d0ecea8e-32d6-47da-a821-369fe2867082)

2. Number of documents = 100; No Classes; Weighted

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/06e81502-64f7-4772-b48e-898b24d67056)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/ff3a7737-35dd-45e9-b850-1c0c9d1cc0d7)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/67aacd1d-2eac-480e-86f8-f06e1585954a)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/86af40b9-47d4-42ea-8e7c-270372a0f5a8)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/898d247e-22bd-4a72-946d-a8f63b5b4bdb)

3. Number of document = 100; Classes; Weight = 1

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/40e0f259-1f5a-4dc6-bd32-28f11246b661)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/97dd3d51-d060-41c1-b6c0-18d32405903e)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/0f911f51-037c-4883-892a-17ff67a6e654)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/bff59b03-bcb0-40e9-bae6-fb9f3ebd4a44)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/587760d2-d51f-452d-ac5c-ebf51c1162e0)

4. Number of document = 100; No Classes; Weight = 1

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/af490b70-685e-49e8-a010-f7ef85e1c4e8)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/b7d5b758-211a-41e6-b56b-a930428d39f4)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/701a0f5c-8fd5-4625-9282-49171f1301ef)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/064ca22d-2ce9-42f0-af42-98c6c39f843e)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/6b86847c-dc7f-4a4e-90bc-bbef6f46e5d1)

### Analysis so far:
In the experiments above, the presence of classes don't affect the result of the document recommended to the user. 

However, it affects the pagerank scores. Classes do increase the confidence of the document that is recommended to the user, as the score is higher in the case where there are classes vs the case where there aren't. This might be more crucial when the graph becomes more convoluted, when the user likes more entities that are in common with other documents and so on.

This is also evident where we compare weighted vs same weights. In the experiments above, the presence of weighted links did not necessarily change the outcome of the recommended document. 

However, it did result in slightly different pagerank scores. Weighted relationships do increase the confidence of the document that is recommended to the user. Again, the significance of this difference might only be more apparent when the graph becomes more convoluted. 

One reason why the pagerank recommendations remain the same whether weighted or not and whether there are classes or not is that the weights in the weighted case are all very much similar (in the 0.6 to 0.7 range) which makes the graph very similar to an unweighted case already.

# Real Life Case

1. Number of documents = 100; Classes; Weighted; More connections

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/28b20e52-3164-495c-8215-105134e20262)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/d0c32b3c-d3d2-4cf7-b3de-d817f619f967)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/52b975a2-9916-4cc2-90c8-9babdfa5a65f)

2. Number of documents = 100; No Classes; All same weight; More connections

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/c46154e6-787a-41fe-adf1-6fe122783f4b)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/473082bf-2963-4579-b184-db949ab40f2e)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/3be5d3e4-f5fe-4c54-8bd2-cbb9db79b6a4)

# Better experiment Part 1 (Testing of Weights)

- Make the user's preference for a certain document to be very obvious than the rest
- But still remain that he likes random entities from random documents
- The goal is to make the links between the user and the entities of a document very skewed (eg. 0.9) while the rest are low (eg. 0.2)
- Change the probability_rate constant from 0.5 to 0.9
- Change the default weight of the IS_SIMILAR_TO and HAS relationships from 0.7 to a range (eg. 0.3 - 0.9)
- Use smaller number of documents for easier analysis
- Compare this case to the case where all relationships are 1 and there are no classes.

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

1. Documents = 20, Weighted, Classes (Base Case)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/bc55e348-a5e1-4982-a10c-3dae65ee74e6)

2. Documents = 20, All weights = 100, Classes
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/524554a1-b213-4fde-a891-e3edc16dd59b)

### Analysis

Here, we choose the top 5 interest nodes as the source nodes (based on the weight of the LIKES relationships) as the basis for the personalised pagerank. The recommendation when it is weighted is hence more meaningful than when all the weights are equal.

# Better experiment Part 2 (Testing of Classes)

Purpose of classes: to form more possible connections to documents that can be recommended (the ranking of documents is more meaningful)

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/63017060-da31-40c1-a908-7973b79328d8)

**CASE 3 & CASE 4:**
- Documents which have more 'locations' entities:
  - document 3, 14, 7, 2, 4, 1
- User '127.0.0.1' (likes mainly 'locations'): [cmpb 2, science park 3, rochor river 4, macritchie reservoir 5, changi 6, rochor 2, depot road 1, tekong 3, plab 5, jurong 2]

3. Documents = 20, Weighted, Classes
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/a5c2f2c2-d79d-44f6-9a0d-ead92aa444e6)

**ORDER:**
**SAME:** 3, 19 **Different:** 6, 9, 4, 13, 1, 14, 2, 16, 7, 11, 18, 20, 10, 8, 12, 17, 15, 5

4. Documents = 20, Weighted, No Classes
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/8a623480-e027-4fe9-a00d-f3513993f544)

**ORDER:**
**Same:** 3, 19 **Different:** 13, 6, 9, 4, 14, 10, 2, 12, 16, 18, 1, 20, 11. Zeros: 15, 17, 5, 7, 8

### Analysis

As can be seen, there is indeed a difference in the ranking of the pageranks, this will matter when we select the top k documents to show to the user. The classes help to ensure that the the order of the documents is more meaningful.

# Better experiment Part 3 (Testing of both classes and weights combined)

**CASE 5 & CASE 6:**

5. Documents = 20, Weighted, Classes (Base Case)

6. Documents = 20, All weights = 1, No Classes
