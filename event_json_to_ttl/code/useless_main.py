from namespaces import NameSpaces
import file_management as fm
import states_events_json as sej
from rdflib import Graph
import json

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

# Code principal
data_folder = "../data/json/"
events_json_files = list(set(["rueArmandCarrel.json", "rueduPèreCorentin.json", "placeJulesJoffrin.json", 
                              "rueMizon.json", "rueFrancsBourgeois.json", "rueLyon.json", "rueLesguidieres.json", 
                              "avenueLedruRollin.json", "placeBataillonPacifique.json"]))
events_ttl_file = data_folder + "events.ttl"

# 在调用 g.add() 之前打印 landmark_type
print(f"landmark_type: {landmark_type}")

# 确保 landmark_type 不为 None
if landmark_type is None:
    raise ValueError(f"landmark_type cannot be None for landmark {landmark_uri}")
else:
    g.add((landmark_uri, np.ADDR["isLandmarkType"], landmark_type))

# 创建一个空的RDF图
g = Graph()
np.bind_namespaces(g)

# 处理所有的事件文件
for file in events_json_files:
    json_file_path = data_folder + file
    g += create_graph_from_events(json_file_path)

# 将图序列化到Turtle文件
serialize_graph(g, events_ttl_file)

