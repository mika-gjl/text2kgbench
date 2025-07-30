import pandas as pd
import random
import json
import uuid
import description_initialisation as di

def read_csv(file_path, separator=','):
    """
    Reads a CSV file and returns a DataFrame.
    """
    try:
        df = pd.read_csv(file_path, sep=separator, encoding='utf-8')
        return df
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return None

def create_event_descriptions(df:pd.DataFrame, out_path):
    df = df.where(pd.notna(df), None)  # Remplacer tous les NaN par None
    events_dict = {}
    events_landmarks = {}

    for index, row in df.iterrows():
        event_id = row.get('event')
        event_label=row.get('event_label')
        time=row.get('time')
        line_id=row.get('line_id')
        landmark_label=row.get('landmark_label')
        landmark_type=row.get('landmark_type')
        relatum_label=row.get('relatum_label')
        relatum_type=row.get('relatum_type')
        relation_type=row.get('relation_type')
        change_on = row.get('change_on')
        change_type = row.get('change_type')
        attribute_type = row.get('attribute_type')
        outdates = row.get('outdates')
        makes_effective = row.get('makes_effective')

        event_desc = events_dict.get(event_id, None)
        ev_landmarks = events_landmarks.get(event_id, {})

        if event_desc is None:
            events_landmarks[event_id] = {}
            prov_desc = {"uri": f"https://opendata.paris.fr/explore/dataset/denominations-emprises-voies-actuelles/{line_id}"}
            event_desc = {"id": event_id, "landmarks": [], "relations": [], "provenance": prov_desc, "lang":"fr"}
            if event_label is not None:
                event_desc["label"] = event_label
        
        if event_desc.get('time') is None and time is not None:
          time_description = create_time_description(time)
          event_desc["time"] = time_description

        if change_on == "attribute":
          cg_desc = create_attribute_change_description(attribute_type, makes_effective, outdates, lang="fr")
        elif change_on == "landmark":
          cg_desc = di.create_landmark_change_event_description(change_type)
        elif change_on == "relation":
          cg_desc = di.create_landmark_relation_change_event_description(change_type)
        landmark_labels = landmark_label.split(";")
        landmark_types = landmark_type.split(";")

        for i in range(len(landmark_labels)):
            label = landmark_labels[i].strip()
            ltype = landmark_types[i].strip()
            
            if label not in ev_landmarks:
                lm_id = str(uuid.uuid4())
                lm_desc = di.create_landmark_event_description(lm_id, ltype, label, "fr", changes=[])
                ev_landmarks[label] = lm_id
                event_desc["landmarks"].append(lm_desc)
            else:
                lm_id = ev_landmarks[label]

            if change_on in ["landmark", "attribute"]:
                for lm in event_desc["landmarks"]:
                    if lm["id"] == lm_id:
                        if "changes" not in lm:
                            lm["changes"] = []
                        if cg_desc not in lm["changes"]:
                            lm["changes"].append(cg_desc)
                        break

  
        if change_on in ["landmark", "attribute"]:
          for lm in event_desc["landmarks"]:
              if lm["id"] == lm_id:
                  if "changes" not in lm:
                      lm["changes"] = []
                  if cg_desc not in lm["changes"]:
                      lm["changes"].append(cg_desc)
                  break
              
        if relatum_label is not None and relatum_label not in ev_landmarks.keys():
            relatum_labels = relatum_label.split(";")
            relatum_types = relatum_type.split(";")
            relatum_ids = [str(uuid.uuid4()) for x in relatum_labels]
            relatum_descs = []
            for i in range(len(relatum_ids)):
                rel_desc = di.create_landmark_event_description(relatum_ids[i], relatum_types[i], relatum_labels[i], "fr", changes=[])
                relatum_descs.append(rel_desc)
                ev_landmarks[relatum_labels[i]] = relatum_ids[i]

            event_desc["landmarks"] += relatum_descs
            lr_id = str(uuid.uuid4())
            lr_desc = di.create_landmark_relation_description(lr_id, relation_type, lm_id, relatum_ids)
            event_desc["relations"].append(lr_desc)
            if change_on == "relation":
                lr_desc["changes"] = [cg_desc]

        events_dict[event_id] = event_desc
        events_landmarks[event_id] = ev_landmarks

    events = {"events": list(events_dict.values())}
    json.dump(events, open(out_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        
def create_time_description(time_stamp:str):
    if time_stamp is None:
        return None
    if len(time_stamp) == 4:
        precision = "year"
    elif len(time_stamp) == 7:
        precision = "month"
    elif len(time_stamp) == 10:
        precision = "day"
    else:
        precision = "day"
    return {"stamp":time_stamp, "calendar":"gregorian", "precision":precision}

def create_attribute_change_description(attribute_type, makes_effective=None, outdates=None, lang="fr"):
    """
    Create a landmark attribute change event description.
    """
    
    if makes_effective is not None:
        makes_effective = [di.create_landmark_attribute_version_description(makes_effective, lang="fr")]
    else:
        makes_effective = None
    if outdates is not None:
      outdates = [di.create_landmark_attribute_version_description(outdates, lang="fr")]
    else:
      outdates = None

    desc = di.create_landmark_attribute_change_event_description(
        attribute_type,
        makes_effective=makes_effective,
        outdates=outdates,
    )

    return desc

def get_triple(
        sub, prop, obj,
        format="list",
        sub_label="sub", prop_label="prop", obj_label="obj"):
    
    if format == "list":
        return [sub, prop, obj]

    if format == "dict":
        return {sub_label:sub, prop_label:prop, obj_label:obj}

def create_simple_train_set_line(
        row, triples_format="list",
        sub_label="sub", prop_label="prop", obj_label="obj"):
    
    triples = []
    change = []

    change_type = row['change_type']
    change_on = row['change_on']
    attribute_type = row['attribute_type']
    time = row["time"] if pd.notnull(row["time"]) else "noTime"
    line_id = row["line_id"]
    event_label = row["event_label"]

    landmark = get_triple(row['landmark_label'], "isLandmarkType", row['landmark_type'], triples_format, sub_label, prop_label, obj_label)
    triples.append(landmark)

    if pd.notnull(row["relatum_label"]):
        relation = get_triple(row["landmark_label"], row["relation_type"], row["relatum_label"], triples_format, sub_label, prop_label, obj_label)
        relatum = get_triple(row["relatum_label"], "isLandmarkType", row["relatum_type"], triples_format, sub_label, prop_label, obj_label)
        triples.append(relation)
        triples.append(relatum) 

    if change_type == "classement" and change_on == "landmark":
        change = get_triple(row['landmark_label'], "isClassifiedOn", time, triples_format, sub_label, prop_label, obj_label)
    elif change_type == "numerotation" and change_on == "landmark":
        change = get_triple(row['landmark_label'], "isNumberedOn", time, triples_format, sub_label, prop_label, obj_label)
    elif change_type == "appearance" and change_on == "landmark":
        change = get_triple(row['landmark_label'], "appearsOn", time, triples_format, sub_label, prop_label, obj_label)
    elif change_type == "disappearance" and change_on == "landmark":
        change = get_triple(row['landmark_label'], "disappearsOn", time, triples_format, sub_label, prop_label, obj_label)

    elif change_type == "appearance" and change_on == "relation":
        change = get_triple(row['landmark_label'], "hasAppearedRelationOn", time, triples_format, sub_label, prop_label, obj_label)
    elif change_type == "disappearance" and change_on == "relation":
        change = get_triple(row['landmark_label'], "hasDisappearedRelationOn", time, triples_format, sub_label, prop_label, obj_label)
    
    elif change_type == "attribute_version_transition" and change_on == "attribute":
        cap_attr_type = attribute_type.capitalize()
        outdated_version = row['outdates']
        made_effective_version = row['makes_effective']
        change = get_triple(row['landmark_label'],f"has{cap_attr_type}ChangeOn", time, triples_format, sub_label, prop_label, obj_label)
        if pd.notnull(outdated_version):
            addedChange = get_triple(row['landmark_label'], f"hasOld{cap_attr_type}", outdated_version, triples_format, sub_label, prop_label, obj_label)
            triples.append(addedChange)
        
        if pd.notnull(made_effective_version):
            addedChange = get_triple(row['landmark_label'], f"hasNew{cap_attr_type}", made_effective_version, triples_format, sub_label, prop_label, obj_label)
            triples.append(addedChange)

    if change != []:
        triples.append(change)
    
    if row['event'] == "3000":
        print(change)

    
    return line_id, event_label, triples
    

def create_simple_train_set(df, sent_label="sent", triples_label="triples",
                     triples_format="list", sub_label="sub", prop_label="prop", obj_label="obj"):
    """
    Crée un ensemble d'entraînement à partir d'un DataFrame.
    """

    train_set = {}
    for i, row in df.iterrows():

        event_id = row['event']

        line_id, event_label, triples = create_simple_train_set_line(row, triples_format, sub_label, prop_label, obj_label)

        if event_id not in train_set:
            train_set[event_id] = {"id":line_id, sent_label:event_label, triples_label:[]}

        train_set[event_id][triples_label] += triples

    for id in train_set:
        # Supprimer les listes en double
        if triples_format == "list":
            train_set[id][triples_label] = [list(x) for x in set(tuple(x) for x in train_set[id][triples_label])]
        if triples_format == "dict":
            seen = set()
            uniques = []
            for x in train_set[id][triples_label]:
                # On convertit le dict en tuple trié pour qu'il soit hashable
                t = tuple(sorted(x.items()))
                if t not in seen:
                    seen.add(t)
                    uniques.append(x)
            train_set[id][triples_label] = uniques

    return train_set

def export_train_set_in_multiple_files(train_set, files_settings):
        # Créer les fichiers en mode écriture
    files = {path: open(path, "w", encoding="utf-8") for path, _ in files_settings}

    # Créer une liste cumulative pour le tirage au sort
    cum_props = []
    cum = 0.0
    for _, p in files_settings:
        cum += p
        cum_props.append(cum)

    # Pour chaque ligne, choisir le fichier selon la proportion
    for key, value in train_set.items():
        r = random.random()
        for idx, cp in enumerate(cum_props):
            if r < cp:
                path = files_settings[idx][0]
                files[path].write(json.dumps(value, ensure_ascii=False) + "\n")
                break

    # Fermer tous les fichiers
    for f in files.values():
        f.close()

def export_train_set_in_jsonl(train_set, jsonl_file_path):
    jsonl_file = open(jsonl_file_path, "w", encoding="utf-8")
    for key, value in train_set.items():
        jsonl_file.write(str(json.dumps(value, ensure_ascii=False)) + "\n")
    jsonl_file.close()

def export_train_set_in_json(train_set, json_file_path):
    with open(json_file_path, "w", encoding="utf-8") as fp:
            json.dump(train_set, fp, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    # Example usage
    in_path = "../test_in.csv"
    out_path = "../test_out.json"
    df = read_csv(in_path, separator=',')
    df = df.where(pd.notna(df), None)  # Remplacer tous les NaN par None
    create_event_descriptions(df, out_path)
   