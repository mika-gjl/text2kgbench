from namespaces import NameSpaces
import file_management as fm
import graphdb as gd
import graphrdf as gr
import states_events_json as sej
from rdflib import Graph, URIRef
import json
import csv_ground_truth_to_json as cgtj

# 初始化命名空间
np = NameSpaces()

def create_graph_from_events(events_json_file: str):
    """
    Création d'un graphe à partir du fichier JSON des événements
    """
    print(f"Traitement du fichier : {events_json_file}")  
    try:
        # 读取JSON文件，确保使用utf-8编码以支持Unicode
        with open(events_json_file, 'r', encoding='utf-8') as file:
            event_descriptions = json.load(file)
    except Exception as e:
        print(f"Erreur lors de la lecture de {events_json_file}: {e}")
        return Graph()  # Retourne un graphe vide pour éviter l'arrêt du programme
    
    print(event_descriptions)
    
    g = sej.create_graph_from_event_descriptions(event_descriptions)
    np.bind_namespaces(g)
    return g

def serialize_graph(g, output_file):
    """
    Sérialiser le graphe au format Turtle
    """
    try:
        # 在序列化时确保以UTF-8编码保存
        with open(output_file, 'w', encoding='utf-8') as file:
            g.serialize(file, format="turtle")
        print(f"Graph correctement sérialisé dans {output_file}")
    except Exception as e:
        print(f"Erreur lors de la sérialisation du graphe : {e}")

if __name__ == '__main__': 

    # Code principal
    data_json_folder = "../data/json/"
    data_folder = "../data/"

    # Transformation du ground truth CSV en JSON puis en TTL
    csv_ground_truth = data_folder + "ground_truth.csv"
    json_ground_truth = data_folder + "ground_truth_complex.json"
    jsonl_ground_truth = data_folder + "ground_truth_complex.jsonl"
    events_ttl_file = data_json_folder + "events_complex.ttl"

    df = cgtj.read_csv(csv_ground_truth, separator='\t')
    cgtj.create_event_descriptions(df, json_ground_truth)

    g = create_graph_from_events(json_ground_truth)
    np.bind_namespaces(g)
    g.serialize(events_ttl_file)

    ##### Partie commentée pour la création du graphe à partir des fichiers JSON des événements #####

    # events_json_files = {
    #     "11753":"avenue_ledru_rollin",
    #     "9198":"place_bataillon_pacifique",
    #     "11578":"place_jules_joffrin",
    #     "8849":"rue_albert_sorel",
    #     "9051":"rue_armand_carrel",
    #     "10817":"rue_francs_bourgeois",
    #     "11829":"rue_lesdiguieres",
    #     "11970":"rue_lyon",
    #     "12269":"rue_mizon",
    #     "12740":"rue_pere_corentin",
    # }
    # events_ttl_file = data_json_folder + "events.ttl"

    # # # 在调用 g.add() 之前打印 landmark_type
    # # print(f"landmark_type: {landmark_type}")

    # # # 确保 landmark_type 不为 None
    # # if landmark_type is None:
    # #     raise ValueError(f"landmark_type cannot be None for landmark {landmark_uri}")
    # # else:
    # #     g.add((landmark_uri, np.ADDR["isLandmarkType"], landmark_type))

    # # 创建一个空的RDF图
    # g = Graph()
    # np.bind_namespaces(g)

    # # 处理所有的事件文件
    # for name in events_json_files.values():
    #     json_file_path = data_json_folder + name + ".json"
    #     g += create_graph_from_events(json_file_path)

    # g.serialize(events_ttl_file)
    # # # 将图序列化到Turtle文件
    # # serialize_graph(g, events_ttl_file)

    ###################################################################################################

    # Import events ttl file in graph db repository
    graphdb_url = URIRef("http://localhost:7000/")
    repository_name = "text2KGbenchTest"
    local_config_file = data_folder + "repo_config_file.ttl"
    ont_file =  data_folder + "ontology-addresses.ttl"

    gd.reinitialize_repository(graphdb_url, repository_name, local_config_file, ruleset_name="rdfsplus-optimized", disable_same_as=True, allow_removal=False)
    gd.load_ontologies(graphdb_url, repository_name, [ont_file], "ontology")
    gd.import_ttl_file_in_graphdb(graphdb_url, repository_name, events_ttl_file, "events")

    ###################################################################################################

    query1 = """
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX addr: <http://rdf.geohistoricaldata.org/def/address#>
    SELECT DISTINCT ?prov ?desc WHERE {
        ?elem prov:wasDerivedFrom ?prov .
        ?ev a addr:Event ; rdfs:comment ?desc ; prov:wasDerivedFrom ?prov . 
    }
    """
    
    query2 = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX : <http://rdf.geohistoricaldata.org/def/address#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX addr: <http://rdf.geohistoricaldata.org/def/address#>
