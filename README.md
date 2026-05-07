 # AdaphotoRet

基于语义分解与硬槽位匹配的可解释个人照片检索智能体。
核心思想：目前将自然语言查询拆解为宠物、人物、场景等多个语义槽位，结合向量初筛与规则重排，输出你想找的那张图片，并同时输出透明、可追溯的推理链，避免黑箱。

## 功能概述

- 多轮对话式检索：支持逐步描述需求，助手主动追问细节。
- 硬槽位分类匹配：根据查询意图自动切换宠物/人物评分逻辑。
- 宠物细粒度理解：识别品种、毛色、年龄、动作，支持口语化昵称。
- 人物属性支持：识别人数、人种、性别，支持模糊数量表达（≥4 人即为一群）。
- 可解释推理报告：展示打分依据，生成约 200 字的自然语言解释。
- 照片墙浏览：网格展示所有照片，支持翻页。
- 对话管理：新建、删除、切换对话，历史自动保存。

## 技术架构

1. 语义解析：提取实体、人物/宠物属性、场景意图。
2. 向量初筛：FAISS 结合 Sentence-BERT 快速召回候选。
3. 规则重排：硬槽位检查、品种别名归一化、人数判定、活动加权。
4. 解释生成：推理链结合 LLM 输出自然语言说明。
5. 多轮交互：助手根据置信度决定提问或执行检索。

标注阶段离线调用视觉模型生成结构化元数据（metadata_cache.json）。

## 项目结构

```
AdaphotoRet_mvp1/
├── data/
│   ├── category1/                 # 人物/生活照片
│   └── category2/                  # 宠物照片
├── AdaphotoRet_run.py       # 核心检索逻辑
├── streamlit_ui.py          # Streamlit 主界面
├── auto_label.py            # 离线标注脚本
├── attributes.py            # 属性提取与别名映射
├── llm_explainer.py         # LLM 解释生成
├── metadata_cache.json      # 离线生成的元数据
├── packages.txt
└── requirements.txt
```

1. 安装依赖

```bash
conda create -n adaphotoret python=3.10
conda activate adaphotoret
pip install -r requirements.txt
```

2. 动态设置你的DASHSCOPE/DEEPSEEK_API_KEY

```bash
export DASHSCOPE_API_KEY="your_key"
export DEEPSEEK_API_KEY="your_key"
```
3. 在data文件夹下上传你的照片（可不用进行分类）
3. 生成所有照片的元数据（照片越多标注时间越长）

```bash
python auto_label.py
```

4. 启动应用

```bash
streamlit run streamlit_ui.py
```

## 使用说明

- 左侧边栏切换照片墙或对话助手。
- 对话助手初始问候后，输入自然语言描述（例如“一只成年蓝白猫”）。
- 助手可能追问细节，最多 4 轮，之后展示 Top-3 照片与推理报告。
- 每次展示后询问是否满意，可继续调整查询。
- 侧边栏对话管理支持新建、切换、删除历史对话。

## 检索规则部分说明

- 语义相似度基础分系数为 0.45。
- 查询意图与图片主体类型不匹配时直接淘汰。
- 品种识别通过别名归一化和别名集合实现口语化匹配。
- 实际人数 ≥ 4 人即满足“一群”条件。
- 核心活动实体（如“沙滩排球”）享更高加分权重。



