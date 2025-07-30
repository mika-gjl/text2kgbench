import argparse
import sys
import os
import json
import re
from typing import List, Dict, Set, Tuple
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer


def calculate_precision_recall_f1(gold: Set, pred: Set) -> (float, float, float):
    """
    Method to calculate precision, recall and f1:
        Precision is calculated as correct_triples/predicted_triples and
        Recall as correct_triples/gold_triples
        F1 as the harmonic mean of precision and recall.
    """
    if len(pred) == 0:
        return 0, 0, 0
    p = len(gold.intersection(pred)) / len(pred)
    r = len(gold.intersection(pred)) / len(gold)
    if p + r > 0:
        f1 = 2 * ((p * r) / (p + r))
    else:
        f1 = 0
    return p, r, f1


def get_subject_object_hallucinations(ps, ontology, test_sentence, triples) -> (float, float):
    """
    Calculate subject and object hallucination metrics. UUIDs (e.g., LM_xxx, EV_xxx) are skipped.
    """
    if len(triples) == 0:
        return 0, 0

    test_sentence += " ".join([c["label"] for c in ontology['concepts']])
    stemmed_sentence = "".join([ps.stem(word) for word in word_tokenize(test_sentence)])
    normalized_stemmed_sentence = re.sub(r"(_|\s+)", "", stemmed_sentence).lower()

    uuid_pattern = re.compile(r"^(LM|EV|CG|ATTR|AV|LMR)_[0-9a-f]{32}$")

    num_subj_hallucinations = 0
    num_obj_hallucinations = 0

    for triple in triples:
        subj, rel, obj = triple

        subj_str = "" if subj is None else str(subj)
        obj_str = "" if obj is None else str(obj)

        if uuid_pattern.match(subj_str):
            normalized_stemmed_subject = None
        else:
            normalized_stemmed_subject = clean_entity_string(ps, subj_str)

        if uuid_pattern.match(obj_str):
            normalized_stemmed_object = None
        else:
            normalized_stemmed_object = clean_entity_string(ps, obj_str)

        if normalized_stemmed_subject is not None:
            if normalized_stemmed_sentence.find(normalized_stemmed_subject) == -1:
                num_subj_hallucinations += 1

        if normalized_stemmed_object is not None:
            if normalized_stemmed_sentence.find(normalized_stemmed_object) == -1:
                num_obj_hallucinations += 1

    subj_hallucination = num_subj_hallucinations / len(triples)
    obj_hallucination = num_obj_hallucinations / len(triples)
    return subj_hallucination, obj_hallucination


def get_ontology_conformance(ontology: Dict, triples: List) -> (float, float):
    """
    Calculate ontology conformance and relation hallucination metrics.
    """
    if len(triples) == 0:
        return 1, 0

    ont_rels_raw = []
    for rel in ontology.get('relations', []):
        pid = rel.get('pid', '')
        if ':' in pid:
            local_name = pid.split(':', 1)[1]
        else:
            local_name = pid
        ont_rels_raw.append(local_name)

    ont_rels_norm = {r.replace("_", "").lower() for r in ont_rels_raw}
    ont_rels_norm.add("label")

    system_rels_raw = [
        tr[1] for tr in triples
        if isinstance(tr, (list, tuple)) and len(tr) > 1
    ]
    system_rels_norm = [r.replace("_", "").lower() for r in system_rels_raw]

    num_rels_conformant = sum(1 for rel_norm in system_rels_norm if rel_norm in ont_rels_norm)

    ont_conformance = num_rels_conformant / len(triples)
    rel_hallucination = 1 - ont_conformance
    return ont_conformance, rel_hallucination


def normalize_triple(sub_label: str, rel_label: str, obj_label: str) -> str:
    """
    Normalize triples for comparison in precision/recall calculations.
    If subject or object is a UUID, only keep the prefix.
    """
    sub_label = "" if sub_label is None else str(sub_label)
    rel_label = "" if rel_label is None else str(rel_label)
    obj_label = "" if obj_label is None else str(obj_label)

    m_sub = re.match(r"^(LM|EV|CG|ATTR|AV|LMR)_[0-9a-f\-]{32,}$", sub_label)
    if m_sub:
        sub_norm = m_sub.group(1).lower()
    else:
        sub_norm = re.sub(r"(_|\s+)", '', sub_label).lower()

    rel_norm = re.sub(r"(_|\s+)", '', rel_label).lower()

    m_obj = re.match(r"^(LM|EV|CG|ATTR|AV|LMR)_[0-9a-f\-]{32,}$", obj_label)
    if m_obj:
        obj_norm = m_obj.group(1).lower()
    else:
        obj_norm = re.sub(r"(_|\s+)", '', obj_label).lower()

    return f"{sub_norm}{rel_norm}{obj_norm}"


