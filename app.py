import streamlit as st
from openai import OpenAI
import json
import re
from datetime import datetime
import os
from dotenv import load_dotenv
import hashlib
import pickle
from pathlib import Path
import time
import pandas as pd
import io
from concurrent.futures import ThreadPoolExecutor

# 加载环境变量
load_dotenv()

# DeepSeek API 配置 - 从环境变量中获取
API_KEY = os.getenv("DEEPSEEK_API_KEY")  # 从环境变量获取 API 密钥
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")  # 默认值为 "https://api.deepseek.com"

# 初始化 OpenAI 客户端
try:
    if not API_KEY:
        st.error("错误：未找到 DEEPSEEK_API_KEY 环境变量。请确保已正确设置环境变量或 .env 文件。")
        st.stop()
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
except Exception as e:
    st.error(f"初始化 DeepSeek API 客户端失败：{e}")
    st.stop()

# 添加缓存目录
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# 缓存管理函数
def get_cache_key(part_number):
    """根据元器件型号生成唯一缓存键"""
    return hashlib.md5(part_number.lower().strip().encode()).hexdigest()

def get_cache_path(cache_key):
    """根据缓存键生成缓存文件路径"""
    return CACHE_DIR / f"{cache_key}.pkl"

def save_to_cache(part_number, data, expiry_hours=72):
    """将查询结果保存到缓存"""
    cache_key = get_cache_key(part_number)
    cache_path = get_cache_path(cache_key)
    
    cached_item = {
        "part_number": part_number,
        "data": data,
        "timestamp": time.time(),
        "expiry": time.time() + (expiry_hours * 3600)  # 默认缓存72小时
    }
    
    with open(cache_path, 'wb') as f:
        pickle.dump(cached_item, f)
    
    # 更新缓存统计信息
    if 'cache_stats' not in st.session_state:
        st.session_state.cache_stats = {"total_entries": 0, "hit_count": 0, "miss_count": 0}
    st.session_state.cache_stats["total_entries"] = len(list(CACHE_DIR.glob("*.pkl")))

def get_from_cache(part_number):
    """尝试从缓存获取结果，如果有效则返回，否则返回None"""
    cache_key = get_cache_key(part_number)
    cache_path = get_cache_path(cache_key)
    
    if not cache_path.exists():
        # 更新缓存统计信息
        if 'cache_stats' not in st.session_state:
            st.session_state.cache_stats = {"total_entries": 0, "hit_count": 0, "miss_count": 0}
        st.session_state.cache_stats["miss_count"] += 1
        return None
    
    try:
        with open(cache_path, 'rb') as f:
            cached_item = pickle.load(f)
        
        # 检查缓存是否过期
        if time.time() > cached_item["expiry"]:
            # 更新缓存统计信息
            if 'cache_stats' not in st.session_state:
                st.session_state.cache_stats = {"total_entries": 0, "hit_count": 0, "miss_count": 0}
            st.session_state.cache_stats["miss_count"] += 1
            return None
        
        # 缓存命中
        if 'cache_stats' not in st.session_state:
            st.session_state.cache_stats = {"total_entries": 0, "hit_count": 0, "miss_count": 0}
        st.session_state.cache_stats["hit_count"] += 1
        return cached_item["data"]
    
    except (pickle.PickleError, EOFError, KeyError):
        # 缓存文件损坏，删除它
        cache_path.unlink(missing_ok=True)
        return None

def clear_expired_cache():
    """清理所有过期的缓存文件"""
    current_time = time.time()
    cleared_count = 0
    
    for cache_file in CACHE_DIR.glob("*.pkl"):
        try:
            with open(cache_file, 'rb') as f:
                cached_item = pickle.load(f)
            
            if current_time > cached_item["expiry"]:
                cache_file.unlink()
                cleared_count += 1
        except:
            # 如果文件损坏，直接删除
            cache_file.unlink(missing_ok=True)
            cleared_count += 1
    
    return cleared_count

def clear_all_cache():
    """清理所有缓存文件"""
    count = 0
    for cache_file in CACHE_DIR.glob("*.pkl"):
        cache_file.unlink(missing_ok=True)
        count += 1
    
    # 重置缓存统计信息
    if 'cache_stats' in st.session_state:
        st.session_state.cache_stats = {"total_entries": 0, "hit_count": 0, "miss_count": 0}
    
    return count

