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

# Evaluation of Results

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

### Conclusion:
In the experiments above, the presence of classes don't affect the result of the document recommended to the user. 

However, it affects the pagerank scores. Classes do increase the confidence of the document that is recommended to the user, as the score is higher in the case where there are classes vs the case where there aren't. This might be more crucial when the graph becomes more convoluted, when the user likes more entities that are in common with other documents and so on.

This is also evident where we compare weighted vs same weights. In the experiments above, the presence of weighted links did not necessarily change the outcome of the recommended document. 

However, it did result in slightly different pagerank scores. Weighted relationships do increase the confidence of the document that is recommended to the user. Again, the significance of this difference might only be more apparent when the graph becomes more convoluted. 

### Real Life Case

1. Number of documents = 100; Classes; Weighted; More connections


2. Number of documents = 100; No Classes; All same weight; More connections

