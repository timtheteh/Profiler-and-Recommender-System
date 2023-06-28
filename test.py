import fasttext

file_path = "/home/grace/grace/vicuna/FastChat/profiler/model.bin"
sentence2vecModel = fasttext.load_model(file_path)

phrase = "dog park"
# tokens = fasttext.tokenize(phrase)

# Get the vector representation of the phrase
vector = sentence2vecModel.get_sentence_vector(phrase)

# Print the vector representation of the phrase
print(vector)

similarity = sentence2vecModel.get_similarity(phrase, "cat park")

print("similarity is: ", similarity)