import streamlit as st
from datetime import datetime
import time
import pandas as pd
import tempfile  # 添加tempfile导入，用于创建临时文件

def render_ui(get_alternative_parts_func):
    # Streamlit 界面 - 确保 set_page_config 是第一个Streamlit命令
    st.set_page_config(page_title="BOM 元器件国产替代推荐工具", layout="wide")
    
    # 初始化会话状态变量，用于处理回车键事件
    if 'search_triggered' not in st.session_state:
        st.session_state.search_triggered = False
    
    # 初始化AI对话相关的状态 - 使用一个简单的布尔值控制对话框显示
    if 'show_chat' not in st.session_state:
        st.session_state.show_chat = False
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
        
    # 处理回车键的回调函数
    def handle_enter_press():
        if st.session_state.part_number_input:  # 检查输入框是否有内容
            st.session_state.search_triggered = True
    
    # 更新CSS样式，精简和优化AI对话部分的样式
    st.markdown("""
    <style>
        /* 整体页面样式 */
        .stApp {
            background-color: #f8f9fa;
        }
        
        /* 标题样式改进 - 减小尺寸和边距 */
        .main-header {
            font-size: 2.5rem; /* 减小字体大小 */
            font-weight: 800;
            color: #1a73e8;
            text-align: center;
            padding: 1rem 0; /* 减小内边距 */
            margin-bottom: 1rem; /* 减小底部外边距 */
            background: linear-gradient(90deg, #1a73e8, #4285f4, #6c5ce7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
            line-height: 1.2;
            text-shadow: 0 4px 10px rgba(26, 115, 232, 0.1);
        }
        
        /* 添加标题装饰 - 减小装饰条尺寸 */
        .header-container {
            position: relative;
            padding: 0 1rem;
            margin-bottom: 1rem; /* 减小底部外边距 */
        }
        
        .header-container::before, 
        .header-container::after {
            content: "";
            position: absolute;
            height: 2px; /* 减小高度 */
            width: 60px;
            background: linear-gradient(90deg, #1a73e8, #6c5ce7);
            border-radius: 3px;
            left: 50%;
            transform: translateX(-50%);
        }
        
        .header-container::before {
            top: 5px; /* 减小距离 */
            width: 80px; /* 减小宽度 */
        }
        
        .header-container::after {
            bottom: 2px; /* 减小距离 */
            width: 160px; /* 减小宽度 */
        }
        
        /* 搜索区域样式改进 - 减小内边距 */
        .search-area {
            background: linear-gradient(145deg, #ffffff, #f0f7ff);
            box-shadow: 0 8px 20px rgba(26, 115, 232, 0.15);
            padding: 1.2rem; /* 减小内边距 */
            border-radius: 1rem;
            margin-bottom: 1.5rem; /* 减小底部外边距 */
            border: 1px solid rgba(26, 115, 232, 0.1);
            max-width: 1000px;
            margin-left: auto;
            margin-right: auto;
            display: flex;
            align-items: center;
        }
        
        /* 修复搜索框和按钮容器 - 确保对齐 */
        .search-container {
            display: flex;
            align-items: center; /* 保持垂直居中 */
            gap: 20px;
            margin: 0; /* 确保没有外边距 */
            padding: 0; /* 确保没有内边距 */
            width: 100%; /* 确保容器宽度充满 */
        }
        
        /* 输入框和按钮容器共享的基本样式 */
        .search-input, .search-button {
            height: 65px;
            display: flex;
            align-items: center;
        }
        
        /* 搜索框样式 */
        .search-input {
            flex: 1;
        }
        
        /* 按钮容器样式 */
        .search-button {
            width: 220px;
            min-width: 220px;
        }
        
        /* streamlit 列的调整 - 确保所有列完全对齐 */
        div.css-1r6slb0.e1tzin5v2, div.css-keje6w.e1tzin5v2 {  /* 输入框和按钮所在列 */
            padding: 0 !important; 
            margin: 0 !important;
            display: flex !important;
            align-items: center !important;
        }
        
        /* 强制所有列的子元素拉伸填充 */
        div.css-1r6slb0.e1tzin5v2 > *, div.css-keje6w.e1tzin5v2 > * {
            width: 100%;
            margin: 0 !important;
            padding: 0 !重要;
        }
        
        /* 输入框容器调整 */
        .stTextInput {
            margin: 0 !important;
            padding: 0 !important;
        }
        
        .stTextInput > div {
            padding: 0 !important; /* 强制移除容器内边距 */
            margin: 0 !important; /* 强制移除容器外边距 */
            height: 65px; /* 明确设置高度 */
        }
        
        .stTextInput > div > div {
            margin: 0 !important;
            padding: 0 !important;
            height: 100%; /* 填充父容器 */
        }
        
        /* 完全自定义输入框样式 */
        .stTextInput > div > div > input {
            border-radius: 0.8rem;
            border: 2px solid #b3d1ff;
            padding: 0 1.2rem;
            font-size: 1.5rem;
            height: 65px; /* 输入框高度 */
            box-shadow: 0 6px 15px rgba(26, 115, 232, 0.12);
            color: #333333;
            background-color: white;
            width: 100%;
            box-sizing: border-box !important; /* 确保边框包含在高度内 */
            margin: 0 !important;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #1a73e8;
            box-shadow: 0 0 0 4px rgba(26, 115, 232, 0.2);
        }
        
        .stTextInput > div > div > input::placeholder {
            color: #8c9bb5;
            opacity: 0.8;
            font-size: 1.5rem; /* 与输入文字大小保持一致 */
            line-height: normal;
        }
        
        /* 移除输入框的标签 */
        .stTextInput > label {
            display: none !重要;
        }
        
        /* 输入框容器调整 */
        .stTextInput > div {
            padding: 3px 0; /* 为容器添加内边距 */
        }
        
        /* 按钮容器样式 - 保证与输入框一致 */
        .search-button {
            width: 220px;
            min-width: 220px; 
            height: 65px; /* 确保与输入框高度一致 */
            display: flex;
            align-items: center;
        }
        
        /* 按钮样式 - 确保与输入框完全匹配 */
        .stButton {
            height: 65px; /* 与输入框相同的固定高度 */
            margin-bottom: 0 !important;
            margin-top: 0; /* 移除顶部间距 */
        }
        
        .stButton > button {
            border-radius: 0.8rem;
            font-weight: 600;
            font-size: 1.5rem; /* 调整字体大小与输入框一致 */
            border: none;
            background: linear-gradient(90deg, #1a73e8, #4285f4);
            color: white;
            transition: all 0.3s;
            height: 65px; /* 固定高度与输入框一致 */
            width: 100%;
            padding: 0 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box !重要; /* 确保边框包含在高度内 */
        }
        
        /* 修复按钮和输入框的列对齐 */
        div[data-testid="column"] {
            padding: 0 !important;
            display: flex !important;
            align-items: center !重要;
        }
        
        /* 确保每个列子元素垂直居中且不溢出 */
        div[data-testid="column"] > div {
            width: 100%;
            display: flex;
            align-items: center;
            padding: 0 !important;
            margin: 0 !重要;
        }
        
        /* 新的结果卡片样式 - 调整大小更紧凑 */
        .result-card {
            padding: 1.2rem; /* 减小内边距 */
            border-radius: 0.8rem;
            height: 100%; /* 保持高度一致 */
            box-shadow: 0 8px 20px rgba(0,0,0,0.07);
            transition: all 0.3s ease;
            position: relative;
            background: linear-gradient(145deg, #ffffff, #f0f7ff);
            border-left: 5px solid #1a73e8;
            display: flex;
            flex-direction: column;
            gap: 0.4rem; /* 减小间距 */
        }
        
        .result-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 25px rgba(26, 115, 232, 0.15);
        }
        
        .result-card::before {
            content: "";
            position: absolute;
            top: -2px;
            right: -2px;
            bottom: -2px;
            width: 5px;
            background: linear-gradient(to bottom, #1a73e8, #80d8ff);
            border-radius: 0 5px 5px 0;
            opacity: 0.7;
        }
        
        /* 方案编号样式 - 减小尺寸 */
        .solution-number {
            font-size: 1rem;
            font-weight: 600;
            color: #1a73e8;
            margin-bottom: 0.2rem; /* 减小底部外边距 */
        }
        
        /* 国产/进口标签样式 - 减小尺寸 */
        .type-badge {
            display: inline-block;
            padding: 0.2rem 0.6rem; /* 减小内边距 */
            border-radius: 1.5rem;
            font-weight: 500;
            font-size: 0.85rem; /* 减小字体大小 */
            box-shadow: 0 2px 4px rgba(26, 115, 232, 0.2);
            margin-bottom: 0.5rem; /* 减小底部外边距 */
            background: linear-gradient(90deg, #1a73e8, #4fc3f7);
            color: white;
            align-self: flex-start;
        }
        
        /* 元器件型号和品牌标题 - 减小尺寸 */
        .model-title {
            font-size: 1.3rem; /* 减小字体大小 */
            font-weight: 600;
            margin: 0.3rem 0; /* 减小外边距 */
            color: #2c3e50;
            line-height: 1.3;
        }
        
        /* 信息行样式 - 减小尺寸 */
        .info-row {
            display: flex;
            margin-bottom: 0.4rem; /* 减小底部外边距 */
            line-height: 1.4;
        }
        
        .info-label {
            font-weight: 600;
            color: #546e7a;
            min-width: 3rem; /* 减小宽度 */
            flex-shrink: 0;
        }
        
        .info-value {
            color: #37474f;
            flex: 1;
        }
        
        /* 参数行特殊样式 - 确保文本完整显示 */
        .parameters {
            border-top: 1px dashed #e0e0e0;
            padding-top: 0.5rem; /* 减小顶部内边距 */
            margin-top: 0.2rem; /* 减小顶部外边距 */
            flex-direction: column;
            flex-grow: 1; /* 让参数部分可以灵活扩展 */
        }
        
        .parameters .info-label {
            margin-bottom: 0.3rem; /* 减小底部外边距 */
        }
        
        .parameters .info-value {
            background-color: #f5f7fa;
            padding: 0.5rem; /* 减小内边距 */
            border-radius: 0.4rem;
            border-left: 3px solid #1a73e8;
            font-size: 0.9rem; /* 减小字体大小 */
            white-space: normal;
            word-break: break-word;
            overflow-wrap: break-word;
            height: auto;
            max-height: none; /* 不限制高度 */
            overflow-y: visible; /* 保证内容可见 */
        }
        
        /* 数据手册链接样式 - 减小尺寸 */
        .card-footer {
            margin-top: 0.5rem; /* 减小顶部外边距 */
            padding-top: 0.5rem; /* 减小顶部内边距 */
        }
        
        .datasheet-link {
            display: inline-block;
            color: #1a73e8;
            text-decoration: none;
            font-weight: 500;
            padding: 0.4rem 0.8rem; /* 减小内边距 */
            background: rgba(26, 115, 232, 0.1);
            border-radius: 0.4rem;
            transition: all 0.2s;
            font-size: 0.9rem; /* 减小字体大小 */
        }
        
        .datasheet-link:hover {
            background: rgba(26, 115, 232, 0.2);
            text-decoration: none;
        }
        
        /* 历史记录样式 - 减小尺寸 */
        .history-area {
            background: linear-gradient(145deg, #ffffff, #f0f7ff);
            padding: 1rem; /* 减小内边距 */
            border-radius: 0.8rem;
            margin-top: 1rem; /* 减小顶部外边距 */
            box-shadow: 0 4px 8px rgba(26, 115, 232, 0.07);
            max-width: 900px;
            margin-left: auto;
            margin-right: auto;
        }
        
        .history-item {
            padding: 0.5rem 0.8rem; /* 减小内边距 */
            margin: 0.3rem 0; /* 减小外边距 */
            background: linear-gradient(145deg, #ffffff, #f5f5f5);
            border-radius: 0.4rem;
            cursor: pointer;
            transition: all 0.2s;
            border-left: 3px solid #1a73e8;
        }
        
        .history-item:hover {
            background: linear-gradient(145deg, #f5f5f5, #e6f3ff);
            transform: translateX(5px);
        }
        
        /* 页脚样式 - 减小尺寸 */
        .footer-text {
            color: #9e9e9e;
            font-size: 0.8rem; /* 减小字体大小 */
            text-align: center;
            padding: 0.8rem 0; /* 减小内边距 */
        }
        
        /* 调整结果区域样式 */
        .results-container {
            max-width: 1100px;
            margin: 0 auto 1.5rem auto; /* 减小底部外边距 */
            margin-top: 0.5rem !important; /* 减少顶部边距 */
        }
        
        /* 警告框样式 - 减小尺寸 */
        .no-result-box {
            background-color: #fff3cd;
            padding: 1.5rem; /* 减小内边距 */
            border-radius: 0.8rem;
            text-align: center;
            margin: 0.8rem auto; /* 减小外边距 */
            max-width: 800px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        }
        
        /* 隐藏Streamlit默认的元素 */
        .css-1544g2n.e1tzin5v3 {
            padding-top: 0 !important;
        }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        .stExpander {
            border: none !important;
            box-shadow: none !重要;
        }
        
        /* 修复streamlit列对齐问题 */
        div[data-testid="column"] {
            padding: 0 !important;
            margin: 0 !important;
            display: flex !important;
            align-items: stretch !重要; /* 确保列拉伸以匹配高度 */
            height: 100% !重要;
        }
        
        div[data-testid="column"] > div {
            width: 100%;
            padding: 0.3rem !重要; /* 添加小间距 */
            box-sizing: border-box;
        }
        
        /* 确保所有卡片等高 */
        div[data-testid="stHorizontalBlock"] {
            align-items: stretch !重要; /* 确保块内元素拉伸 */
            display: flex !重要;
        }
        
        /* 标签页样式调整 - 减少空间占用 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 30px !important; /* 增加标签页之间的间距 */
            margin-bottom: 10px;
        }
        
        .stTabs [data-baseweb="tab"] {
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
            font-weight: 600; /* 增加字体粗细 */
        }
        
        .stTabs [data-baseweb="tab-panel"] {
            padding-top: 1rem;
        }
        
        /* 减少tab内部元素的间距 */
        .stTabs [data-baseweb="tab-panel"] > div > div {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }
        
        /* 减少整体页面的内边距 */
        .block-container {
            padding-top: 1rem !重要;
            padding-bottom: 1rem !重要;
            max-width: 1200px;
            padding-left: 1.5rem !重要;
            padding-right: 1.5rem !重要;
        }
        
        /* 减少standard垂直间距 */
        .css-1kyxreq {
            margin-top: 0.5rem !重要;
            margin-bottom: 0.5rem !重要;
        }
        
        /* 为Streamlit的elements减少垂直间距 */
        .stButton, .stTextInput, .stSelectbox, .stFileUploader {
            margin-bottom: 0.5rem;
        }
        
        /* 确保卡片等高和宽度一致 */
        .result-card {
            padding: 1.2rem;
            border-radius: 0.8rem;
            height: 100% !重要; /* 强制相同高度 */
            min-height: 450px; /* 墛大最小高度 */
            max-height: 450px; /* 墛大最大高度 */
            box-shadow: 0 8px 20px rgba(0,0,0,0.07);
            transition: all 0.3s ease;
            position: relative;
            background: linear-gradient(145deg, #ffffff, #f0f7ff);
            border-left: 5px solid #1a73e8;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            overflow: auto; /* 允许内容超出时滚动 */
        }
        
        /* 让卡片容器也保持等高 */
        div.css-1r6slb0.e1tzin5v2 {
            height: 100% !重要;
        }
        
        /* 确保列也是等高的 */
        div[data-testid="column"] {
            height: 450px !重要; /* 与卡片高度保持一致 */
            padding: 0.3rem !重要;
        }
        
        /* 确保行容器也是等高的 */
        div[data-testid="stHorizontalBlock"] {
            height: 450px !重要; /* 与卡片高度保持一致 */
            margin-bottom: 1rem;
        }
        
        /* 参数行特殊样式 - 确保内容在固定高度内可滚动 */
        .parameters {
            border-top: 1px dashed #e0e0e0;
            padding-top: 0.5rem;
            margin-top: 0.2rem;
            flex-direction: column;
            flex-grow: 1;
            max-height: 150px; /* 限制参数部分的最大高度 */
            overflow-y: auto; /* 内容多时可滚动 */
        }
        
        .parameters .info-value {
            background-color: #f5f7fa;
            padding: 0.5rem;
            border-radius: 0.4rem;
            border-left: 3px solid #1a73e8;
            font-size: 0.9rem;
            white-space: normal;
            word-break: break-word;
            overflow-wrap: break-word;
        }
        
        /* 自定义滚动条样式 */
        .parameters::-webkit-scrollbar {
            width: 4px;
        }
        
        .parameters::-webkit-scrollbar-thumb {
            background-color: rgba(26, 115, 232, 0.3);
            border-radius: 4px;
        }
        
        .parameters::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.05);
        }
        
        /* 确保卡片内部内容不会撑开卡片 */
        .model-title {
            font-size: 1.3rem;
            font-weight: 600;
            margin: 0.3rem 0;
            color: #2c3e50;
            line-height: 1.3;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        /* 调整标签页间距 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 30px !important;
            margin-bottom: 10px;
        }
        
        /* 减小成功消息与搜索框之间的距离 */
        .st-emotion-cache-16idsys p {
            margin-top: -5px !important;  /* 减小顶部边距 */
            padding-top: 5px !重要;
            padding-bottom: 5px !重要;
        }
        
        /* 成功框样式 */
        .success-box {
            margin-top: 0.5rem !重要;
            margin-bottom: 0.5rem !重要;
            padding: 0.5rem !重要;
        }
        
        /* 确保卡片尺寸更大 */
        .result-card {
            padding: 1.2rem;
            border-radius: 0.8rem;
            height: 100% !重要;
            min-height: 450px; /* 墛大最小高度 */
            max-height: 450px; /* 墛大最大高度 */
            box-shadow: 0 8px 20px rgba(0,0,0,0.07);
            transition: all 0.3s ease;
            position: relative;
            background: linear-gradient(145deg, #ffffff, #f0f7ff);
            border-left: 5px solid #1a73e8;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            overflow: auto;
        }
        
        /* 让卡片容器也保持等高 */
        div.css-1r6slb0.e1tzin5v2 {
            height: 100% !重要;
        }
        
        /* 确保列也是等高的 */
        div[data-testid="column"] {
            height: 450px !重要; /* 与卡片高度保持一致 */
            padding: 0.3rem !重要;
        }
        
        /* 确保行容器也是等高的 */
        div[data-testid="stHorizontalBlock"] {
            height: 450px !重要; /* 与卡片高度保持一致 */
            margin-bottom: 1rem;
        }
        
        /* 调整结果区域与成功消息之间的距离 */
        .results-container {
            max-width: 1100px;
            margin: 0 auto 1.5rem auto;
            margin-top: 0.5rem !重要; /* 减少顶部边距 */
        }
        
        /* 减少元素间垂直间距 */
        .element-container, .stAlert > div {
            margin-top: 0.5rem !重要;
            margin-bottom: 0.5rem !重要;
        }
        
        /* 调整成功消息的样式 */
        .st-emotion-cache-1gserj1 {
            margin-top: 0.3rem !重要;
            margin-bottom: 0.3rem !重要;
            padding-top: 0.5rem !重要;
            padding-bottom: 0.5rem !重要;
        }
        
        /* 修改结果卡片样式 - 改为纵向布局优化 */
        .result-card {
            padding: 1.5rem;
            border-radius: 1rem;
            width: 100%;
            box-shadow: 0 8px 20px rgba(0,0,0,0.07);
            transition: all 0.3s ease;
            position: relative;
            background: linear-gradient(145deg, #ffffff, #f0f7ff);
            border-left: 5px solid #1a73e8;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            margin-bottom: 1rem; /* 为纵向布局添加下边距 */
            overflow: visible; /* 确保内容不被截断 */
        }
        
        /* 型号标题样式优化 - 让型号可以完整显示 */
        .model-title {
            font-size: 1.4rem;
            font-weight: 600;
            margin: 0.4rem 0;
            color: #2c3e50;
            line-height: 1.3;
            white-space: normal; /* 允许换行 */
            overflow: visible; /* 允许内容溢出 */
            text-overflow: clip; /* 不使用省略号 */
        }
        
        /* 调整参数部分，确保完整显示 */
        .parameters {
            border-top: 1px dashed #e0e0e0;
            padding-top: 0.8rem;
            margin-top: 0.3rem;
            flex-direction: column;
            flex-grow: 1;
            max-height: none; /* 移除高度限制 */
            overflow-y: visible; /* 不需要滚动 */
        }
        
        /* 每个结果区块 */
        .solution-block {
            margin-bottom: 1.5rem;
            width: 100%;
        }
        
        /* 减少成功消息与结果之间的距离 */
        .st-emotion-cache-16idsys p {
            margin-top: -5px !important;
            padding-top: 5px !important;
            padding-bottom: 5px !重要;
        }
        
        /* 成功框样式 */
        .success-box {
            margin-top: 0.5rem !重要;
            margin-bottom: 0.8rem !重要;
            padding: 0.5rem !重要;
        }
        
        /* 调整结果区域样式 */
        .results-container {
            max-width: 900px; /* 稍微减小宽度 */
            margin: 0 auto 1.5rem auto;
            margin-top: 0.5rem !重要;
        }
        
        /* 纵向布局的卡片头部样式 */
        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.8rem;
        }
        
        /* 显式设置型号容器宽度 */
        .model-container {
            width: 100%;
            padding-right: 1rem;
        }
        
        /* AI聊天相关样式 */
        .chat-container {
            max-width: 800px;
            margin: 0 auto;
            background-color: #fff;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            padding: 1rem;
        }
        
        /* 聊天消息样式 */
        .chat-message {
            padding: 0.5rem 1rem;
            margin-bottom: 0.5rem;
            border-radius: 0.8rem;
        }
        
        .user-message {
            background-color: #e6f2ff;
            border-left: 3px solid #1a73e8;
            margin-left: 1rem;
            margin-right: 2rem;
        }
        
        .assistant-message {
            background-color: #f5f5f5;
            border-right: 3px solid #4caf50;
            margin-left: 2rem;
            margin-right: 1rem;
        }
        
        /* 对话按钮样式 */
        .chat-button {
            font-size: 1rem;
            padding: 0.5rem 1rem;
            background: linear-gradient(90deg, #4caf50, #45a049);
            color: white;
            border-radius: 0.5rem;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            transition: all 0.2s;
        }
        
        .chat-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(76, 175, 80, 0.3);
        }
        
        .chat-button svg {
            fill: currentColor;
            width: 1.2em;
            height: 1.2em;
        }
        
        /* 对话框标题 */
        .chat-title {
            margin-bottom: 1rem;
            text-align: center;
            font-size: 1.5rem;
            font-weight: 600;
            color: #2c3e50;
        }
        
        /* 对话区域样式 */
        .chat-area {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 80%;
            max-width: 800px;
            max-height: 80vh;
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            z-index: 1000;
            padding: 1.5rem;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }
        
        /* 聊天背景遮罩 */
        .chat-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
            z-index: 999;
        }
        
        /* 聊天关闭按钮 */
        .chat-close-btn {
            position: absolute;
            top: 15px;
            right: 15px;
            background: none;
            border: none;
            font-size: 1.5rem;
            cursor: pointer;
            color: #777;
            transition: all 0.2s;
        }
        
        .chat-close-btn:hover {
            color: #f44336;
            transform: scale(1.1);
        }
        
        /* 聊天内容区域 */
        .chat-content {
            flex-grow: 1;
            overflow-y: auto;
            margin-bottom: 1rem;
            padding-right: 0.5rem;
        }
        
        /* 聊天输入区域 */
        .chat-input-area {
            display: flex;
            gap: 0.5rem;
        }
        
        /* 修正在移动设备上的显示 */
        @media (max-width: 768px) {
            .chat-area {
                width: 95%;
                max-height: 90vh;
            }
        }
        
        /* 修改AI对话按钮样式，使其与查询按钮区分 */
        .ai-chat-button > button {
            background: linear-gradient(90deg, #4caf50, #45a049) !important;
            color: white !important;
        }
        
        /* 对话弹窗样式 */
        .chat-dialog {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 80%;
            max-width: 800px;
            height: 80vh;
            max-height: 600px;
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            z-index: 9999;
            padding: 20px;
            display: flex;
            flex-direction: column;
        }
        
        /* 对话框背景遮罩 */
        .dialog-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-color: rgba(0,0,0,0.5);
            z-index: 9998;
        }
        
        /* 对话框标题栏 */
        .chat-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #eee;
        }
        
        /* 对话框标题 */
        .chat-title {
            font-size: 1.5rem;
            font-weight: 600;
            margin: 0;
            color: #2c3e50;
        }
        
        /* 对话内容区 */
        .chat-body {
            flex-grow: 1;
            overflow-y: auto;
            margin-bottom: 15px;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }
        
        /* 对话框底部 */
        .chat-footer {
            display: flex;
            justify-content: flex-end;
        }
        
        /* 关闭按钮样式 */
        .close-button {
            position: absolute;
            top: 20px;
            right: 20px;
            background: none;
            border: none;
            font-size: 24px;
            line-height: 1;
            cursor: pointer;
            color: #666;
        }
        
        .close-button:hover {
            color: #ff0000;
        }
        
        /* 新增样式：预设问题按钮样式 */
        .preset-question {
            display: inline-block;
            margin: 5px 0;
            padding: 8px 12px;
            background-color: #e6f2ff;
            border: 1px solid #b3d1ff;
            border-radius: 20px;
            color: #1a73e8;
            font-size: 0.9rem;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .preset-question:hover {
            background-color: #d4e6ff;
            box-shadow: 0 2px 5px rgba(26, 115, 232, 0.1);
            transform: translateY(-1px);
        }
        
        /* 欢迎信息样式 */
        .welcome-message {
            background-color: #f5f5f5;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #4caf50;
        }
        
        /* 注释文本样式 */
        .note-text {
            font-size: 0.8rem;
            color: #777;
            font-style: italic;
            margin-top: 5px;
        }
        
        /* 预设问题容器 */
        .preset-questions-container {
            margin-top: 10px;
            margin-bottom: 15px;
        }
        
        /* 修改预设问题按钮样式 - 更小更浅 */
        .preset-question-btn {
            background-color: #f0f7ff !important;
            color: #1a73e8 !important; 
            border: 1px solid #cce4ff !important;
            border-radius: 20px !important;
            font-size: 0.85rem !important;
            padding: 0.3rem 0.7rem !important;
            margin: 0.25rem 0.15rem !important;
            min-height: unset !important;
            height: auto !important;
            line-height: 1.2 !important;
            white-space: normal !important;
        }
        
        .preset-question-btn:hover {
            background-color: #e6f0ff !important;
            border-color: #b3d1ff !important;
            transform: translateY(-1px);
            box-shadow: 0 1px 3px rgba(26, 115, 232, 0.1) !important;
        }
        
        /* 预设问题容器 */
        .preset-questions-container {
            margin-top: 5px !important;
            margin-bottom: 15px !重要;
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
        }
        
        /* 欢迎信息样式 */
        .welcome-message {
            background-color: #f5f5f5;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #4caf50;
        }
        
        /* 常见问题标题样式 */
        .faq-title {
            font-size: 0.9rem;
            color: #666;
            margin: 5px 0 !important;
            font-weight: normal;
        }
        
        /* 数据手册链接样式 - 改进 */
        .card-footer {
            margin-top: auto;  /* 自动占用剩余空间，将按钮推到底部 */
            padding-top: 1rem; /* 增加顶部内边距 */
            display: flex;     /* 使用弹性布局 */
            flex-wrap: wrap;   /* 允许按钮换行 */
            gap: 0.5rem;       /* 按钮间隔 */
            justify-content: space-between; /* 分散对齐，确保充分利用空间 */
        }
        
        .datasheet-link {
            display: inline-block;
            text-decoration: none;
            font-weight: 500;
            padding: 0.4rem 0.8rem;
            border-radius: 0.4rem;
            transition: all 0.2s;
            font-size: 0.9rem;
            text-align: center;  /* 居中文字 */
            flex: 1;             /* 允许链接拉伸填充空间 */
            white-space: nowrap; /* 防止文字换行 */
        }
        
        /* 主数据手册链接样式 */
        .primary-link {
            background-color: rgba(26, 115, 232, 0.1);
            color: #1a73e8;
            border: 1px solid rgba(26, 115, 232, 0.2);
        }
        
        .primary-link:hover {
            background-color: rgba(26, 115, 232, 0.2);
            box-shadow: 0 2px 5px rgba(26, 115, 232, 0.2);
            transform: translateY(-1px);
        }
        
        /* 搜索链接样式 */
        .search-link {
            background-color: rgba(76, 175, 80, 0.1);
            color: #4caf50;
            border: 1px solid rgba(76, 175, 80, 0.2);
        }
        
        .search-link:hover {
            background-color: rgba(76, 175, 80, 0.2);
            box-shadow: 0 2px 5px rgba(76, 175, 80, 0.2);
            transform: translateY(-1px);
        }
        
        /* 卡片中内容弹性布局，确保页脚始终在底部 */
        .result-card {
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        
        /* 确保参数区域可以伸缩，但有最小和最大高度限制 */
        .parameters {
            flex-grow: 1;
            min-height: 100px;
            max-height: 200px;
            overflow-y: auto;
        }
    </style>
    """, unsafe_allow_html=True)

    # 使用容器包裹标题，以应用额外样式
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">BOM 元器件国产替代推荐工具</h1>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 在此处添加选项卡，区分单个查询和批量查询
    tab1, tab2 = st.tabs(["单个元器件查询", "BOM批量查询"])
    
    with tab1:
        # 搜索区域 - 修改结构，确保输入框和按钮完全匹配并添加AI对话按钮
        with st.container():
            st.markdown('<div class="search-area">', unsafe_allow_html=True)
            st.markdown('<div class="search-container">', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([3, 0.8, 0.8])  # 调整列比例以容纳两个按钮
            with col1:
                st.markdown('<div class="search-input">', unsafe_allow_html=True)
                # 修改输入框，添加 on_change 参数和键盘事件处理
                part_number = st.text_input("元器件型号", placeholder="输入元器件型号，例如：STM32F103C8", label_visibility="collapsed", 
                                            key="part_number_input", on_change=handle_enter_press)
                st.markdown('</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="search-button">', unsafe_allow_html=True)
                search_button = st.button("查询替代方案", use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div class="search-button ai-chat-button">', unsafe_allow_html=True)
                # 简化AI对话按钮，直接切换会话状态
                if st.button("💬 AI对话助手", key="chat_btn1", use_container_width=True):
                    st.session_state.show_chat = not st.session_state.show_chat
                    # 如果是首次打开对话，添加欢迎消息
                    if st.session_state.show_chat and not st.session_state.chat_messages:
                        st.session_state.chat_messages = [{
                            "role": "assistant",
                            "content": "你好！我是电子元器件专家助手。我可以回答您关于电子元器件的问题，包括参数、应用场景、替代方案和设计建议等。请告诉我您想了解什么？"
                        }]
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # 单个查询按钮逻辑 - 增加对回车键检测的条件
        if search_button or st.session_state.search_triggered:
            if st.session_state.search_triggered:  # 重置状态
                st.session_state.search_triggered = False
                
            if not part_number:
                st.error("⚠️ 请输入元器件型号！")
            else:
                with st.spinner(f"🔄 正在查询 {part_number} 的国产替代方案..."):
                    # 调用后端函数获取替代方案
                    recommendations = get_alternative_parts_func(part_number)
                    
                    # 保存到历史记录
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.search_history.append({
                        "timestamp": timestamp,
                        "part_number": part_number,
                        "recommendations": recommendations,
                        "type": "single"
                    })
                    
                    # 显示结果
                    display_search_results(part_number, recommendations)
    
    with tab2:
        st.markdown("""
        ### 批量查询BOM元器件国产替代方案
        
        上传您的BOM文件（支持 Excel、CSV 格式），工具将自动识别元器件并查询替代方案。
        """)
        
        # 文件上传区域
        uploaded_file = st.file_uploader("上传BOM文件", type=["xlsx", "xls", "csv"])
        
        if uploaded_file is not None:
            # 批量处理按钮 - 移除AI对话按钮，使用单列布局
            col1, col2 = st.columns([3, 1])  # 调整比例，使按钮靠右对齐
            with col2:
                batch_process_button = st.button("开始批量查询", use_container_width=True)
            
            # 如果上传了文件，尝试预览
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_preview = pd.read_csv(uploaded_file, nrows=5)
                else:
                    df_preview = pd.read_excel(uploaded_file, nrows=5)
                
                with st.expander("查看BOM文件预览", expanded=True):
                    st.dataframe(df_preview)
            except Exception as e:
                st.error(f"文件预览失败: {e}")
            
            # 批量处理逻辑
            if batch_process_button:
                # 从backend导入函数
                import sys
                import os
                
                # 确保backend模块可以被导入
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                
                # 现在导入所需函数
                from backend import process_bom_file, batch_get_alternative_parts
                
                # 处理BOM文件，获取更丰富的元器件信息
                components, columns_info = process_bom_file(uploaded_file)
                
                if not components:
                    st.error("⚠️ 无法从BOM文件中识别元器件型号！")
                else:
                    # 显示识别到的列信息
                    st.info(f"已识别 {len(components)} 个不同的元器件")
                    st.success(f"识别到的关键列: 型号列({columns_info.get('mpn_column', '未识别')}), "
                              f"名称列({columns_info.get('name_column', '未识别')}), "
                              f"描述列({columns_info.get('description_column', '未识别')})")
                    
                    # 创建进度条
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # 定义进度回调函数
                    def update_progress(progress, text):
                        progress_bar.progress(progress)
                        status_text.text(text)
                    
                    # 批量查询
                    with st.spinner("批量查询中，请稍候..."):
                        batch_results = batch_get_alternative_parts(components, update_progress)
                    
                    # 完成进度
                    progress_bar.progress(1.0)
                    status_text.text(f"批量查询完成！处理了 {len(components)} 个元器件")
                    
                    # 保存到历史记录
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state.search_history.append({
                        "timestamp": timestamp,
                        "part_number": f"批量查询({len(components)}个)",
                        "batch_results": batch_results,
                        "type": "batch"
                    })
                    
                    # 显示批量结果摘要
                    st.subheader("批量查询结果摘要")
                    
                    # 创建结果摘要表格
                    results_summary = []
                    for mpn, result_info in batch_results.items():
                        alts = result_info.get('alternatives', [])
                        name = result_info.get('name', '')
                        results_summary.append({
                            "元器件名称": name,
                            "元器件型号": mpn,
                            "找到替代方案数": len(alts),
                            "国产替代方案": sum(1 for alt in alts if alt.get("type") == "国产"),
                            "进口替代方案": sum(1 for alt in alts if alt.get("type") == "进口")
                        })
                    
                    # 显示摘要表格
                    df_summary = pd.DataFrame(results_summary)
                    st.dataframe(df_summary)
                    
                    # 显示详细结果
                    with st.expander("查看详细替代方案", expanded=False):
                        for mpn, result_info in batch_results.items():
                            alts = result_info.get('alternatives', [])
                            name = result_info.get('name', '')
                            st.markdown(f"### {mpn} ({name})")
                            if alts:
                                # 修改为竖向排列，每个替代方案占据整行
                                for i, rec in enumerate(alts[:3], 1):
                                    # 构建型号和品牌的展示
                                    model_display = rec['model']
                                    if 'brand' in rec and rec['brand'] and rec['brand'] != '未知品牌':
                                        model_display = f"{model_display} ({rec['brand']})"
                                    
                                    # 使用与单次查询相同的卡片样式，改为纵向排列
                                    st.markdown(f"""
                                    <div class="solution-block">
                                        <div class="result-card">
                                            <div class="card-header">
                                                <div class="model-container">
                                                    <div class="solution-number">方案 {i}</div>
                                                    <div class="type-badge">{rec.get('type', '未知')}</div>
                                                    <h2 class="model-title" title="{model_display}">{model_display}</h2>
                                                </div>
                                            </div>
                                            <div class="info-row">
                                                <div class="info-label">类型：</div>
                                                <div class="info-value">{rec.get('category', '未知类别')}</div>
                                            </div>
                                            <div class="info-row">
                                                <div class="info-label">封装：</div>
                                                <div class="info-value">{rec.get('package', '未知封装')}</div>
                                            </div>
                                            <div class="info-row parameters">
                                                <div class="info-label">参数：</div>
                                                <div class="info-value">{rec['parameters']}</div>
                                            </div>
                                            <div class="card-footer">
                                                <a href="{rec['datasheet']}" target="_blank" class="datasheet-link">查看数据手册</a>
                                            </div>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                            else:
                                st.info("未找到替代方案")
                            st.markdown("---")
                    
                    # 提供下载结果的选项
                    st.subheader("下载查询结果")
                    
                    # 将结果转换为可下载的Excel格式
                    result_data = []
                    for mpn, result_info in batch_results.items():
                        alts = result_info.get('alternatives', [])
                        name = result_info.get('name', '')
                        for i, alt in enumerate(alts[:3], 1):
                            result_data.append({
                                "原元器件名称": name,
                                "原型号": mpn,
                                "替代方案序号": i,
                                "替代型号": alt.get("model", ""),
                                "类型": alt.get("type", "未知"),
                                "参数": alt.get("parameters", ""),
                                "数据手册链接": alt.get("datasheet", "")
                            })
                    
                    if result_data:
                        df_results = pd.DataFrame(result_data)
                        # 将DataFrame转换为Excel
                        output = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
                        with pd.ExcelWriter(output.name) as writer:
                            df_results.to_excel(writer, sheet_name='替代方案', index=False)
                        
                        with open(output.name, 'rb') as f:
                            st.download_button(
                                label="下载替代方案表格 (Excel)",
                                data=f.read(),
                                file_name=f"替代方案查询结果_{timestamp.replace(':', '-')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
        else:
            # 移除空白状态下的AI对话按钮
            st.info("请上传BOM文件（Excel或CSV格式）进行批量查询")

    # 在此处显示AI对话界面 - 将其放在标签页之外，确保无论在哪个标签页都能显示
    if st.session_state.show_chat:
        with st.container():
            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            
            # 聊天标题和关闭按钮
            col1, col2 = st.columns([10, 1])
            with col1:
                st.markdown('<div class="chat-header">', unsafe_allow_html=True)
                st.markdown('<h3 class="chat-title">🤖 电子元器件专家助手</h3>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            with col2:
                if st.button("✕", key="close_chat_btn"):
                    st.session_state.show_chat = False
                    st.rerun()
            
            # 显示欢迎消息和预设问题（始终显示，无论是否有对话历史）
            if len(st.session_state.chat_messages) == 0:
                st.markdown("""
                <div class="welcome-message">
                我是元器件知识小助手，如果你有关于元器件的问题，请随时告诉我，我会尽我所能提供解答。
                <div class="note-text">注：AI智能回复，仅供参考，建议决策时进行多方信息验证。</div>
                </div>
                """, unsafe_allow_html=True)
            
            # 预设问题区域 - 无论是否有历史都显示
            st.markdown('<div class="preset-questions-container">', unsafe_allow_html=True)
            
            # 修改为更明显的样式，确保按钮足够突出
            st.markdown("<p>👇 <b>常见问题示例</b>：</p>", unsafe_allow_html=True)
            
            # 使用行布局，一行一个按钮
            if st.button("有哪些主要型号的LM2596的参数和特性?", key="preset_q1", use_container_width=True):
                # 添加用户问题到对话历史
                preset_question = "有哪些主要型号的LM2596的参数和特性?"
                st.session_state.chat_messages.append({"role": "user", "content": preset_question})
                
                # 调用backend模块获取回复
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from backend import chat_with_expert
                
                with st.spinner("思考中..."):
                    response_stream = chat_with_expert(preset_question)
                    full_response = ""
                    for chunk in response_stream:
                        if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                            content = chunk.choices[0].delta.content
                            if content:
                                full_response += content
                
                # 将AI回复添加到对话历史
                st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
                st.rerun()
            
            if st.button("LDO的常见应用场景有哪些?", key="preset_q2", use_container_width=True):
                # 添加用户问题到对话历史
                preset_question = "LDO的常见应用场景有哪些?"
                st.session_state.chat_messages.append({"role": "user", "content": preset_question})
                
                # 调用backend模块获取回复
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from backend import chat_with_expert
                
                with st.spinner("思考中..."):
                    response_stream = chat_with_expert(preset_question)
                    full_response = ""
                    for chunk in response_stream:
                        if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                            content = chunk.choices[0].delta.content
                            if content:
                                full_response += content
                
                # 将AI回复添加到对话历史
                st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
                st.rerun()
            
            if st.button("如何使用TPS5450设计一个稳定的电源电路?", key="preset_q3", use_container_width=True):
                # 添加用户问题到对话历史
                preset_question = "如何使用TPS5450设计一个稳定的电源电路?"
                st.session_state.chat_messages.append({"role": "user", "content": preset_question})
                
                # 调用backend模块获取回复
                import sys
                import os
                sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                from backend import chat_with_expert
                
                with st.spinner("思考中..."):
                    response_stream = chat_with_expert(preset_question)
                    full_response = ""
                    for chunk in response_stream:
                        if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                            content = chunk.choices[0].delta.content
                            if content:
                                full_response += content
                
                # 将AI回复添加到对话历史
                st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
                st.rerun()
                
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 显示对话历史记录
            for message in st.session_state.chat_messages:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(message["content"])
                else:
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])
            
            # 用户输入
            user_input = st.chat_input("请输入您的问题...")
            if user_input:
                # 显示用户输入
                with st.chat_message("user"):
                    st.markdown(user_input)
                # 添加到对话历史
                st.session_state.chat_messages.append({"role": "user", "content": user_input})
                
                # 显示AI回复
                with st.chat_message("assistant"):
                    with st.spinner("思考中..."):
                        # 导入backend模块
                        import sys
                        import os
                        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                        from backend import chat_with_expert
                        
                        # 调用AI对话函数并处理流式输出
                        response_stream = chat_with_expert(
                            user_input, 
                            history=st.session_state.chat_messages[:-1]  # 不包括刚刚添加的用户消息
                        )
                        
                        response_container = st.empty()
                        full_response = ""
                        
                        # 处理流式响应
                        for chunk in response_stream:
                            if hasattr(chunk.choices[0], 'delta') and hasattr(chunk.choices[0].delta, 'content'):
                                content = chunk.choices[0].delta.content
                                if content:
                                    full_response += content
                                    response_container.markdown(full_response + "▌")
                        
                        # 显示最终结果
                        response_container.markdown(full_response)
                
                # 将AI回复添加到对话历史
                st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
                st.rerun()
            
            # 清除对话按钮
            if st.button("清除对话记录", key="clear_chat_btn"):
                st.session_state.chat_messages = [{
                    "role": "assistant", 
                    "content": "对话已清除。有什么我可以帮到您的？"
                }]
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

    # 在此处添加历史查询功能
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []

    # 修改历史记录展示区以支持批量查询记录
    with st.expander("📜 历史查询记录", expanded=False):
        st.markdown('<div class="history-area">', unsafe_allow_html=True)
        
        # 历史记录标题和清除按钮
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader("您的历史查询")
        with col2:
            if st.button("清除", key="clear_history") and len(st.session_state.search_history) > 0:
                st.session_state.search_history = []
                st.rerun()
        
        # 显示历史记录
        if not st.session_state.search_history:
            st.info("暂无历史查询记录")
        else:
            for idx, history_item in enumerate(reversed(st.session_state.search_history)):
                col1, col2 = st.columns([4, 1])
                with col1:
                    query_type = "批量查询" if history_item.get('type') == 'batch' else "单元器件查询"
                    st.markdown(f"""
                    <div class="history-item">
                        <div class="history-header">
                            <b>{history_item['part_number']}</b>
                            <span class="timestamp">({query_type}) {history_item['timestamp']}</span>
                        </div>
                        <div>
                            {
                                '批量查询多个元器件' if history_item.get('type') == 'batch' 
                                else f"找到 {len(history_item.get('recommendations', []))} 种替代方案"
                            }
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button(f"查看", key=f"view_history_{idx}"):
                        st.session_state.selected_history = history_item
                        st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    # 修改历史记录查看逻辑，以支持批量查询结果
    if 'selected_history' in st.session_state:
        st.markdown("---")
        history_item = st.session_state.selected_history
        
        if history_item.get('type') == 'batch':
            # 显示批量查询结果
            st.subheader(f"历史批量查询结果: {history_item['part_number']}")
            st.caption(f"查询时间: {history_item['timestamp']}")
            
            batch_results = history_item.get('batch_results', {})
            
            # 创建结果摘要表格
            results_summary = []
            for mpn, result_info in batch_results.items():
                if isinstance(result_info, dict) and 'alternatives' in result_info:
                    # 新格式
                    alts = result_info.get('alternatives', [])
                    name = result_info.get('name', '')
                    results_summary.append({
                        "元器件名称": name,
                        "元器件型号": mpn,
                        "找到替代方案数": len(alts),
                        "国产替代方案": sum(1 for alt in alts if alt.get("type") == "国产"),
                        "进口替代方案": sum(1 for alt in alts if alt.get("type") == "进口")
                    })
                else:
                    # 旧格式 - 兼容旧历史记录
                    alts = result_info if isinstance(result_info, list) else []
                    results_summary.append({
                        "元器件型号": mpn,
                        "找到替代方案数": len(alts),
                        "国产替代方案": sum(1 for alt in alts if alt.get("type") == "国产"),
                        "进口替代方案": sum(1 for alt in alts if alt.get("type") == "进口")
                    })
            
            # 显示摘要表格
            df_summary = pd.DataFrame(results_summary)
            st.dataframe(df_summary)
            
            # 显示详细结果
            with st.expander("查看详细替代方案", expanded=False):
                for mpn, result_info in batch_results.items():
                    # 处理新旧格式
                    if isinstance(result_info, dict) and 'alternatives' in result_info:
                        alts = result_info.get('alternatives', [])
                        name = result_info.get('name', '')
                        st.markdown(f"### {mpn} ({name})")
                    else:
                        alts = result_info if isinstance(result_info, list) else []
                        st.markdown(f"### {mpn}")
                    
                    if alts:
                        # 修改为竖向排列
                        for i, rec in enumerate(alts[:3], 1):
                            # 构建型号和品牌的展示
                            model_display = rec['model']
                            if 'brand' in rec and rec['brand'] and rec['brand'] != '未知品牌':
                                model_display = f"{model_display} ({rec['brand']})"
                            
                            # 使用与单次查询相同的卡片样式，改为纵向排列
                            st.markdown(f"""
                            <div class="solution-block">
                                <div class="result-card">
                                    <div class="card-header">
                                        <div class="model-container">
                                            <div class="solution-number">方案 {i}</div>
                                            <div class="type-badge">{rec.get('type', '未知')}</div>
                                            <h2 class="model-title" title="{model_display}">{model_display}</h2>
                                        </div>
                                    </div>
                                    <div class="info-row">
                                        <div class="info-label">类型：</div>
                                        <div class="info-value">{rec.get('category', '未知类别')}</div>
                                    </div>
                                    <div class="info-row">
                                        <div class="info-label">封装：</div>
                                        <div class="info-value">{rec.get('package', '未知封装')}</div>
                                    </div>
                                    <div class="info-row parameters">
                                        <div class="info-label">参数：</div>
                                        <div class="info-value">{rec['parameters']}</div>
                                    </div>
                                    <div class="card-footer">
                                        <a href="{rec['datasheet']}" target="_blank" class="datasheet-link">查看数据手册</a>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("未找到替代方案")
                    st.markdown("---")
        else:
            # 单个查询结果显示
            st.subheader(f"历史查询结果: {history_item['part_number']}")
            st.caption(f"查询时间: {history_item['timestamp']}")
            
            # 使用与原始查询相同的显示逻辑
            recommendations = history_item.get('recommendations', [])
            display_search_results(history_item['part_number'], recommendations)
        
        if st.button("返回"):
            del st.session_state.selected_history
            st.rerun()

    # 添加页脚信息 - 降低显示度
    st.markdown("---")
    st.markdown('<p class="footer-text">本工具基于深度学习模型与Nexar API，提供元器件替代参考，实际使用请结合专业工程师评估</p>', unsafe_allow_html=True)

# 抽取显示结果的函数，以便重复使用
def display_search_results(part_number, recommendations):
    # 结果区域添加容器
    st.markdown('<div class="results-container">', unsafe_allow_html=True)
    
    if recommendations:
        # 使用自定义样式的成功消息
        st.markdown(f"""
        <div class="success-box st-emotion-cache-16idsys">
            <p>已为 <b>{part_number}</b> 找到 {len(recommendations)} 种替代方案</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 获取推荐数量
        rec_count = min(3, len(recommendations))
        
        # 纵向展示每个方案
        for i in range(rec_count):
            rec = recommendations[i]
            
            # 构建型号和品牌的展示
            model_display = rec['model']
            if 'brand' in rec and rec['brand'] and rec['brand'] != '未知品牌':
                model_display = f"{model_display} ({rec['brand']})"
            
            # 创建方案卡片 - 纵向排列
            st.markdown(f"""
            <div class="solution-block">
                <div class="result-card">
                    <div class="card-header">
                        <div class="model-container">
                            <div class="solution-number">方案 {i+1}</div>
                            <div class="type-badge">{rec.get('type', '未知')}</div>
                            <h2 class="model-title" title="{model_display}">{model_display}</h2>
                        </div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">类型：</div>
                        <div class="info-value">{rec.get('category', '未知类别')}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label">封装：</div>
                        <div class="info-value">{rec.get('package', '未知封装')}</div>
                    </div>
                    <div class="info-row parameters">
                        <div class="info-label">参数：</div>
                        <div class="info-value">{rec['parameters']}</div>
                    </div>
                    <div class="card-footer">
                        <a href="{rec['datasheet']}" target="_blank" class="datasheet-link">查看数据手册</a>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="no-result-box">
            <h3>未找到合适的替代方案</h3>
            <p>请尝试修改搜索关键词或查询其他型号</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown('</div>', unsafe_allow_html=True)