def extract_json_content(content):
    """增强的JSON提取函数，使用多种方法尝试从文本中提取有效的JSON"""
    
    # 方法1：直接尝试解析整个内容
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    
    # 方法2：尝试提取 ```json ... ``` 代码块中的内容
    try:
        code_block_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
        code_match = re.search(code_block_pattern, content)
        if code_match:
            json_content = code_match.group(1).strip()
            return json.loads(json_content)
    except json.JSONDecodeError:
        pass
    
    # 方法3：使用正则表达式查找 JSON 数组
    try:
        json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
        if json_match:
            json_content = json_match.group(0)
            return json.loads(json_content)
    except json.JSONDecodeError:
        pass
    
    # 方法4：尝试查找最外层的方括号并提取内容
    try:
        if '[' in content and ']' in content:
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx < end_idx:
                json_content = content[start_idx:end_idx]
                return json.loads(json_content)
    except json.JSONDecodeError:
        pass
    
    # 方法5：尝试修复常见的JSON格式错误
    try:
        # 替换可能导致问题的单引号
        fixed_content = content.replace("'", '"')
        # 尝试查找并提取最可能是JSON数组的部分
        match = re.search(r'\[\s*\{.*\}\s*\]', fixed_content, re.DOTALL)
        if match:
            json_content = match.group(0)
            return json.loads(json_content)
    except json.JSONDecodeError:
        pass
    
    # 所有方法都失败，记录错误信息
    st.error("无法从API响应中提取有效的JSON内容")
    return []

