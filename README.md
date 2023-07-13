# Profiler and Recommender System

Goal: To recommend 'Documents' to 'Users'

Solution: Enhance the graph by
1. Enhancing user profiles (by adding user's interested entities into graoh along with a user-entity edge that has a weight calculated based on frequency and recency of query)
2. Enhancing the the graph by adding entity-class relationships which help to improve the personalised pagerank algrithm

Step 1: Populate the graph database

Files: addPredefinedClasses.py, addingDocuments.py
addPredefinedClasses.py:
  - These are predefined class nodes which entities will be linked to
addingDocuments.py:
  - Documents are randomly generated based on a whitelist of keywords
  - These keywords are then extracted
  - Links between the document and the extracted keywords are formed with a default value of 0.7 first
  - Links between the extracted keywords and the predefined classes are also formed.

Step 2: Logging and Adding entities to enhance a user profile

Files: loggingToES.py, addingToProfile.py

Test Case 1
1. A node of the same name as the entity in question (EIQ) already exists
2. There is an existing LIKES relationship between this node and the user
Action: update this relationship's properties (freq, rec, weight) based on logs and update the datetimeadded of the entity

Test Case 2
1. A node of the same name as the entity in question (EIQ) already exists
2. There is NO existing LIKES relationship between this node and the user
Action: form a new LIKES relationship between user and the entity and give its properties (freq, rec, weight) based on logs and update the datetimeadded of the entity

Test Case 3
1. A node of the same name as the entity in question (EIQ) DOES NOT already exist 
Action: create the EIQ first with its corresponding vector embedding and datetimeadded and create link between entity and class via predefined relationships if entity is in the predefined list
2. Find the most similar existing entity node in the graph and its similarity score
3. Similarity score is < threshold_for_similarity (not similar to any existing node)
Action: form a new LIKES relationship between user and EIQ and find the most similar 'Class' node(s) to link it to

Test Case 4
1. A node of the same name as the entity in question (EIQ) DOES NOT already exist 
Action: create the EIQ first with its corresponding vector embedding and datetimeadded
2. Find the most similar existing entity node in the graph and its similarity score
3. Similarity score is > threshold_for_similarity (there is already a node similar to EIQ)
4. A relationship between user and this node already exists
Action: update this relationship's properties (freq, rec, weight) based on logs and delete the EIQ

Test Case 5
1. A node of the same name as the entity in question (EIQ) DOES NOT already exist 
Action: create the EIQ first with its corresponding vector embedding and datetimeadded
2. Find the most similar existing entity node in the graph and its similarity score
3. Similarity score is > threshold_for_similarity (there is already a node similar to EIQ)
4. A relationship between user and this node DOES NOT already exist
Action: form a new LIKES relationship between user and the entity and give its properties (freq, rec, weight) based on logsand delete the EIQ

Test Case 6: Base Case
1. A node of the same name as the entity in question (EIQ) DOES NOT already exist 
Action: create the EIQ first with its corresponding vector embedding and datetimeadded
2. EIQ is the only entity node in graph
Action: form a new LIKES relationship between user and the entity and give its properties (freq, rec, weight) based on logs and link EIQ to the correct classes

Step 3: Recommendation

Files: recommendation.py
  - runs a personalised pagerank algorithm to get the highest ranked document to recommend to user

![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/759613c9-c60b-4305-a605-c8910c3a4300)
Result: For user '127.0.0.1', the document recommended to it is 'Document 2'. For user '10.0.0.1', the document recommended to it is 'Document 3'.
Legend: Blue (entities), Yellow (classes), Pink (Users), Red (Documents)
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/75cf7d7a-e4ef-4b06-b272-1191574c0652)

Control experiment: weights of all relationships are set to 0 
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/23f5f14a-6ffa-4aac-ae06-a99069d98f2e)
Recommendations are less meaningful than the case where the edges are weighted.


# Evaluation of Results
![image](https://github.com/timtheteh/Profiler-and-Recommender-System/assets/76463517/c61b4d25-a685-4836-ab0a-99cbd611d7c4)

### Weighted vs Unweighted vs All same weight

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


