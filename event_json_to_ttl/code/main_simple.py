import csv_ground_truth_to_json as cgtj

if __name__ == '__main__': 

    # Code principal
    data_json_folder = "../data/json/"
    data_folder = "../data/"

    # Transformation du ground truth CSV en JSON puis en TTL
    csv_ground_truth = data_folder + "ground_truth.csv"
    json_ground_truth = data_folder + "simplified_ground_truth.json"
    jsonl_ground_truth = data_folder + "simplified_ground_truth.jsonl"
    
    jsonl_train_set = data_folder + "new_train.jsonl"
    jsonl_valid_set = data_folder + "new_valid.jsonl"
    jsonl_test_set = data_folder + "new_test.jsonl"

    # Définir les proportions (par exemple : 70% train, 10% valid, 20% test)
    files_settings = [
        (jsonl_train_set, 0.7),
        (jsonl_valid_set, 0.1),
        (jsonl_test_set, 0.2)
    ]

    triples_label = "triples"
    sent_label = "sent"
    triples_format = "dict"
    sub_label, prop_label, obj_label = "sub", "rel", "obj"

    df = cgtj.read_csv(csv_ground_truth, separator='\t')
  
    train_set = cgtj.create_simple_train_set(df, sent_label, triples_label, triples_format, sub_label, prop_label, obj_label)
    cgtj.export_train_set_in_json(train_set, json_ground_truth)
    cgtj.export_train_set_in_jsonl(train_set, jsonl_ground_truth)
    cgtj.export_train_set_in_multiple_files(train_set, files_settings)