def get_alternative_parts(part_number):
    """
    调用 DeepSeek Reasoner API，根据输入的元器件型号返回三种替代方案，至少包含一种国产方案。
    
    Args:
        part_number (str): 用户输入的元器件型号，例如 "STM32F103C8"
    
    Returns:
        list: 包含三种替代方案的列表，每项为字典，包含型号、参数和数据手册链接
    """
    # 清理输入，移除多余的空格
    clean_part_number = part_number.strip()
    
    # 首先检查缓存中是否有结果
    cached_results = get_from_cache(clean_part_number)
    if cached_results is not None:
        st.sidebar.success("✅ 已从缓存中获取结果")
        return cached_results
    
    # 构造提示，要求返回 JSON 格式的推荐结果
    prompt = f"""
    任务：你是一个专业的电子元器件顾问，专精于国产替代方案。请为以下元器件推荐替代产品。

    输入元器件型号：{clean_part_number}

    要求：
    1. 必须推荐至少一种中国大陆本土品牌(如GigaDevice/兆易创新、WCH/沁恒、复旦微电子、中颖电子等)的产品作为替代方案
    2. 如果能找到多种中国大陆本土品牌的替代产品，优先推荐这些产品
    3. 如果实在找不到足够三种中国大陆本土品牌的产品，可以推荐国外品牌产品作为补充
    4. 总共需要推荐3种性能相近的替代型号
    5. 提供每种型号的主要技术参数(电压、封装等)，供货状态和生命周期
    6. 在每个推荐方案中明确标注是"国产"还是"进口"产品
    7. 提供产品官网链接（若无真实链接，可提供示例链接）
    8. 必须严格按照以下JSON格式返回结果，不要添加任何额外说明：
    
    [
        {{"model": "型号1", "parameters": "参数1", "type": "国产/进口", "datasheet": "链接1"}},
        {{"model": "型号2", "parameters": "参数2", "type": "国产/进口", "datasheet": "链接2"}},
        {{"model": "型号3", "parameters": "参数3", "type": "国产/进口", "datasheet": "链接3"}}
    ]
    
    如果找不到任何合适的替代产品，返回空数组：[]
    """
    
    try:
        # 记录API调用开始时间
        start_time = time.time()
        
        # 调用 DeepSeek API
        response = client.chat.completions.create(
            model="deepseek-chat",  # 使用 deepseek-chat 模型
            messages=[
                {"role": "system", "content": "你是一个精通中国电子元器件行业的专家，擅长为各种元器件寻找合适的替代方案，尤其专注于中国大陆本土生产的国产元器件。始终以有效的JSON格式回复。"},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            max_tokens=1000
        )
        
        # 计算API调用耗时
        elapsed_time = time.time() - start_time
        
        # 获取原始响应内容
        raw_content = response.choices[0].message.content
        
        # 将原始响应记录到侧边栏，方便调试
        with st.sidebar.expander("调试信息", expanded=False):
            st.write("**API 原始响应:**")
            st.code(raw_content, language="json")
            st.write(f"**API调用耗时:** {elapsed_time:.2f}秒")
        
        # 使用增强的JSON提取函数处理响应内容
        recommendations = extract_json_content(raw_content.strip())
        
        # 将结果保存到缓存
        save_to_cache(clean_part_number, recommendations)
        
        return recommendations
        
    except Exception as e:
        st.error(f"API 调用失败：{e}")
        st.sidebar.error(f"详细错误信息：{str(e)}")
        return []

# 添加批量查询处理函数
def process_batch_query(df, part_number_column, max_workers=3):
    """
    批量处理多个元器件型号，并返回结果DataFrame
    
    Args:
        df (pandas.DataFrame): 包含元器件型号的数据框
        part_number_column (str): 数据框中包含元器件型号的列名
        max_workers (int): 最大并行处理线程数
    
    Returns:
        pandas.DataFrame: 包含批量查询结果的数据框
    """
    # 检查列是否存在
    if part_number_column not in df.columns:
        st.error(f"未在上传的文件中找到列 '{part_number_column}'")
        return None
    
    # 获取所有元器件型号并去重
    part_numbers = df[part_number_column].astype(str).str.strip().dropna().unique()
    
    # 初始化结果
    results = []
    total_parts = len(part_numbers)
    
    # 创建进度条
    progress_bar = st.progress(0)
    progress_text = st.empty()
    progress_text.text(f"正在处理: 0/{total_parts} 完成...")
    
    # 定义处理单个元器件的函数
    def process_single_part(index, part):
        # 更新进度信息
        progress_text.text(f"正在处理: {index+1}/{total_parts} - 当前: {part}")
        
        # 查询替代方案
        alternatives = get_alternative_parts(part)
        
        # 将查询结果添加到列表中
        if alternatives and len(alternatives) > 0:
            for alt in alternatives:
                results.append({
                    "查询型号": part,
                    "替代型号": alt.get("model", "未知"),
                    "类型": alt.get("type", "未知"),
                    "参数": alt.get("parameters", ""),
                    "数据手册": alt.get("datasheet", "")
                })
        else:
            # 没有找到替代方案，仍然记录
            results.append({
                "查询型号": part,
                "替代型号": "未找到替代方案",
                "类型": "-",
                "参数": "-",
                "数据手册": "-"
            })
        
        # 更新进度条
        progress_bar.progress((index + 1) / total_parts)
    
    # 处理所有元器件型号
    for i, part in enumerate(part_numbers):
        process_single_part(i, part)
    
    # 将结果转换为DataFrame
    if results:
        result_df = pd.DataFrame(results)
        return result_df
    else:
        return None

# 用户反馈数据存储的函数
def save_feedback(part_number, feedback_score, feedback_text=""):
    """
    保存用户对查询结果的反馈
    
    Args:
        part_number (str): 查询的元器件型号
        feedback_score (int): 评分 (1-5)
        feedback_text (str): 用户的详细反馈意见
    """
    # 确保反馈目录存在
    FEEDBACK_DIR = Path("feedback")
    FEEDBACK_DIR.mkdir(exist_ok=True)
    
    feedback_data = {
        "part_number": part_number,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "score": feedback_score,
        "feedback_text": feedback_text
    }
    
    # 使用JSON格式存储反馈数据
    feedback_file = FEEDBACK_DIR / f"feedback_{datetime.now().strftime('%Y%m%d')}.json"
    
    # 读取现有反馈数据
    existing_feedback = []
    if feedback_file.exists():
        try:
            with open(feedback_file, 'r', encoding='utf-8') as f:
                existing_feedback = json.load(f)
        except json.JSONDecodeError:
            existing_feedback = []
    
    # 添加新的反馈
    existing_feedback.append(feedback_data)
    
    # 保存更新后的反馈数据
    with open(feedback_file, 'w', encoding='utf-8') as f:
        json.dump(existing_feedback, f, ensure_ascii=False, indent=2)
    
    # 更新反馈统计信息
    if 'feedback_stats' not in st.session_state:
        st.session_state.feedback_stats = {"total": 0, "avg_score": 0}
    
    st.session_state.feedback_stats["total"] += 1
    
    # 重新计算平均分数
    all_feedbacks = []
    for fb_file in FEEDBACK_DIR.glob("feedback_*.json"):
        try:
            with open(fb_file, 'r', encoding='utf-8') as f:
                all_feedbacks.extend(json.load(f))
        except:
            pass
    
    if all_feedbacks:
        avg_score = sum(fb["score"] for fb in all_feedbacks) / len(all_feedbacks)
        st.session_state.feedback_stats["avg_score"] = round(avg_score, 1)
        st.session_state.feedback_stats["total"] = len(all_feedbacks)

def get_feedback_stats():
    """获取反馈统计信息"""
    if 'feedback_stats' not in st.session_state:
        # 初始化反馈统计
        FEEDBACK_DIR = Path("feedback")
        FEEDBACK_DIR.mkdir(exist_ok=True)
        
        all_feedbacks = []
        for fb_file in FEEDBACK_DIR.glob("feedback_*.json"):
            try:
                with open(fb_file, 'r', encoding='utf-8') as f:
                    all_feedbacks.extend(json.load(f))
            except:
                pass
        
        if all_feedbacks:
            avg_score = sum(fb["score"] for fb in all_feedbacks) / len(all_feedbacks)
            st.session_state.feedback_stats = {
                "total": len(all_feedbacks),
                "avg_score": round(avg_score, 1)
            }
        else:
            st.session_state.feedback_stats = {"total": 0, "avg_score": 0}
    
    return st.session_state.feedback_stats

# 创建反馈界面组件
def render_feedback_ui(part_number, container=None):
    """
    渲染用户反馈界面
    
    Args:
        part_number (str): 元器件型号
        container: streamlit容器，如果为None则使用st
    """
    if container is None:
        container = st
    
    # 检查是否已经提交过反馈
    feedback_key = f"feedback_{part_number}"
    if feedback_key in st.session_state:
        container.success("✅ 感谢您的反馈!")
        return
    
    container.markdown("### 您对这些替代方案的满意度如何?")
    container.write("您的反馈将帮助我们改进查询质量和结果准确性")
    
    # 使用列布局放置评分按钮
    cols = container.columns(5)
    
    # 定义评分处理函数
    def submit_rating(score):
        st.session_state[feedback_key] = score
        save_feedback(part_number, score)
        st.experimental_rerun()
    
    # 创建评分按钮
    with cols[0]:
        if st.button("😞 很差", key=f"rating_1_{part_number}"):
            submit_rating(1)
    with cols[1]:
        if st.button("🙁 不满意", key=f"rating_2_{part_number}"):
            submit_rating(2)
    with cols[2]:
        if st.button("😐 一般", key=f"rating_3_{part_number}"):
            submit_rating(3)
    with cols[3]:
        if st.button("🙂 满意", key=f"rating_4_{part_number}"):
            submit_rating(4)
    with cols[4]:
        if st.button("😊 非常满意", key=f"rating_5_{part_number}"):
            submit_rating(5)
    
    # 添加详细反馈文本框
    feedback_text = container.text_area("您有什么具体的建议或意见吗?", key=f"feedback_text_{part_number}")
    
    if container.button("提交详细反馈", key=f"submit_feedback_{part_number}"):
        # 如果用户没有评分就直接提交文本反馈，默认为3分
        if feedback_key not in st.session_state:
            save_feedback(part_number, 3, feedback_text)
        else:
            save_feedback(part_number, st.session_state[feedback_key], feedback_text)
        st.session_state[feedback_key] = True
        st.experimental_rerun()

# Streamlit 界面
st.set_page_config(page_title="BOM 元器件国产替代推荐工具", layout="wide")

# 初始化反馈统计
feedback_stats = get_feedback_stats()

# 更新CSS样式，增强视觉效果
st.markdown("""
<style>
    /* 整体页面样式 */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* 标题样式改进 - 增大尺寸 */
    .main-header {
        font-size: 3.5rem;
        font-weight: 800;
        color: #1a73e8;
        text-align: center;
        padding: 1.8rem 0;
        margin-bottom: 1.5rem;
        background: linear-gradient(90deg, #1a73e8, #4285f4, #6c5ce7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
        line-height: 1.2;
        text-shadow: 0 4px 10px rgba(26, 115, 232, 0.1);
    }
    
    /* 添加标题装饰 */
    .header-container {
        position: relative;
        padding: 0 1rem;
        margin-bottom: 2rem;
    }
    
    .header-container::before, 
    .header-container::after {
        content: "";
        position: absolute;
        height: 3px;
        width: 60px;
        background: linear-gradient(90deg, #1a73e8, #6c5ce7);
        border-radius: 3px;
        left: 50%;
        transform: translateX(-50%);
    }
    
    .header-container::before {
        top: 10px;
        width: 100px;
    }
    
    .header-container::after {
        bottom: 5px;
        width: 200px;
    }
    
    /* 搜索区域样式改进 - 增大尺寸和显示度 */
    .search-area {
        background: linear-gradient(145deg, #ffffff, #f0f7ff);
        box-shadow: 0 10px 25px rgba(26, 115, 232, 0.15);
        padding: 3rem;
        border-radius: 1.2rem;
        margin-bottom: 2.5rem;
        border: 1px solid rgba(26, 115, 232, 0.1);
        max-width: 1000px;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* 修复搜索框和按钮容器 - 确保对齐 */
    .search-container {
        display: flex;
        align-items: stretch; /* 改为stretch确保高度一致 */
        gap: 20px;
    }
    
    /* 搜索框样式 - 增大尺寸并保证文字清晰可见 */
    .search-input {
        flex: 1;
    }
    
    /* 按钮容器样式 - 保证与输入框一致 */
    .search-button {
        width: 220px;
        min-width: 220px;
    }
    
    /* 输入框样式增强 - 确保文字清晰可见 */
    .stTextInput > div {
        margin-bottom: 0 !important;
    }
    
    /* 去除Streamlit默认的边距 */
    .stTextInput {
        margin-bottom: 0 !important;
    }
    
    .stTextInput > div > div {
        margin-bottom: 0 !important;
    }
    
    /* 完全自定义输入框样式，增加高度和改进字体显示 */
    .stTextInput > div > div > input {
        border-radius: 0.8rem;
        border: 2px solid #b3d1ff;
        padding: 0.8rem 1.2rem; /* 增加上下内边距 */
        font-size: 1.4rem; /* 稍微调整字体大小 */
        height: 90px; /* 再次增加高度以确保足够空间 */
        box-shadow: 0 6px 15px rgba(26, 115, 232, 0.12);
        color: #333333;
        background-color: white;
        width: 100%;
        line-height: 1.5; /* 设置合理的行高 */
        margin-top: 5px;
        margin-bottom: 5px;
        overflow: visible; /* 确保文本不被截断 */
        white-space: normal; /* 允许文本换行 */
        text-overflow: initial; /* 不使用省略号 */
        display: block; /* 确保元素完全显示 */
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #1a73e8;
        box-shadow: 0 0 0 4px rgba(26, 115, 232, 0.2);
    }
    
    .stTextInput > div > div > input::placeholder {
        color: #8c9bb5;
        opacity: 0.8;
        font-size: 1.3rem; /* 调整占位符文字大小 */
        position: relative; /* 确保占位符在适当位置 */
        top: 0; /* 避免占位符位置偏移 */
    }
    
    /* 移除输入框的标签 */
    .stTextInput > label {
        display: none !important;
    }
    
    /* 输入框容器调整 - 防止截断 */
    .stTextInput > div {
        padding: 3px 0; /* 为容器添加内边距 */
        overflow: visible !important; /* 确保不会截断内容 */
    }
    
    /* 按钮样式 - 确保与输入框完全匹配 */
    .stButton {
        height: 90px; /* 与更新后的输入框高度匹配 */
        margin-bottom: 0 !important;
        margin-top: 5px;
    }
    
    .stButton > button {
        border-radius: 0.8rem;
        font-weight: 600;
        font-size: 1.3rem;
        border: none;
        background: linear-gradient(90deg, #1a73e8, #4285f4);
        color: white;
        transition: all 0.3s;
        height: 90px; /* 与输入框高度匹配 */
        width: 100%;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    /* 结果卡片样式升级 */
    .result-card {
        padding: 1.8rem;
        border-radius: 1rem;
        height: 100%;
        box-shadow: 0 10px 25px rgba(0,0,0,0.07);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
        background: linear-gradient(145deg, #ffffff, #f0f7ff);
        border-left: 5px solid #1a73e8;
    }
    
    .result-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 30px rgba(26, 115, 232, 0.15);
    }
    
    /* 统一使用蓝白配色 */
    .result-card::before {
        content: "";
        position: absolute;
        top: -2px;
        right: -2px;
        bottom: -2px;
        width: 7px;
        background: linear-gradient(to bottom, #1a73e8, #80d8ff);
        border-radius: 0 5px 5px 0;
        opacity: 0.7;
    }
    
    /* 标签改进 */
    .chip-type {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 2rem;
        font-weight: 500;
        font-size: 0.9rem;
        box-shadow: 0 2px 5px rgba(26, 115, 232, 0.2);
        margin-bottom: 0.8rem;
        background: linear-gradient(90deg, #1a73e8, #4fc3f7);
        color: white;
    }
    
    /* 卡片内部标题 */
    .result-card h3 {
        font-size: 1.2rem;
        color: #1a73e8;
        margin-bottom: 0.5rem;
    }
    
    .result-card h2 {
        font-size: 1.8rem;
        font-weight: 600;
        margin: 0.7rem 0 1rem 0;
        color: #2c3e50;
    }
    
    /* 参数样式 */
    .param-label {
        font-weight: 600;
        color: #1a73e8;
        display: inline-block;
        margin-bottom: 0.5rem;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 0.2rem;
    }
    
    /* 历史记录样式 - 增加上边距 */
    .history-area {
        background: linear-gradient(145deg, #ffffff, #f0f7ff);
        padding: 1.2rem;
        border-radius: 0.8rem;
        margin-top: 3rem; /* 增加上边距，将历史记录区域下移 */
        box-shadow: 0 4px 10px rgba(26, 115, 232, 0.07);
        max-width: 900px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .history-item {
        padding: 0.6rem 1rem;
        margin: 0.4rem 0;
        background: linear-gradient(145deg, #ffffff, #f5f5f5);
        border-radius: 0.5rem;
        cursor: pointer;
        transition: all 0.2s;
        border-left: 3px solid #1a73e8;
    }
    
    .history-item:hover {
        background: linear-gradient(145deg, #f5f5f5, #e6f3ff);
        transform: translateX(5px);
    }
    
    /* 页脚样式 - 降低显示度 */
    .footer-text {
        color: #9e9e9e;
        font-size: 0.85rem;
        text-align: center;
        padding: 1rem 0;
    }
    
    /* 调整结果区域样式 */
    .results-container {
        max-width: 1100px;
        margin: 0 auto 2rem auto;
    }
    
    /* 隐藏Streamlit默认的元素 */
    .css-1544g2n.e1tzin5v3 {
        padding-top: 0 !important;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .stExpander {
        border: none !important;
        box-shadow: none !important;
    }
</style>
""", unsafe_allow_html=True)

# 使用容器包裹标题，以应用额外样式
st.markdown('<div class="header-container">', unsafe_allow_html=True)
st.markdown('<h1 class="main-header">BOM 元器件国产替代推荐工具</h1>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 搜索区域 - 修改结构，确保输入框和按钮完全匹配
with st.container():
    st.markdown('<div class="search-area">', unsafe_allow_html=True)
    
    # 使用选项卡分离单个查询和批量查询功能
    tab1, tab2 = st.tabs(["单个查询", "批量查询"])
    
    with tab1:
        st.markdown('<div class="search-container">', unsafe_allow_html=True)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown('<div class="search-input">', unsafe_allow_html=True)
            part_number = st.text_input("", placeholder="输入元器件型号，例如：STM32F103C8", label_visibility="collapsed")
            st.markdown('</div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="search-button">', unsafe_allow_html=True)
            search_button = st.button("🔍 查询替代方案", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown("<h3>批量查询元器件替代方案</h3>", unsafe_allow_html=True)
        
        # 上传文件说明
        st.write("上传包含元器件型号的Excel或CSV文件，系统将自动为每个型号查询替代方案。")
        
        # 文件上传控件
        uploaded_file = st.file_uploader("选择Excel或CSV文件", type=["xlsx", "xls", "csv"])
        
        if uploaded_file is not None:
            try:
                # 根据文件类型读取数据
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                # 显示上传的数据表格预览
                st.write("文件预览:")
                st.dataframe(df.head(5))
                
                # 选择包含元器件型号的列
                column_options = df.columns.tolist()
                selected_column = st.selectbox("请选择包含元器件型号的列", column_options)
                
                # 批量查询按钮
                batch_button = st.button("开始批量查询", use_container_width=True, key="batch_query_button")
                
                if batch_button:
                    # 处理批量查询
                    with st.spinner("正在批量处理元器件查询，请稍候..."):
                        result_df = process_batch_query(df, selected_column)
                        
                        if result_df is not None and not result_df.empty:
                            # 保存结果到会话状态便于导出
                            st.session_state.batch_results = result_df
                            
                            # 显示查询结果
                            st.success(f"✅ 查询完成! 共为 {len(df[selected_column].dropna().unique())} 个型号查询了替代方案")
                            
                            # 显示汇总统计
                            found_count = result_df[result_df["替代型号"] != "未找到替代方案"].shape[0]
                            st.write(f"- 找到替代方案的型号数量: {found_count}")
                            st.write(f"- 总替代方案数量: {result_df.shape[0]}")
                            domestic_count = result_df[result_df["类型"].str.contains("国产", na=False)].shape[0]
                            st.write(f"- 国产替代方案数量: {domestic_count}")
                            
                            # 显示结果表格
                            st.subheader("查询结果")
                            st.dataframe(result_df)
                            
                            # 提供CSV/Excel导出选项
                            col1, col2 = st.columns(2)
                            with col1:
                                csv = result_df.to_csv(index=False).encode('utf-8')
                                st.download_button(
                                    label="📥 下载CSV格式",
                                    data=csv,
                                    file_name=f"元器件替代方案查询结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv",
                                )
                            
                            with col2:
                                output = io.BytesIO()
                                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                    result_df.to_excel(writer, index=False, sheet_name='元器件替代方案')
                                excel_data = output.getvalue()
                                st.download_button(
                                    label="📥 下载Excel格式",
                                    data=excel_data,
                                    file_name=f"元器件替代方案查询结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                                    mime="application/vnd.ms-excel"
                                )
                        else:
                            st.error("批量查询未返回任何结果，请检查元器件型号列是否正确。")
                
            except Exception as e:
                st.error(f"处理文件时出错: {str(e)}")
                st.info("请确保上传的是有效的Excel或CSV文件，并且含有元器件型号列。")
        
        # 使用说明
        with st.expander("批量查询使用说明"):
            st.markdown("""
            ### 批量查询使用说明
            
            1. **准备文件**：创建Excel或CSV文件，其中包含需要查询的元器件型号列表
            2. **上传文件**：使用上方的上传按钮选择文件
            3. **选择列**：在下拉菜单中选择包含元器件型号的列名
            4. **开始查询**：点击"开始批量查询"按钮，系统将处理所有型号
            5. **查看结果**：处理完成后，可以查看结果表格并下载
            
            **注意**：
            - 批量查询可能需要较长时间，请耐心等待
            - 查询速度受API限制，系统会自动进行缓存以提高效率
            - 对于未找到替代方案的型号，将显示"未找到替代方案"
            """)
    
    st.markdown('</div>', unsafe_allow_html=True)

# 在此处添加历史查询功能
if 'search_history' not in st.session_state:
    st.session_state.search_history = []

# 查询按钮逻辑
if search_button:
    if not part_number:
        st.error("⚠️ 请输入元器件型号！")
    else:
        with st.spinner(f"🔄 正在查询 {part_number} 的国产替代方案..."):
            # 调用 API 获取替代方案
            recommendations = get_alternative_parts(part_number)
            
            # 保存到历史记录
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.search_history.append({
                "timestamp": timestamp,
                "part_number": part_number,
                "recommendations": recommendations
            })
            
            # 结果区域添加容器
            st.markdown('<div class="results-container">', unsafe_allow_html=True)
            
            if recommendations:
                st.success(f"✅ 已为 **{part_number}** 找到 {len(recommendations)} 种替代方案")
                
                # 创建三列布局
                cols = st.columns(min(3, len(recommendations)))
                
                # 在每列中填充一个方案
                for i, (col, rec) in enumerate(zip(cols, recommendations[:3]), 1):
                    with col:
                        st.markdown(f"""
                        <div class="result-card">
                            <h3>方案 {i}</h3>
                            <span class="chip-type">📋 {rec.get('type', '未知')}</span>
                            <h2>{rec['model']}</h2>
                            <p><span class="param-label">参数：</span><br>{rec['parameters']}</p>
                            <p><a href="{rec['datasheet']}" target="_blank">📄 查看数据手册</a></p>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div class="no-result-box">
                    <h3>😔 未找到合适的替代方案</h3>
                    <p>请尝试修改搜索关键词或查询其他型号</p>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 添加反馈界面
            st.markdown("---")
            render_feedback_ui(part_number)

# 添加历史记录展示区 - 减小尺寸
with st.expander("📜 历史查询记录", expanded=False):
    st.markdown('<div class="history-area">', unsafe_allow_html=True)
    
    # 历史记录标题和清除按钮
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("您的历史查询")
    with col2:
        if st.button("🗑️ 清除", key="clear_history") and len(st.session_state.search_history) > 0:
            st.session_state.search_history = []
            st.experimental_rerun()
    
    # 显示历史记录
    if not st.session_state.search_history:
        st.info("暂无历史查询记录")
    else:
        for idx, history_item in enumerate(reversed(st.session_state.search_history)):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"""
                <div class="history-item">
                    <div class="history-header">
                        <b>🔍 {history_item['part_number']}</b>
                        <span class="timestamp">{history_item['timestamp']}</span>
                    </div>
                    <div>找到 {len(history_item['recommendations'])} 种替代方案</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                if st.button(f"查看", key=f"view_history_{idx}"):
                    st.session_state.selected_history = history_item
                    st.experimental_rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# 显示选中的历史记录
if 'selected_history' in st.session_state:
    st.markdown("---")
    history_part_number = st.session_state.selected_history['part_number']
    st.subheader(f"历史查询结果: {history_part_number}")
    st.caption(f"查询时间: {st.session_state.selected_history['timestamp']}")
    
    # 使用与原始查询相同的显示逻辑
    recommendations = st.session_state.selected_history['recommendations']
    
    # 结果区域添加容器
    st.markdown('<div class="results-container">', unsafe_allow_html=True)
    
    if recommendations:
        # 创建三列布局
        cols = st.columns(min(3, len(recommendations)))
        
        # 在每列中填充一个方案
        for i, (col, rec) in enumerate(zip(cols, recommendations[:3]), 1):
            with col:
                st.markdown(f"""
                <div class="result-card">
                    <h3>方案 {i}</h3>
                    <span class="chip-type">📋 {rec.get('type', '未知')}</span>
                    <h2>{rec['model']}</h2>
                    <p><span class="param-label">参数：</span><br>{rec['parameters']}</p>
                    <p><a href="{rec['datasheet']}" target="_blank">📄 查看数据手册</a></p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="no-result-box">
            <h3>😔 未找到合适的替代方案</h3>
            <p>请尝试修改搜索关键词或查询其他型号</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 添加反馈界面
    st.markdown("---")
    render_feedback_ui(history_part_number)
    
    if st.button("返回"):
        del st.session_state.selected_history
        st.experimental_rerun()

# 添加页脚信息 - 降低显示度
st.markdown("---")
st.markdown('<p class="footer-text">💡 本工具基于深度学习模型，提供元器件替代参考，实际使用请结合专业工程师评估</p>', unsafe_allow_html=True)