# Profiler-and-Recommender-System

Goal: To recommend 'Documents' to 'Users'

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