SELECT DISTINCT * WHERE {
    ?ev prov:wasDerivedFrom ?prov.
    OPTIONAL {
        ?ev ?evProp ?evType ; rdfs:label ?evLabel .
    	FILTER(?evProp IN (addr:isAttributeType, addr:isLandmarkType, addr:isLandmarkRelationType))
    }
    OPTIONAL { ?ev addr:hasTime [addr:timeStamp ?time] . }
    OPTIONAL {
        ?cg addr:isChangeType ?cgType ; addr:dependsOn ?ev ; addr:appliedTo ?elem .
        OPTIONAL {
            ?elem ?elemProp ?elemType .
            OPTIONAL {?elem rdfs:label ?elemLabel }
            FILTER(?elemProp IN (addr:isAttributeType, addr:isLandmarkType, addr:isLandmarkRelationType))
            OPTIONAL {
                ?cg ?cgProp ?attrVersion .
                ?attrVersion addr:versionValue ?versionValue .
                FILTER(?cgProp IN (addr:makesEffective, addr:outdates))
            }
        }
    }
} 
    """

    query3 = """
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX addr: <http://rdf.geohistoricaldata.org/def/address#>
SELECT DISTINCT ?prov ?lr ?loc ?rel WHERE {
    ?lr a addr:LandmarkRelation ; addr:locatum ?loc ; addr:relatum ?rel ; prov:wasDerivedFrom ?prov .
} 
"""

    query4 = """
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX addr: <http://rdf.geohistoricaldata.org/def/address#>
SELECT DISTINCT ?lm ?attr ?prov WHERE {
    ?lm a addr:Landmark ;  addr:hasAttribute ?attr ; prov:wasDerivedFrom ?prov .
} 
"""

    mapping = {
        "http://rdf.geohistoricaldata.org/id/codes/address/changeType/LandmarkNumerotation" : "landmark_numerotation",
        "http://rdf.geohistoricaldata.org/id/codes/address/changeType/LandmarkClassement" : "landmark_classement",
        "http://rdf.geohistoricaldata.org/id/codes/address/changeType/LandmarkAppearance" : "landmark_appearance",
        "http://rdf.geohistoricaldata.org/id/codes/address/changeType/LandmarkDisappearance" : "landmark_disappearance",
        "http://rdf.geohistoricaldata.org/id/codes/address/changeType/LandmarkRelationAppearance" : "landmark_relation_appearance",
        "http://rdf.geohistoricaldata.org/id/codes/address/changeType/LandmarkRelationDisappearance" : "landmark_relation_disappearance",
        "http://rdf.geohistoricaldata.org/id/codes/address/changeType/AttributeVersionTransition" : "attribute_version_transition",

        "http://rdf.geohistoricaldata.org/def/address#isLandmarkType": "isLandmarkType",
        "http://rdf.geohistoricaldata.org/def/address#isLandmarkRelationType": "isLandmarkRelationType",
        "http://rdf.geohistoricaldata.org/def/address#isAttributeType": "isAttributeType",
        
        "http://rdf.geohistoricaldata.org/id/codes/address/landmarkType/Thoroughfare" : "thoroughfare",
        "http://rdf.geohistoricaldata.org/id/codes/address/landmarkType/Municipality" : "municipality",
        "http://rdf.geohistoricaldata.org/id/codes/address/landmarkType/HouseNumber" : "house_number",
        "http://rdf.geohistoricaldata.org/id/codes/address/landmarkRelationType/Within" : "within",
        "http://rdf.geohistoricaldata.org/id/codes/address/landmarkRelationType/Belongs" : "belongs",
        "http://rdf.geohistoricaldata.org/id/codes/address/attributeType/Geometry" : "geometry",
        "http://rdf.geohistoricaldata.org/id/codes/address/attributeType/Name" : "name",

        "http://rdf.geohistoricaldata.org/def/address#outdates" : "outdates",
        "http://rdf.geohistoricaldata.org/def/address#makesEffective" : "makes_effective"

    }

    results1 = gd.select_query_to_json(query1 , graphdb_url, repository_name)
    results1 =  results1.get("results").get("bindings")
    results2 = gd.select_query_to_json(query2 , graphdb_url, repository_name)
    results2 =  results2.get("results").get("bindings")
    results3 = gd.select_query_to_json(query3 , graphdb_url, repository_name)
    results3 =  results3.get("results").get("bindings")
    results4 = gd.select_query_to_json(query4 , graphdb_url, repository_name)
    results4 =  results4.get("results").get("bindings")
    outputs = {}

    namespace = "http://rdf.geohistoricaldata.org/id/address/factoids/"
    prov_namespace = "https://opendata.paris.fr/explore/dataset/denominations-emprises-voies-actuelles/"

    for element in results1:
        # Retrieval of URIs (attribute and attribute version) and geometry
        prov = gr.convert_result_elem_to_rdflib_elem(element.get('prov'))
        prov_id = prov.strip().replace(prov_namespace, "")
        desc = gr.convert_result_elem_to_rdflib_elem(element.get('desc'))
        output = {"id":prov_id,"sent":desc.strip(),"triples":[]}
        outputs[prov_id] = output

    for element in results2:
        # Retrieval of URIs (attribute and attribute version) and geometry
        ev = gr.convert_result_elem_to_rdflib_elem(element.get('ev'))
        ev_type = gr.convert_result_elem_to_rdflib_elem(element.get('evType'))
        ev_prop = gr.convert_result_elem_to_rdflib_elem(element.get('evProp'))
        ev_label = gr.convert_result_elem_to_rdflib_elem(element.get('evLabel'))

        prov = gr.convert_result_elem_to_rdflib_elem(element.get('prov'))
        prov_id = prov.strip().replace(prov_namespace, "")
        time = gr.convert_result_elem_to_rdflib_elem(element.get('time'))

        cg = gr.convert_result_elem_to_rdflib_elem(element.get('cg'))
        cg_type = gr.convert_result_elem_to_rdflib_elem(element.get('cgType'))
        cg_prop = gr.convert_result_elem_to_rdflib_elem(element.get('cgProp'))
        elem = gr.convert_result_elem_to_rdflib_elem(element.get('elem'))
        elem_type = gr.convert_result_elem_to_rdflib_elem(element.get('elemType'))
        elem_prop = gr.convert_result_elem_to_rdflib_elem(element.get('elemProp'))
        attr_version = gr.convert_result_elem_to_rdflib_elem(element.get('attrVersion'))
        version_value = gr.convert_result_elem_to_rdflib_elem(element.get('versionValue'))
        output = outputs.get(prov_id)
        triples = []

        ev_id = ev.strip().replace(namespace, "")

        if None not in [ev, ev_prop, ev_type]:
            triples.append({"sub": ev_id, "rel": mapping.get(ev_prop.strip()), "obj": mapping.get(ev_type.strip())})
        if None not in [ev, ev_label]:
            triples.append({"sub": ev_id, "rel": "label", "obj": ev_label.n3()})

        if time is not None:
            triples.append({"sub": ev_id, "rel": "hasTime", "obj": time.strip()})

        if None not in [ev,cg]:
            triples.append({"sub": ev_id, "rel": "hasChange", "obj": cg.strip().replace(namespace, "")})

        if None not in [cg, cg_type]:
            triples.append({"sub": cg.strip().replace(namespace, ""), "rel": "isChangeType", "obj": mapping.get(cg_type.strip())})
        if None not in [cg, elem]:
            triples.append({"sub": cg.strip().replace(namespace, ""), "rel": "appliedTo", "obj": elem.strip().replace(namespace, "")})
        if None not in [elem, elem_prop,elem_type]:
            triples.append({"sub": elem.strip().replace(namespace, ""), "rel": mapping.get(elem_prop.strip()), "obj": mapping.get(elem_type.strip())})

        if None not in [cg, cg_prop, attr_version]:
            triples.append({"sub": cg.strip().replace(namespace, ""), "rel": mapping.get(cg_prop.strip()), "obj": attr_version.strip().replace(namespace, "")})
        
        if None not in [attr_version, version_value]:
            triples.append({"sub": attr_version.strip().replace(namespace, ""), "rel":"versionValue", "obj": version_value.n3()})     
        
        output["triples"] += triples

    for element in results3:
        # Retrieval of URIs (attribute and attribute version) and geometry
        prov = gr.convert_result_elem_to_rdflib_elem(element.get('prov'))
        prov_id = prov.strip().replace(prov_namespace, "")
        lm_relation = gr.convert_result_elem_to_rdflib_elem(element.get('lr'))
        locatum = gr.convert_result_elem_to_rdflib_elem(element.get('loc'))
        relatum = gr.convert_result_elem_to_rdflib_elem(element.get('rel'))
       
        output = outputs.get(prov_id)
        triples = []
        if None not in [lm_relation, locatum]:
            triples.append({"sub": lm_relation.strip().replace(namespace, ""), "rel":"locatum", "obj": locatum.strip().replace(namespace, "")})
        if None not in [lm_relation, relatum]:
            triples.append({"sub": lm_relation.strip().replace(namespace, ""), "rel":"relatum", "obj": relatum.strip().replace(namespace, "")})

        output["triples"] += triples

    for element in results4:
        # Retrieval of URIs (attribute and attribute version) and geometry
        prov = gr.convert_result_elem_to_rdflib_elem(element.get('prov'))
        prov_id = prov.strip().replace(prov_namespace, "")
        lm = gr.convert_result_elem_to_rdflib_elem(element.get('lm'))
        attr = gr.convert_result_elem_to_rdflib_elem(element.get('attr'))
       
        output = outputs.get(prov_id)
        triples = []
        if None not in [lm, attr]:
            triples.append({"sub": lm.strip().replace(namespace, ""), "rel":"hasAttribute", "obj": attr.strip().replace(namespace, "")})

        output["triples"] += triples

    for output in outputs.values():
        triples = output["triples"]
        final_triples = []
        for triple in triples:
            if triple not in final_triples:
                final_triples.append(triple)

        output["triples"] = final_triples

    #### Partie commentée pour la création du ground truth à partir des événements JSON ####
    # ground_truth_folder = "../../ground_truth/"
    # for prov_id, name in events_json_files.items():
    #     ground_truth_file = ground_truth_folder + f"{name}_ground_truth.jsonl"
    #     local_output = {}
    #     for key, value in outputs.items():
    #         if prov_id in key:
    #             local_output[key] = value

    #     is_first_line = True
    #     # Écrire en JSONL
    #     with open(ground_truth_file, "w", encoding="utf-8") as f:
    #         for key, value in local_output.items():
    #             if is_first_line:
    #                 is_first_line = False
    #             else:
    #                 f.write(",\n")
    #             f.write(json.dumps(value, ensure_ascii=False))

    ###################################################################################################

    ground_truth_folder = "../../ground_truth/"
    ground_truth_file = ground_truth_folder + f"ground_truth_complexe.json"
    

    is_first_line = True
    #Écrire en JSONL
    with open(ground_truth_file, "w", encoding="utf-8") as f:
       for key, value in outputs.items():
            if is_first_line:
               is_first_line = False
            else:
                f.write(",\n")
            f.write(json.dumps(value, ensure_ascii=False))

