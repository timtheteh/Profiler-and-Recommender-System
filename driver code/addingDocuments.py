import os
import string
from fastchat.constants import LOGDIR

whitelist_file_path = "profiler/newEntityList2.txt"
whitelist_filename = os.path.join(LOGDIR, f"{whitelist_file_path}")
punctuationString = string.punctuation
punctuationList=[*punctuationString]

with open(whitelist_filename, 'r') as f:
    whitelist_string = f.read()

whitelist = whitelist_string.split("\n")

list_of_texts = {"text1": "surveillance system hi?",
                 "text2": "hi surveillance system?",
                 "text3": " surveillance system ", 
                 "text4": "nosurveillance system", 
                 "text5": "nosurveillance system ", 
                 "text6": " nosurveillance system", 
                 }

textName_entities = {}

for textName, textContent in list_of_texts.items():
    textName_entities[textName] = []
    for phrase in whitelist:
        if (phrase+" ") in textContent and textContent.find(phrase) == 0:
            textName_entities[textName].append(phrase)
            continue
        elif (phrase+" ") in textContent:
            for punctuation in punctuationList:
                if (punctuation+phrase+" ") in textContent:
                    textName_entities[textName].append(phrase)
                    break
            continue
        elif (" "+phrase) in textContent and textContent.rfind(phrase)+len(phrase)-1 == len(textContent)-1:
            textName_entities[textName].append(phrase)
            continue
        elif (" "+phrase) in textContent:
            for punctuation in punctuationList:
                if (" "+phrase+punctuation) in textContent:
                    textName_entities[textName].append(phrase)
                    break
            continue
        elif (" "+phrase+" ") in textContent:
            textName_entities[textName].append(phrase)
            continue

print(['bye ']+['hi'])