def clean_entity_string(ps, entity: str) -> str:
    """
    Clean subject and object strings of triples for hallucination detection.
    """
    stemmed_entity = "".join([ps.stem(word) for word in word_tokenize(entity)])
    normalized_stemmed_entity = re.sub(r"(_|\s+)", '', stemmed_entity).lower()
    return normalized_stemmed_entity.replace("01januari", "")


def read_jsonl(jsonl_path: str, is_json: bool = True) -> List:
    """
    Read lines from a .jsonl file into a data list.
    """
    data = []
    if not os.path.exists(jsonl_path):
        print(f"❌ Debug - 文件不存在: {jsonl_path}")
        return data

    with open(jsonl_path, "r", encoding="utf-8") as in_file:
        for line in in_file:
            line = line.strip()
            if not line:
                continue
            if is_json:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"⚠️ Debug - JSON 解析失败: {e}\n行: {line}")
            else:
                data.append(line)
    print(f"☑️ Debug - 从 {jsonl_path} 读取了 {len(data)} 条记录")
    return data


def load_config(eval_config_path: str) -> Dict:
    """
    Load the evaluation configuration file.
    """
    raw_config = read_json(eval_config_path)
    onto_list = raw_config.get('onto_list', [])
    path_patterns = raw_config.get("path_patterns", {})
    new_config = dict()
    expanded_onto_list = list()

    for onto in onto_list:
        onto_data = dict()
        onto_data["id"] = onto
        for key in path_patterns:
            onto_data[key] = path_patterns[key].replace("$$onto$$", onto)
        expanded_onto_list.append(onto_data)

    new_config["onto_list"] = expanded_onto_list
    new_config["avg_out_file"] = raw_config.get("avg_out_file", "")
    return new_config


def save_jsonl(data: List, jsonl_path: str) -> None:
    """
    Serialize a list of json objects to a .jsonl file.
    """
    with open(jsonl_path, "w", encoding="utf-8") as out_file:
        for item in data:
            out_file.write(f"{json.dumps(item)}\n")
    print(f"☑️ Debug - 写入 {len(data)} 条评估结果到 {jsonl_path}")


def append_jsonl(data: Dict, jsonl_path: str) -> None:
    """
    Append a new line to a .jsonl file.
    """
    with open(jsonl_path, "a+", encoding="utf-8") as out_file:
        out_file.write(f"{json.dumps(data)}\n")
    print(f"☑️ Debug - 追加平均指标到 {jsonl_path}: {data}")


def read_json(json_path: str) -> Dict:
    """
    Read a JSON file into a dictionary.
    """
    if not os.path.exists(json_path):
        print(f"❌ Debug - JSON 文件不存在: {json_path}")
        return {}
    with open(json_path, "r", encoding="utf-8") as in_file:
        content = json.load(in_file)
    print(f"☑️ Debug - 读取配置/本体 JSON: {json_path}")
    return content


