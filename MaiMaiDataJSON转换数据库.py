import json

def process_entry(entry):
    """
    处理单个条目，将其转换为目标格式。
    """
    alias = entry.get("alias", [])
    basic_info = entry.get("basic_info", {})
    ds = entry.get("ds", [])
    old_ds = entry.get("old_ds", [])
    level = entry.get("level", [])
    id_ = entry.get("id", "")
    title = entry.get("title", "")

    # 处理 type 字段
    type_value = entry.get("type", "").upper()
    if type_value == "SD":
        type_value = "标准"
    elif type_value == "DX":
        pass  # 保持不变
    else:
        type_value = ""  # 默认值

    # 构建基础信息部分
    processed_basic_info = {
        "artist": basic_info.get("artist", ""),
        "bpm": basic_info.get("bpm", 0),
        "版本": basic_info.get("from", ""),  # 修改字段名
        "流派": basic_info.get("genre", ""),  # 修改字段名
        "image_url": basic_info.get("image_url", ""),
        "是否为Best15曲": basic_info.get("is_new", False),
        "歌名": basic_info.get("title", ""),  # 修改字段名
        "版本代号": basic_info.get("version", ""),  # 修改字段名
        "定数": ds,
        "MusicID": id_,
        "等级": level,
        "老定数": old_ds,
        "title": title,
        "type": type_value  # 处理后的 type 字段
    }

    return {
        "别名": alias,
        "基础信息": processed_basic_info
    }

def main():
    # 输入文件路径
    input_file = 'input.json'
    # 输出文件路径
    output_file = 'output.json'

    # 打开并加载原始 JSON 文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 处理每个条目
    processed_entries = []
    for i, entry in enumerate(data):
        processed_entry = process_entry(entry)
        processed_entries.append(processed_entry)

 
    # 将处理后的数据保存到新的 JSON 文件中
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_entries, f, ensure_ascii=False, indent=4)

    print(f"处理完成，结果已保存到 {output_file}")

if __name__ == "__main__":
    main()
