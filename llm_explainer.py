import os
from typing import Dict, List
from openai import OpenAI

def get_deepseek_client():
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError("请设置环境变量 DEEPSEEK_API_KEY")
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
    )


def generate_explanation(
    user_query: str,
    top_results: List[Dict],
    metadata: Dict,
) -> str:
    if not top_results:
        return "无结果，无法生成解释。"

    info_text = ""
    for idx, r in enumerate(top_results, start=1):
        img_path = r["img_path"]
        img_info = metadata.get(img_path, {})
        desc = img_info.get("description", "无描述")
        scene = img_info.get("scene", "未知场景")
        keywords = img_info.get("keywords", [])
        people = img_info.get("main_subjects", {})
        pet = img_info.get("pet_details", {})
        category = img_info.get("category", "")
        is_pet = (category == "宠物") or bool(pet)

        trace = r["trace"]
        matched_rules = [f"{rule}: {evidence}" for rule, delta, evidence in trace if delta > 0]
        mismatched_rules = [f"{rule}: {evidence}" for rule, delta, evidence in trace if delta < 0]

        info_text += f"""
【图片 {idx}】路径：{img_path}
场景：{scene}
描述：{desc}
关键词：{', '.join(keywords) if keywords else '无'}
"""
        if is_pet:
            pet_breed = pet.get("breed", "未知")
            pet_color = pet.get("coat_color", [])
            pet_life = pet.get("life_stage", "未知")
            info_text += f"""宠物信息：品种={pet_breed}，毛色={pet_color}，年龄={pet_life}
"""
        else:
            if people:
                cnt = people.get("count", 0)
                cnt_cat = people.get("count_category", "未知")
                eth = people.get("primary_ethnicity", "未知")
                info_text += f"""人物信息：数量={cnt_cat}（实际{cnt}人），人种={eth}
"""

        info_text += f"""匹配的规则：{matched_rules if matched_rules else '无'}
不匹配的规则：{mismatched_rules if mismatched_rules else '无'}
得分：{r['score']}
"""

    prompt = f"""你是一个图像检索系统的可解释性助手。用户查询是："{user_query}"。

系统返回了 Top3 候选图片，请根据每张图片的元数据和匹配规则，必须用中文生成一段约150字的解释。
要求：
1. 首先概括整体检索情况。
2. 对每张图片，详细说明选择图片的原因，以及可能存在的不足（尤其对于排名靠后的图片）。
3. 语气客观、专业，避免重复。
4. 每张图片概述的最少字数不得少于100。
5. **特别注意**：
   - 如果图片包含“宠物信息”，则**严禁**在解释中提及任何人物数量、人种或“一群人”的相关描述，仅围绕宠物特征展开。
   - 本系统中，“一群人”的定义是 **4人及以上**，该规则仅适用于人物照片，不得用于宠物照片。
6. **格式要求（非常重要）**：
   - 禁止使用任何 Markdown 标题符号（如 `#`、`##`、`###`）或粗体（`**`）来标记图片编号。
   - 每张图片的描述必须用普通文本，格式为：`图片X（得分Y）：` 后直接接内容，冒号为中文冒号。
   - 不要添加额外的空行或分割线。
   - 图片描述之间用正常换行分隔即可。

以下是图片信息：
{info_text}

请输出解释文本（不要包含其他无关内容，严格按照格式要求）："""

    try:
        client = get_deepseek_client()
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"解释生成失败：{e}"
