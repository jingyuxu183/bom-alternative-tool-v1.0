import streamlit as st
from openai import OpenAI
import json
import re
from datetime import datetime
import os
from dotenv import load_dotenv

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
    # 构造提示，要求返回 JSON 格式的推荐结果
    prompt = f"""
    任务：你是一个专业的电子元器件顾问，专精于国产替代方案。请为以下元器件推荐替代产品。

    输入元器件型号：{part_number}

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
        
        # 获取原始响应内容
        raw_content = response.choices[0].message.content
        
        # 将原始响应记录到侧边栏，方便调试
        with st.sidebar.expander("调试信息", expanded=False):
            st.write("**API 原始响应:**")
            st.code(raw_content, language="json")
        
        # 使用增强的JSON提取函数处理响应内容
        recommendations = extract_json_content(raw_content.strip())
        return recommendations
        
    except Exception as e:
        st.error(f"API 调用失败：{e}")
        st.sidebar.error(f"详细错误信息：{str(e)}")
        return []

# Streamlit 界面
st.set_page_config(page_title="BOM 元器件国产替代推荐工具", layout="wide")

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
    
    /* 完全自定义输入框样式 */
    .stTextInput > div > div > input {
        border-radius: 0.8rem;
        border: 2px solid #b3d1ff;
        padding: 0 1.2rem;
        font-size: 1.3rem;
        height: 65px; /* 增加高度从60px到65px */
        box-shadow: 0 6px 15px rgba(26, 115, 232, 0.12);
        color: #333333;
        background-color: white;
        width: 100%;
        line-height: 65px; /* 与高度匹配确保垂直居中 */
        margin-top: 5px; /* 添加顶部间距 */
        margin-bottom: 5px; /* 添加底部间距 */
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #1a73e8;
        box-shadow: 0 0 0 4px rgba(26, 115, 232, 0.2);
    }
    
    .stTextInput > div > div > input::placeholder {
        color: #8c9bb5;
        opacity: 0.8;
        font-size: 1.2rem; /* 调整占位符文字大小 */
    }
    
    /* 移除输入框的标签 */
    .stTextInput > label {
        display: none !important;
    }
    
    /* 输入框容器调整 */
    .stTextInput > div {
        padding: 3px 0; /* 为容器添加内边距 */
    }
    
    /* 按钮样式 - 确保与输入框完全匹配 */
    .stButton {
        height: 65px; /* 与输入框相同的固定高度 */
        margin-bottom: 0 !important;
        margin-top: 5px; /* 添加顶部间距 */
    }
    
    .stButton > button {
        border-radius: 0.8rem;
        font-weight: 600;
        font-size: 1.3rem;
        border: none;
        background: linear-gradient(90deg, #1a73e8, #4285f4);
        color: white;
        transition: all 0.3s;
        height: 65px; /* 固定高度与输入框一致 */
        width: 100%;
        padding: 0;
        line-height: 65px; /* 确保文字垂直居中 */
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
    
    /* 历史记录样式 - 减小尺寸 */
    .history-area {
        background: linear-gradient(145deg, #ffffff, #f0f7ff);
        padding: 1.2rem;
        border-radius: 0.8rem;
        margin-top: 1.5rem;
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
    st.subheader(f"历史查询结果: {st.session_state.selected_history['part_number']}")
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
    
    if st.button("返回"):
        del st.session_state.selected_history
        st.experimental_rerun()

# 添加页脚信息 - 降低显示度
st.markdown("---")
st.markdown('<p class="footer-text">💡 本工具基于深度学习模型，提供元器件替代参考，实际使用请结合专业工程师评估</p>', unsafe_allow_html=True)