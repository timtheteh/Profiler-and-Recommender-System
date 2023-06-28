import fasttext

path_to_model = "/home/grace/Downloads/wiki.en/wiki.en.bin"
model = fasttext.load_model(path_to_model)
model.save_model("/home/grace/grace/vicuna/FastChat/profiler/model.bin")