def convert_to_dict(data: List[Dict], id_name: str = "id") -> Dict:
    """
    Convert a list of dictionaries into a dictionary keyed by id_name.
    """
    result = {}
    for item in data:
        if id_name in item:
            result[item[id_name]] = item
        else:
            print(f"⚠️ Debug - 在数据项里找不到字段 '{id_name}'，该项将被跳过: {item}")
    print(f"☑️ Debug - convert_to_dict 得到 {len(result)} 个键值对 (key 用 {id_name})")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--eval_config_path', type=str, required=True)
    args = parser.parse_args()

    ps = PorterStemmer()

    eval_config_path = args.eval_config_path
    if not os.path.exists(eval_config_path):
        print(f"❌ Evaluation config file is not found in path: {eval_config_path}")
        sys.exit(1)

    eval_inputs = load_config(eval_config_path)
    print(f"☑️ Debug - 最终装载的 eval_inputs: {json.dumps(eval_inputs, indent=2, ensure_ascii=False)}")

    global_p = global_r = global_f1 = 0
    global_onto_conf = global_rel_halluc = global_sub_halluc = global_obj_halluc = 0

    for onto in eval_inputs.get('onto_list', []):
        onto_id = onto.get('id', 'UNKNOWN')
        print(f"\n🔎 ===== 开始评估本体: {onto_id} =====")

        t_p = t_r = t_f1 = 0
        t_onto_conf = t_rel_halluc = t_sub_halluc = t_obj_halluc = 0

        sel_t_p = sel_t_r = sel_t_f1 = 0
        sel_t_onto_conf = sel_t_rel_halluc = sel_t_sub_halluc = sel_t_obj_halluc = 0

        eval_metrics_list = []

        sys_path = onto.get('sys', '')
        gt_path = onto.get('gt', '')
        test_path = onto.get('test', '')

        print(f"☑️ Debug - Loading system output from: {sys_path}")
        system_list = read_jsonl(sys_path)
        print(f"☑️ Debug - Loading ground truth from: {gt_path}")
        ground_list = read_jsonl(gt_path)
        print(f"☑️ Debug - Loading test set from: {test_path}")
        test_list = read_jsonl(test_path)

        system_output = convert_to_dict(system_list)
        ground_truth = convert_to_dict(ground_list)
        test_sentences = convert_to_dict(test_list, id_name="id")

        onto_path = onto.get('onto', '')
        ontology = read_json(onto_path)

        if 'selected_ids' in onto:
            selected_ids = read_jsonl(onto['selected_ids'], is_json=False)
            print(f"☑️ Debug - selected_ids 列表: {selected_ids}")
        else:
            selected_ids = []
            print(f"☑️ Debug - 没有提供 selected_ids，跳过此环节")

        total_test_cases = len(test_sentences)
        total_selected_test_cases = len(selected_ids)

        # 新增：统计实际上参与评估的测试句子数
        evaluated_count = 0
        evaluated_selected_count = 0

        for sent_id in list(test_sentences.keys()):
            # 如果没有 ground truth，跳过
            if sent_id not in ground_truth:
                continue
            # 如果没有系统输出，跳过
            if sent_id not in system_output:
                continue

            # 既然获得了地面真值和系统输出，就算作一次有效评估
            evaluated_count += 1
            if sent_id in selected_ids:
                evaluated_selected_count += 1

            print(f"\n🔸 处理句子 ID: {sent_id}")
            gt_entry = ground_truth[sent_id]
            gt_triples = [[tr['sub'], tr['rel'], tr['obj']] for tr in gt_entry.get('triples', [])]
            sentence = gt_entry.get("sent", "")
            print(f"    📜 Ground-truth triples: {gt_triples}")
            print(f"    📖 原始句子: {sentence}")

            system_triples = system_output[sent_id].get('triples', [])
            print(f"    🤖 系统输出 triples (raw): {system_triples}")

            normalized_gt_relations = {
                re.sub(r"(_|\s+)", '', str(tr[1])).lower() for tr in gt_triples
            }
            print(f"    🔄 Ground-truth 关系 normalize 后: {normalized_gt_relations}")

            filtered_system_triples = [
                tr for tr in system_triples
                if isinstance(tr, (list, tuple)) and len(tr) > 1 and
                   re.sub(r"(_|\s+)", '', str(tr[1])).lower() in normalized_gt_relations
            ]
            print(f"    🔹 过滤后 system triples: {filtered_system_triples}")

            normalized_system_triples = {
                normalize_triple(tr[0], tr[1], tr[2]) for tr in filtered_system_triples
            }
            normalized_gt_triples = {
                normalize_triple(tr[0], tr[1], tr[2]) for tr in gt_triples
            }
            print(f"    🔄 系统 triples normalize 后: {normalized_system_triples}")
            print(f"    🔄 Ground-truth triples normalize 后: {normalized_gt_triples}")

            precision, recall, f1 = calculate_precision_recall_f1(normalized_gt_triples, normalized_system_triples)
            print(f"    ✅ Precision={precision:.2f}, Recall={recall:.2f}, F1={f1:.2f}")

            ont_conformance, rel_hallucination = get_ontology_conformance(ontology, system_triples)
            print(f"    ✅ Ontology conformance={ont_conformance:.2f}, Rel hallucination={rel_hallucination:.2f}")

            subj_hallucination, obj_hallucination = get_subject_object_hallucinations(ps, ontology, sentence, system_triples)
            print(f"    ✅ Subj hallucination={subj_hallucination:.2f}, Obj hallucination={obj_hallucination:.2f}")

            if f1 < 1 and len(filtered_system_triples) > 0 and subj_hallucination == 0 and obj_hallucination == 0:
                print(f"    🧐 警告: F1 < 1 且没有 sub/obj hallucination！")
                print(f"      Sent: {sentence}")
                print(f"      f1: {f1}")
                print(f"      sys: {filtered_system_triples}")
                print(f"      gt: {gt_triples}")

            eval_metrics = {
                "id": sent_id,
                "precision": f"{precision:.2f}",
                "recall": f"{recall:.2f}",
                "f1": f"{f1:.2f}",
                "onto_conf": f"{ont_conformance:.2f}",
                "rel_halluc": f"{rel_hallucination:.2f}",
                "sub_halluc": f"{subj_hallucination:.2f}",
                "obj_halluc": f"{obj_hallucination:.2f}",
                "llm_triples": system_triples,
                "filtered_llm_triples": filtered_system_triples,
                "gt_triples": gt_triples,
                "sent": sentence
            }
            eval_metrics_list.append(eval_metrics)

            t_p += precision
            t_r += recall
            t_f1 += f1
            t_onto_conf += ont_conformance
            t_rel_halluc += rel_hallucination
            t_sub_halluc += subj_hallucination
            t_obj_halluc += obj_hallucination

            if sent_id in selected_ids:
                sel_t_p += precision
                sel_t_r += recall
                sel_t_f1 += f1
                sel_t_onto_conf += ont_conformance
                sel_t_rel_halluc += rel_hallucination
                sel_t_sub_halluc += subj_hallucination
                sel_t_obj_halluc += obj_hallucination

        # 写 per-sentence 评估结果
        output_path = onto.get('output', '')
        save_jsonl(eval_metrics_list, output_path)

        # 用 evaluated_count 而不是 total_test_cases 来计算平均指标
        if evaluated_count > 0:
            average_metrics = {
                "onto": onto_id,
                "type": "all_test_cases",
                "avg_precision": f"{(t_p / evaluated_count):.2f}",
                "avg_recall":    f"{(t_r / evaluated_count):.2f}",
                "avg_f1":        f"{(t_f1 / evaluated_count):.2f}",
                "avg_onto_conf": f"{(t_onto_conf / evaluated_count):.2f}",
                "avg_sub_halluc":f"{(t_sub_halluc / evaluated_count):.2f}",
                "avg_rel_halluc":f"{(t_rel_halluc / evaluated_count):.2f}",
                "avg_obj_halluc":f"{(t_obj_halluc / evaluated_count):.2f}"
            }
            append_jsonl(average_metrics, eval_inputs['avg_out_file'])
            global_p += (t_p / evaluated_count)
            global_r += (t_r / evaluated_count)
            global_f1 += (t_f1 / evaluated_count)
            global_onto_conf += (t_onto_conf / evaluated_count)
            global_sub_halluc += (t_sub_halluc / evaluated_count)
            global_rel_halluc += (t_rel_halluc / evaluated_count)
            global_obj_halluc += (t_obj_halluc / evaluated_count)
        else:
            print(f"⚠️ Debug - 没有有效的测试案例，无法计算平均指标")

        # 用 evaluated_selected_count 计算 selected 平均指标
        if evaluated_selected_count > 0:
            selected_average_metrics = {
                "onto": onto_id,
                "type": "selected_test_cases",
                "avg_precision": f"{(sel_t_p / evaluated_selected_count):.2f}",
                "avg_recall":    f"{(sel_t_r / evaluated_selected_count):.2f}",
                "avg_f1":        f"{(sel_t_f1 / evaluated_selected_count):.2f}",
                "avg_onto_conf": f"{(sel_t_onto_conf / evaluated_selected_count):.2f}",
                "avg_sub_halluc":f"{(sel_t_sub_halluc / evaluated_selected_count):.2f}",
                "avg_rel_halluc":f"{(sel_t_rel_halluc / evaluated_selected_count):.2f}",
                "avg_obj_halluc":f"{(sel_t_obj_halluc / evaluated_selected_count):.2f}"
            }
            append_jsonl(selected_average_metrics, eval_inputs['avg_out_file'])
        else:
            print(f"⚠️ Debug - 没有有效的 selected_ids 测试案例，跳过此部分")

    # 计算并写入全局指标，需除以本体数量
    num_ontologies = len(eval_inputs.get('onto_list', []))
    if num_ontologies > 0:
        global_metrics = {
            "id": "global",
            "type": "global",
            "avg_precision": f"{(global_p / num_ontologies):.2f}",
            "avg_recall":    f"{(global_r / num_ontologies):.2f}",
            "avg_f1":        f"{(global_f1 / num_ontologies):.2f}",
            "avg_onto_conf": f"{(global_onto_conf / num_ontologies):.2f}",
            "avg_sub_halluc":f"{(global_sub_halluc / num_ontologies):.2f}",
            "avg_rel_halluc":f"{(global_rel_halluc / num_ontologies):.2f}",
            "avg_obj_halluc":f"{(global_obj_halluc / num_ontologies):.2f}",
            "onto_list": eval_inputs.get('onto_list', [])
        }
        append_jsonl(global_metrics, eval_inputs['avg_out_file'])
    else:
        print("⚠️ Debug - 没有本体可计算全局指标")


if __name__ == "__main__":
    sys.exit(main())
