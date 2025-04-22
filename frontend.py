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
        /* 整体页面样式 - 减少空白 */
        .stApp {
            background-color: #f8f9fa;
        }
        
        /* 标题样式改进 - 进一步减小外边距 */
        .main-header {
            font-size: 2.5rem;
            font-weight: 800;
            color: #1a73e8;
            text-align: center;
            padding: 0.5rem 0; /* 减少顶部和底部内边距 */
            margin-bottom: 0.5rem; /* 减少底部外边距 */
            background: linear-gradient(90deg, #1a73e8, #4285f4, #6c5ce7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
            line-height: 1.2;
            text-shadow: 0 4px 10px rgba(26, 115, 232, 0.1);
        }
        
        /* 修改标题装饰 - 减少间距 */
        .header-container {
            position: relative;
            padding: 0 0.5rem; /* 减小内边距 */
            margin-bottom: 0.5rem; /* 减小底部外边距 */
        }
        
        /* 使标签面板与页面背景色保持一致，移除边框和阴影 */
        .stTabs [data-baseweb="tab-panel"] {
            background-color: transparent !重要; 
            border: none !重要;
            box-shadow: none !重要;
            padding-top: 0.3rem !重要; /* 减少顶部内边距 */
        }
        
        /* 修改标签样式，减少空间 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 20px !重要; /* 减少标签之间的间距 */
            margin-bottom: 0 !重要; /* 移除底部外边距 */
        }
        
        /* 搜索区域样式改进 - 进一步减小内边距和外边距 */
        .search-area {
            background: linear-gradient(145deg, #ffffff, #f0f7ff);
            box-shadow: 0 5px 15px rgba(26, 115, 232, 0.15);
            padding: 0.8rem; /* 减小内边距 */
            border-radius: 0.8rem;
            margin-bottom: 1rem; /* 减小底部外边距 */
            border: 1px solid rgba(26, 115, 232, 0.1);
            max-width: 1000px;
            margin-left: auto;
            margin-right: auto;
            display: flex;
            align-items: center;
        }
        
        /* 修复搜索框和按钮容器 - 减少间距 */
        .search-container {
            display: flex;
            align-items: center;
            gap: 10px; /* 减少间距 */
            margin: 0;
            padding: 0;
            width: 100%;
        }
        
        /* 减少整体页面的内边距 */
        .block-container {
            padding-top: 0.5rem !重要; /* 减少顶部内边距 */
            padding-bottom: 0.5rem !重要; /* 减少底部内边距 */
            max-width: 1200px;
            padding-left: 1rem !重要; /* 减少左侧内边距 */
            padding-right: 1rem !重要; /* 减少右侧内边距 */
        }
        
        /* 减少元素间垂直间距 */
        .element-container, .stAlert > div {
            margin-top: 0.3rem !重要; /* 减少顶部外边距 */
            margin-bottom: 0.3rem !重要; /* 减少底部外边距 */
        }
        
        /* 聊天容器样式 - 减少空白区域 */
        .chat-container {
            max-width: 800px;
            margin: 0 auto;
            background-color: #fff;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            padding: 0.8rem; /* 减少内边距 */
            margin-top: 0.5rem; /* 减少顶部外边距 */
            margin-bottom: 0.5rem; /* 减少底部外边距 */
        }
        
        /* 对话框标题区域 - 减少间距 */
        .chat-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            padding-bottom: 5px; /* 减少底部内边距 */
            border-bottom: 1px solid #eee;
        }
        
        /* 对话框标题 - 减少间距 */
        .chat-title {
            margin-bottom: 0.5rem; /* 减少底部外边距 */
            text-align: center;
            font-size: 1.3rem; /* 减小字体大小 */
            font-weight: 600;
            color: #2c3e50;
        }
        
        /* 预设问题容器 - 减少间距 */
        .preset-questions-container {
            margin-top: 0.3rem !重要; /* 减少顶部外边距 */
            margin-bottom: 0.5rem !重要; /* 减少底部外边距 */
            display: flex;
            flex-wrap: wrap;
            gap: 3px; /* 减少按钮之间的间距 */
        }
        
        /* 欢迎信息样式 - 减少间距 */
        .welcome-message {
            background-color: #f5f5f5;
            border-radius: 8px; /* 减小圆角 */
            padding: 10px; /* 减少内边距 */
            margin-bottom: 8px; /* 减少底部外边距 */
            border-left: 4px solid #4caf50;
        }
        
        /* 常见问题标题样式 */
        .faq-title {
            font-size: 0.9rem;
            color: #666;
            margin: 3px 0 !重要; /* 减少外边距 */
            font-weight: normal;
        }
        
        /* 对话内容区域样式 */
        .stChatMessage {
            padding: 8px !重要; /* 减少内边距 */
            border-radius: 8px !重要; /* 减小圆角 */
            margin-bottom: 6px !重要; /* 减少底部外边距 */
        }
        
        /* 让输入框在聊天对话区域更加紧凑 */
        .stChatInput {
            margin-top: 8px !重要; /* 减少顶部外边距 */
            margin-bottom: 8px !重要; /* 减少底部外边距 */
            padding: 3px !重要; /* 减少内边距 */
        }
        
        /* 隐藏Streamlit默认元素的外边距 */
        div.css-1kyxreq {
            margin-top: 0.3rem !重要;
            margin-bottom: 0.3rem !重要;
        }
        
        /* 减少各种Streamlit元素的垂直间距 */
        .stButton, .stTextInput, .stSelectbox, .stFileUploader {
            margin-bottom: 0.3rem;
        }
        
        /* 修复列对齐问题，减少列间距 */
        div[data-testid="column"] {
            padding: 0 !重要;
            margin: 0 !重要;
        }
        
        /* 减少tab内部元素的间距 */
        .stTabs [data-baseweb="tab-panel"] > div > div {
            margin-top: 0.3rem;
            margin-bottom: 0.3rem;
        }
        
        /* 减少单个元器件查询和BOM批量查询tab之间的垂直间距 */
        .stTabs {
            margin-bottom: 0.5rem !重要;
        }
        
        /* 处理输入框的提示文字 */
        .stChatInput textarea::placeholder, .stChatInput input::placeholder {
            color: #8c9bb5 !重要;
            font-size: 1rem !重要; /* 减小字体大小 */
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
                    df_preview = pd.read_csv(uploaded_file)  # 移除nrows=5限制，显示所有行
                else:
                    df_preview = pd.read_excel(uploaded_file)  # 移除nrows=5限制，显示所有行
                
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
                    st.subheader("📊 下载查询结果")
                    
                    # 将结果转换为可下载的Excel格式
                    result_data = []
                    
                    # 遍历所有批量查询结果
                    for mpn, result_info in batch_results.items():
                        alts = result_info.get('alternatives', [])
                        name = result_info.get('name', '')
                        description = result_info.get('description', '')
                        
                        # 如果没有替代方案，添加一个"未找到替代方案"的记录
                        if not alts:
                            result_data.append({
                                "原元器件名称": name,
                                "原型号": mpn,
                                "原器件描述": description,
                                "替代方案序号": "-",
                                "替代型号": "未找到替代方案",
                                "替代品牌": "-",
                                "类别": "-",
                                "封装": "-",
                                "类型": "-",
                                "参数": "-",
                                "数据手册链接": "-"
                            })
                        else:
                            # 添加找到的替代方案
                            for i, alt in enumerate(alts, 1):
                                result_data.append({
                                    "原元器件名称": name,
                                    "原型号": mpn,
                                    "原器件描述": description,
                                    "替代方案序号": i,
                                    "替代型号": alt.get("model", ""),
                                    "替代品牌": alt.get("brand", "未知品牌"),
                                    "类别": alt.get("category", "未知类别"),
                                    "封装": alt.get("package", "未知封装"),
                                    "类型": alt.get("type", "未知"),
                                    "参数": alt.get("parameters", ""),
                                    "数据手册链接": alt.get("datasheet", "")
                                })
                    
                    # 当有结果数据时，生成并提供下载
                    if result_data:
                        # 创建DataFrame
                        df_results = pd.DataFrame(result_data)
                        
                        # 添加两种下载格式选项
                        col1, col2 = st.columns(2)
                        
                        # 创建Excel文件
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as excel_file:
                            with pd.ExcelWriter(excel_file.name, engine='openpyxl') as writer:
                                df_results.to_excel(writer, sheet_name='替代方案查询结果', index=False)
                            
                            # 读取生成的Excel文件
                            with open(excel_file.name, 'rb') as f:
                                excel_data = f.read()
                        
                        # 创建CSV文件
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as csv_file:
                            df_results.to_csv(csv_file.name, index=False, encoding='utf-8-sig')  # 使用带BOM的UTF-8编码，Excel可以正确识别中文
                            
                            # 读取生成的CSV文件
                            with open(csv_file.name, 'rb') as f:
                                csv_data = f.read()
                        
                        # 显示两个下载按钮
                        with col1:
                            st.download_button(
                                label="📥 下载为Excel文件 (.xlsx)",
                                data=excel_data,
                                file_name=f"元器件替代方案查询结果_{timestamp.replace(':', '-')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True
                            )
                        
                        with col2:
                            st.download_button(
                                label="📥 下载为CSV文件 (.csv)",
                                data=csv_data,
                                file_name=f"元器件替代方案查询结果_{timestamp.replace(':', '-')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        
                        # 添加下载说明
                        st.info("💡 提示：Excel格式适合大多数办公软件查看，CSV格式兼容性更广但可能需要额外设置字符编码")
                    else:
                        st.warning("⚠️ 没有查询到任何替代方案，无法生成下载文件")
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
            
            # 显示欢迎消息（始终显示，无论是否有对话历史）
            if len(st.session_state.chat_messages) == 0:
                st.markdown("""
                <div class="welcome-message">
                我是元器件知识小助手，如果你有关于元器件的问题，请随时告诉我，我会尽我所能提供解答。
                <div class="note-text">注：AI智能回复，仅供参考，建议决策时进行多方信息验证。</div>
                </div>
                """, unsafe_allow_html=True)
            
            # 显示对话历史记录
            for message in st.session_state.chat_messages:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(message["content"])
                else:
                    with st.chat_message("assistant"):
                        st.markdown(message["content"])
            
            # 预设问题区域 - 移动到这里，在对话历史和用户输入之间
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