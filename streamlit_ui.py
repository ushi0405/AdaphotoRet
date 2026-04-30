import json
import os
from datetime import datetime
from typing import Dict, List
import streamlit as st
from AdaphotoRet_run import search_photos, image_paths, metadata
from llm_explainer import get_deepseek_client

CHAT_HISTORY_FILE = "chat_history.json"

def load_all_conversations():
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_all_conversations(convs):
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(convs, f, ensure_ascii=False, indent=2)

# ---------- 页面配置 ----------
st.set_page_config(page_title="AdaphotoRet", page_icon="🐱", layout="wide")

# ---------- 强制取消所有高度限制 ----------
st.markdown("""
<style>
/* 让聊天消息内容区域完全自适应高度，不截断 */
div[data-testid="stChatMessageContent"] {
    overflow: visible !important;
    max-height: none !important;
    height: auto !important;
}
/* 展开器内容也去除高度限制 */
div[data-testid="stExpanderContent"] {
    max-height: none !important;
    overflow: visible !important;
}
/* Markdown区域自然显示 */
.stMarkdown {
    overflow: visible !important;
}
/* 图片美化 */
.stChatMessage img {
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

# ---------- 初始化会话状态 ----------
if "conversations" not in st.session_state:
    st.session_state.conversations = load_all_conversations()
if "current_conv_id" not in st.session_state:
    convs = st.session_state.conversations
    if convs:
        latest_id = max(convs.keys(), key=lambda x: convs[x]["created"])
        st.session_state.current_conv_id = latest_id
    else:
        now = datetime.now().isoformat()
        new_id = now
        st.session_state.conversations[new_id] = {
            "name": "新对话",
            "created": now,
            "messages": []
        }
        st.session_state.current_conv_id = new_id

# 自动问候
def ensure_greeting():
    conv = get_current_conversation()
    if conv and not conv["messages"]:
        greeting = {
            "role": "assistant",
            "content": "你好～我是AdaphotoRet，你的私人记忆相册。想找哪张照片呢？可以直接告诉我哦！",
            "thinking": "",
            "images": [],
            "report": ""
        }
        conv["messages"].append(greeting)
        save_all_conversations(st.session_state.conversations)

def get_current_conversation():
    return st.session_state.conversations.get(st.session_state.current_conv_id)

def get_current_messages():
    conv = get_current_conversation()
    return conv["messages"] if conv else []

def add_message(role, content, thinking="", images=None, report=""):
    conv = get_current_conversation()
    if conv:
        conv["messages"].append({
            "role": role,
            "content": content,
            "thinking": thinking,
            "images": images or [],
            "report": report
        })
        save_all_conversations(st.session_state.conversations)

def search_photos_tool(query):
    result = search_photos(query)
    top1, top2, top3, report, table_data, top_results = result
    return {
        "top1": top1,
        "top2": top2,
        "top3": top3,
        "report": report,
        "table": table_data,
        "top_results": top_results
    }

def run_assistant(user_message):
    messages = get_current_messages()
    add_message("user", user_message)

    client = get_deepseek_client()
    context = [{"role": m["role"], "content": m["content"]} for m in messages[-5:]]
    system_prompt = """你是一个照片检索助手，名叫“AdaphotoRet”。你必须遵循以下原则：
1. 你的默认任务是让最佳匹配照片符合用户输入。当用户的查询不够具体时，你应主动在【提问】中列出关键差异并给出选项。但当你收到用户的回答后，必须结合你自己的问题和用户的回答来推断真正的意图。
2. **意图整合规则（极其重要）**：
   - 如果你问了一个具体特征（例如“是橘猫吗？”），而用户回答“记不清了”、“不知道”、“不确定”或类似表达，你必须立即丢弃该特征，不能再将其加入任何查询词。
   - 在进行【检索】前，你必须重新审视整个对话，只提取经过双方确认的有效信息。你问过的、但被用户否定或表示模糊的问题，一律不得使用。
3. 每次追问最多涉及两个问题，最大连续追问次数为4次，四次后必须输出照片。
4. 当连续两次追问都得到模糊回答（如“记不清楚”）时，必须立即根据已有确定线索输出照片。
5. 当你认为有70%以上信心时，必须停止追问，直接检索。
6. **检索关键词生成规则**：
   - 必须把对话历史中经双方确认的关键描述整合成完整查询词。
   - 只能使用用户明确确认或你从对话中推断出的有效词语，绝对不能使用已被用户否定或表示模糊的特征。
   - 绝对不能使用“回答”、“提供”、“信息”、“找到”、“想要”、“不够”、“准确”、“请”、“告诉”、“需要”、“调整”等系统引导词。
7. 展示照片后，必须在末尾追问“这里有您想要的照片吗？如果不够准确，请告诉我哪里需要调整。”
8. 回复格式必须严格为：
   【思考】你的内部推理过程（必须包含对用户否定信息的处理）
   【行动】“提问：你的问题内容” 或 “检索：优化后的查询词” 或 “回答：你的最终答复（包含追问）”
不要输出其他内容。"""
    context.insert(0, {"role": "system", "content": system_prompt})

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=context,
            temperature=0.3,
            max_tokens=400,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        reply = f"【思考】调用失败：{e}\n【行动】回答：抱歉，请稍后再试。"

    thinking_part = ""
    action_part = ""
    if "【行动】" in reply:
        parts = reply.split("【行动】")
        thinking_part = parts[0].replace("【思考】", "").strip()
        action_part = parts[1].strip()
    elif "【思考】" in reply:
        thinking_part = reply.replace("【思考】", "").strip()
        summary_prompt = f"""根据以下对话历史，提炼出一个完整的照片检索查询词。
规则：
1. 只能使用用户明确描述的、或者你从对话中推断出的有效信息。
2. 如果助手的提问被用户用“记不清了”、“不知道”等否定，则必须丢弃该特征。
3. 绝不能出现“回答”、“提供”、“信息”、“找到”、“想要”、“不够”、“准确”、“请”、“告诉”、“需要”、“调整”等系统引导词。
对话历史：
{chr(10).join([f"用户：{m['content']}" for m in messages[-5:] if m['role'] == 'user'])}"""
        try:
            summary_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.2,
                max_tokens=100,
            )
            optimized_query = summary_response.choices[0].message.content.strip()
        except Exception:
            optimized_query = user_message
        action_part = "检索：" + optimized_query
    else:
        thinking_part = "尝试理解中..."
        summary_prompt = f"""根据以下对话历史，提炼出一个完整的照片检索查询词。
规则：
1. 只能使用用户明确描述的、或者你从对话中推断出的有效信息。
2. 如果助手的提问被用户用“记不清了”、“不知道”等否定，则必须丢弃该特征。
3. 绝不能出现“回答”、“提供”、“信息”、“找到”、“想要”、“不够”、“准确”、“请”、“告诉”、“需要”、“调整”等系统引导词。
对话历史：
{chr(10).join([f"用户：{m['content']}" for m in messages[-5:] if m['role'] == 'user'])}"""
        try:
            summary_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.2,
                max_tokens=100,
            )
            optimized_query = summary_response.choices[0].message.content.strip()
        except Exception:
            optimized_query = user_message
        action_part = "检索：" + optimized_query

    if action_part.startswith("提问："):
        question = action_part.replace("提问：", "").strip()
        add_message("assistant", question, thinking=thinking_part)
    elif action_part.startswith("检索："):
        query = action_part.replace("检索：", "").strip()
        results = search_photos_tool(query)
        imgs = [results["top1"], results["top2"], results["top3"]]
        content = "我找到了以下照片。这里有您想要的照片吗？如果没有，请告诉我需要调整的地方。"
        add_message("assistant", content, thinking=thinking_part, images=[img for img in imgs if img], report=results.get("report", ""))
    elif action_part.startswith("回答："):
        answer = action_part.replace("回答：", "").strip()
        add_message("assistant", answer, thinking=thinking_part)
    else:
        add_message("assistant", "抱歉，请再描述一下。", thinking=thinking_part)

# ---------- 侧边栏导航 ----------
st.sidebar.title("🐱 AdaphotoRet")
page = st.sidebar.radio("导航", ["📷 照片墙", "💬 对话助手"])

if page == "📷 照片墙":
    st.title("📷 照片墙")
    total = len(image_paths)
    per_page = 4
    total_pages = max(1, (total + per_page - 1) // per_page)
    page_num = st.slider("翻页", 1, total_pages, 1)
    start_idx = (page_num - 1) * per_page
    end_idx = min(start_idx + per_page, total)
    cols = st.columns(per_page)
    for i in range(start_idx, end_idx):
        with cols[i - start_idx]:
            st.image(image_paths[i], use_container_width=True)

elif page == "💬 对话助手":
    st.title("💬 对话助手")
    ensure_greeting()

    with st.sidebar.expander("📝 对话管理", expanded=True):
        if st.button("➕ 新建对话"):
            now = datetime.now().isoformat()
            new_id = now
            st.session_state.conversations[new_id] = {
                "name": "新对话",
                "created": now,
                "messages": []
            }
            st.session_state.current_conv_id = new_id
            save_all_conversations(st.session_state.conversations)
            st.rerun()

        convs = st.session_state.conversations
        if convs:
            conv_ids = list(convs.keys())
            conv_ids.sort(key=lambda x: convs[x]["created"], reverse=True)
            for cid in conv_ids:
                cname = convs[cid].get("name", "未命名")
                col1, col2 = st.columns([8, 1])
                with col1:
                    if cid == st.session_state.current_conv_id:
                        st.markdown(f"**🔹 {cname}**")
                    else:
                        if st.button(f"📄 {cname}", key=f"load_{cid}"):
                            st.session_state.current_conv_id = cid
                            st.rerun()
                with col2:
                    if cid != st.session_state.current_conv_id:
                        if st.button("🗑️", key=f"del_{cid}", help="删除该对话"):
                            del st.session_state.conversations[cid]
                            save_all_conversations(st.session_state.conversations)
                            st.rerun()
        else:
            st.caption("暂无对话")

    current_conv = get_current_conversation()
    if current_conv:
        conv_name = st.text_input("对话标题", value=current_conv.get("name", "新对话"), key="conv_name_input")
        if st.button("更新标题"):
            current_conv["name"] = conv_name
            save_all_conversations(st.session_state.conversations)

    # 显示聊天记录
    for msg in get_current_messages():
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                if msg.get("thinking"):
                    st.caption(f"🧠 {msg['thinking']}")
                if msg.get("content"):
                    st.write(msg["content"])
                if msg.get("images"):
                    cols = st.columns(len(msg["images"]))
                    for i, img_path in enumerate(msg["images"]):
                        with cols[i]:
                            st.image(img_path, use_container_width=True)
                if msg.get("report"):
                    st.markdown(msg["report"])

    user_input = st.chat_input("描述你想找的照片...")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        run_assistant(user_input)
        st.rerun()
