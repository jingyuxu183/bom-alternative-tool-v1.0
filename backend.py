import os
import sys
import importlib.util
import subprocess
from dotenv import load_dotenv
from openai import OpenAI
import json
import re
import streamlit as st
import pandas as pd
import tempfile
from nexarClient import NexarClient

# 检查并安装必要的依赖库
def check_and_install_dependencies():
    """检查并安装处理Excel文件所需的依赖库"""
    dependencies = {
        'xlrd': 'xlrd>=2.0.1',      # 处理旧版 .xls 文件
        'openpyxl': 'openpyxl',     # 处理新版 .xlsx 文件
    }
    
    for module, package in dependencies.items():
        if importlib.util.find_spec(module) is None:
            try:
                st.info(f"正在安装依赖: {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                st.success(f"{package} 安装完成")
            except Exception as e:
                st.error(f"安装 {package} 失败: {e}")
                st.info(f"请手动安装: pip install {package}")

# 在导入pandas之前检查依赖
check_and_install_dependencies()

# 加载环境变量
load_dotenv()

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
if not DEEPSEEK_API_KEY:
    raise ValueError("错误：未找到 DEEPSEEK_API_KEY 环境变量。")
deepseek_client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# Nexar API 配置
NEXAR_CLIENT_ID = os.getenv("NEXAR_CLIENT_ID")
NEXAR_CLIENT_SECRET = os.getenv("NEXAR_CLIENT_SECRET")
if not NEXAR_CLIENT_ID or not NEXAR_CLIENT_SECRET:
    raise ValueError("错误：未找到 NEXAR_CLIENT_ID 或 NEXAR_CLIENT_SECRET 环境变量。")
nexar_client = NexarClient(NEXAR_CLIENT_ID, NEXAR_CLIENT_SECRET)

# GraphQL 查询
QUERY_ALTERNATIVE_PARTS = '''
query findAlternativeParts($q: String!, $limit: Int = 10) {
  supSearchMpn(q: $q, limit: $limit) {
    hits
    results {
      part {
        similarParts {
          name
          mpn
          octopartUrl
        }
      }
    }
  }
}
'''

def get_nexar_alternatives(mpn: str, limit: int = 10):
    variables = {"q": mpn, "limit": limit}
    try:
        data = nexar_client.get_query(QUERY_ALTERNATIVE_PARTS, variables)
        alternative_parts = []
        
        # 添加数据有效性检查与调试信息
        if not data:
            st.warning(f"Nexar API 未返回有效数据，可能是查询 '{mpn}' 无结果")
            return []
            
        # 显示调试信息
        with st.sidebar.expander(f"Nexar API 调试信息 - {mpn}", expanded=False):
            st.write(f"**原始Nexar API响应结构:**")
            st.write(data)
            
        # 完全重写数据提取逻辑，以更健壮的方式处理各种可能的结构
        if isinstance(data, dict):
            # 尝试从不同位置提取数据
            sup_search = data.get("supSearchMpn", {})
            
            # 如果supSearchMpn是字典
            if isinstance(sup_search, dict):
                results = sup_search.get("results", [])
                
                # 如果results是列表
                if isinstance(results, list):
                    # 正常处理
                    for result in results:
                        if not isinstance(result, dict):
                            continue
                            
                        part = result.get("part", {})
                        if not isinstance(part, dict):
                            continue
                            
                        similar_parts = part.get("similarParts", [])
                        if not isinstance(similar_parts, list):
                            continue
                            
                        for similar in similar_parts:
                            if not isinstance(similar, dict):
                                continue
                                
                            alternative_parts.append({
                                "name": similar.get("name", ""),
                                "mpn": similar.get("mpn", ""),
                                "octopartUrl": similar.get("octopartUrl", "")
                            })
                else:
                    # 如果results不是列表，尝试其他数据结构
                    st.warning(f"Nexar API 返回了非标准结构的数据 (results不是列表)")
                    
                    # 尝试直接从顶层提取数据
                    parts_data = []
                    
                    # 检查是否有直接的part字段
                    if "part" in sup_search:
                        part = sup_search.get("part", {})
                        if isinstance(part, dict) and "similarParts" in part:
                            parts_data = part.get("similarParts", [])
                    
                    # 如果找到疑似部件数据
                    if isinstance(parts_data, list):
                        for part_item in parts_data:
                            if not isinstance(part_item, dict):
                                continue
                                
                            alternative_parts.append({
                                "name": part_item.get("name", "未知名称"),
                                "mpn": part_item.get("mpn", "未知型号"),
                                "octopartUrl": part_item.get("octopartUrl", "https://example.com")
                            })
            else:
                st.warning(f"Nexar API 返回了非标准结构 (supSearchMpn不是字典)")
                # 尝试从整个响应中找到任何可能的部件信息
                for key, value in data.items():
                    if isinstance(value, dict) and "parts" in value:
                        parts = value.get("parts", [])
                        if isinstance(parts, list):
                            for part in parts:
                                if not isinstance(part, dict):
                                    continue
                                alternative_parts.append({
                                    "name": part.get("name", "未知名称"),
                                    "mpn": part.get("mpn", "未知型号"),
                                    "octopartUrl": "https://example.com"
                                })
        
        # 如果无法找到任何替代件
        if not alternative_parts:
            st.info(f"Nexar API 未能为 '{mpn}' 找到替代元器件")
            
            # 创建一个假数据用于测试其他部分的功能
            if st.session_state.get("use_dummy_data", False):
                st.info("使用测试数据继续查询")
                alternative_parts = [
                    {
                        "name": f"类似元件: {mpn}替代品1",
                        "mpn": f"{mpn}_ALT1",
                        "octopartUrl": "https://www.octopart.com"
                    },
                    {
                        "name": f"类似元件: {mpn}替代品2",
                        "mpn": f"{mpn}_ALT2",
                        "octopartUrl": "https://www.octopart.com"
                    }
                ]
            
        return alternative_parts
        
    except Exception as e:
        st.error(f"Nexar API 查询失败: {e}")
        import traceback
        with st.sidebar.expander("Nexar API错误详情", expanded=False):
            st.code(traceback.format_exc())
        return []

def is_domestic_brand(model_name):
    domestic_brands = [
        "GigaDevice", "兆易创新", "WCH", "沁恒", "Fudan Micro", "复旦微电子",
        "Zhongying", "中颖电子", "SG Micro", "圣邦微电子", "LD", "LDO", "SG", "SGC",
        "APM", "AP", "BL", "BYD", "CETC", "CR Micro", "CR", "HuaDa", "HuaHong",
        "SGM", "BLD", "EUTECH", "EUTECH Micro", "3PEAK", "Chipsea", "Chipown"
    ]
    # 更宽松的匹配：检查型号是否以国产品牌的常见前缀开头或包含品牌名
    return any(model_name.lower().startswith(brand.lower()) for brand in domestic_brands) or \
           any(brand.lower() in model_name.lower() for brand in domestic_brands)

def extract_json_content(content, call_type="初次调用"):
    # 记录原始内容以便调试
    with st.sidebar.expander(f"调试信息 - 原始响应 ({call_type})", expanded=False):
        st.write(f"**尝试解析的原始响应内容 ({call_type}):**")
        st.code(content, language="text")

    # 处理空响应
    if not content or content.strip() == "":
        st.warning(f"{call_type} 返回了空响应")
        return []

    # 直接尝试解析 JSON
    try:
        parsed = json.loads(content)
        # 检查是否为列表
        if not isinstance(parsed, list):
            raise ValueError("响应不是 JSON 数组")
        # 补全缺少的字段
        for item in parsed:
            # 确保基本字段存在
            item["model"] = item.get("model", "未知型号")
            item["brand"] = item.get("brand", "未知品牌")
            item["parameters"] = item.get("parameters", "参数未知")
            item["type"] = item.get("type", "未知")
            item["datasheet"] = item.get("datasheet", "https://www.example.com/datasheet")
            
            # 确保新增字段存在
            item["category"] = item.get("category", "未知类别")
            item["package"] = item.get("package", "未知封装")
            
        return parsed
    except json.JSONDecodeError:
        pass

    # 尝试提取代码块中的 JSON
    code_block_pattern = r"```(?:json)?\s*\n?([\s\S]*?)\n?```"
    code_match = re.search(code_block_pattern, content, re.DOTALL)
    if (code_match):
        json_content = code_match.group(1).strip()
        try:
            parsed = json.loads(json_content)
            for item in parsed:
                # 确保基本字段存在
                item["model"] = item.get("model", "未知型号")
                item["brand"] = item.get("brand", "未知品牌")
                item["parameters"] = item.get("parameters", "参数未知")
                item["type"] = item.get("type", "未知")
                item["datasheet"] = item.get("datasheet", "https://www.example.com/datasheet")
                
                # 确保新增字段存在
                item["category"] = item.get("category", "未知类别")
                item["package"] = item.get("package", "未知封装")
                
            return parsed
        except json.JSONDecodeError:
            pass

    # 尝试提取裸 JSON 数组
    json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            for item in parsed:
                if not all(key in item for key in ["model", "parameters", "type", "datasheet"]):
                    item["model"] = item.get("model", "未知型号")
                    item["parameters"] = item.get("parameters", "参数未知")
                    item["type"] = item.get("type", "未知")
                    item["datasheet"] = item.get("datasheet", "https://www.example.com/datasheet")
                # 确保品牌字段存在
                if "brand" not in item:
                    item["brand"] = item.get("brand", "未知品牌")
                # 确保新增字段存在
                item["category"] = item.get("category", "未知类别")
                item["package"] = item.get("package", "未知封装")
            return parsed
        except json.JSONDecodeError:
            pass

    # 尝试逐行解析，处理可能的多行 JSON
    lines = content.strip().split('\n')
    json_content = ''
    in_json = False
    for line in lines:
        line = line.strip()
        if line.startswith('[') or in_json:
            json_content += line
            in_json = True
        if line.endswith(']'):
            break
    if json_content:
        try:
            parsed = json.loads(json_content)
            for item in parsed:
                if not all(key in item for key in ["model", "parameters", "type", "datasheet"]):
                    item["model"] = item.get("model", "未知型号")
                    item["parameters"] = item.get("parameters", "参数未知")
                    item["type"] = item.get("type", "未知")
                    item["datasheet"] = item.get("datasheet", "https://www.example.com/datasheet")
                # 确保品牌字段存在
                if "brand" not in item:
                    item["brand"] = item.get("brand", "未知品牌")
                # 确保新增字段存在
                item["category"] = item.get("category", "未知类别")
                item["package"] = item.get("package", "未知封装")
            return parsed
        except json.JSONDecodeError:
            pass

    # 添加更强大的JSON提取处理，处理更多边缘情况
    # 尝试从文本中抽取任何看起来像JSON对象的内容
    possible_json_pattern = r'\[\s*\{\s*"model"\s*:.*?\}\s*\]'
    json_fragments = re.findall(possible_json_pattern, content, re.DOTALL)
    
    for fragment in json_fragments:
        try:
            parsed = json.loads(fragment)
            # 补全缺少的字段
            for item in parsed:
                if not all(key in item for key in ["model", "parameters", "type", "datasheet"]):
                    item["model"] = item.get("model", "未知型号")
                    item["parameters"] = item.get("parameters", "参数未知")
                    item["type"] = item.get("type", "未知")
                    item["datasheet"] = item.get("datasheet", "https://www.example.com/datasheet")
                # 确保品牌字段存在
                if "brand" not in item:
                    item["brand"] = item.get("brand", "未知品牌")
                # 确保新增字段存在
                item["category"] = item.get("category", "未知类别")
                item["package"] = item.get("package", "未知封装")
            return parsed
        except json.JSONDecodeError:
            pass
            
    # 如果上面方法都失败，尝试手动修复常见的JSON格式错误
    for fix_attempt in [
        lambda c: c.replace("'", '"'),  # 单引号替换为双引号
        lambda c: re.sub(r'",\s*\}', '"}', c),  # 修复尾部多余逗号
        lambda c: re.sub(r',\s*]', ']', c)  # 修复数组尾部多余逗号
    ]:
        try:
            fixed_content = fix_attempt(content)
            parsed = json.loads(fixed_content)
            if isinstance(parsed, list):
                for item in parsed:
                    if not all(key in item for key in ["model", "parameters", "type", "datasheet"]):
                        item["model"] = item.get("model", "未知型号")
                        item["parameters"] = item.get("parameters", "参数未知")
                        item["type"] = item.get("type", "未知")
                        item["datasheet"] = item.get("datasheet", "https://www.example.com/datasheet")
                    # 确保品牌字段存在
                    if "brand" not in item:
                        item["brand"] = item.get("brand", "未知品牌")
                    # 确保新增字段存在
                    item["category"] = item.get("category", "未知类别")
                    item["package"] = item.get("package", "未知封装")
                return parsed
        except:
            pass

    st.error(f"无法从API响应中提取有效的JSON内容 ({call_type})")
    return []

def get_alternative_parts(part_number):
    # Step 1: 获取 Nexar API 的替代元器件数据
    nexar_alternatives = get_nexar_alternatives(part_number, limit=10)
    context = "Nexar API 提供的替代元器件数据：\n"
    if (nexar_alternatives):
        for i, alt in enumerate(nexar_alternatives, 1):
            context += f"{i}. 型号: {alt['mpn']}, 名称: {alt['name']}, 链接: {alt['octopartUrl']}\n"
    else:
        st.warning("⚠️ Nexar API 未返回数据，将直接使用 DeepSeek 推荐。")
        context = "无 Nexar API 数据可用，请直接推荐替代元器件。\n"

    # Step 2: 构造 DeepSeek API 的提示词
    prompt = f"""
    任务：你是一个专业的电子元器件顾问，专精于国产替代方案。以下是 Nexar API 提供的替代元器件数据，请结合这些数据为输入元器件推荐替代产品。推荐的替代方案必须与输入型号 {part_number} 不同（绝对不能推荐 {part_number} 或其变体，如 {part_number} 的不同封装）。

    输入元器件型号：{part_number}

    {context}

    要求：
    1. 必须推荐至少一种中国大陆本土品牌的替代方案（如 GigaDevice/兆易创新、WCH/沁恒、复旦微电子、中颖电子、圣邦微电子等）
    2. 如果能找到多种中国大陆本土品牌的替代产品，优先推荐这些产品，推荐的国产方案数量越多越好
    3. 如果实在找不到足够三种中国大陆本土品牌的产品，可以推荐国外品牌产品作为补充，但必须明确标注
    4. 总共需要推荐 3 种性能相近的替代型号
    5. 提供每种型号的品牌名称、封装信息和元器件类目（例如：MCU、DCDC、LDO、传感器、存储芯片等）
    6. 根据元器件类型提供不同的关键参数：
       - 若是MCU/单片机：提供CPU内核、主频、程序存储容量、RAM大小、IO数量
       - 若是DCDC：提供输入电压范围、输出电压、最大输出电流、效率
       - 若是LDO：提供输入电压范围、输出电压、最大输出电流、压差
       - 若是存储器：提供容量、接口类型、读写速度
       - 若是传感器：提供测量范围、精度、接口类型
       - 其他类型提供对应的关键参数
    7. 在每个推荐方案中明确标注是"国产"还是"进口"产品
    8. 提供产品官网链接（若无真实链接，可提供示例链接，如 https://www.example.com/datasheet）
    9. 推荐的型号不能与输入型号 {part_number} 相同
    10. 必须严格返回以下 JSON 格式的结果，不允许添加任何额外说明、Markdown 格式或代码块标记（即不要使用 ```json 或其他标记），直接返回裸 JSON：
    [
        {{"model": "SG1117-1.2", "brand": "SG Micro/圣邦微电子", "category": "LDO", "package": "DPAK", "parameters": "输入电压: 2.0-12V, 输出电压: 1.2V, 输出电流: 800mA, 压差: 1.1V", "type": "国产", "datasheet": "https://www.sgmicro.com/datasheet"}},
        {{"model": "GD32F103C8T6", "brand": "GigaDevice/兆易创新", "category": "MCU", "package": "LQFP48", "parameters": "CPU内核: ARM Cortex-M3, 主频: 72MHz, Flash: 64KB, RAM: 20KB, IO: 37", "type": "国产", "datasheet": "https://www.gigadevice.com/datasheet"}},
        {{"model": "MP2307DN", "brand": "MPS/芯源系统", "category": "DCDC", "package": "SOIC-8", "parameters": "输入电压: 4.75-23V, 输出电压: 0.925-20V, 输出电流: 3A, 效率: 95%", "type": "进口", "datasheet": "https://www.monolithicpower.com/datasheet"}}
    ]
    """

    try:
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个精通中国电子元器件行业的专家，擅长为各种元器件寻找合适的替代方案，尤其专注于中国大陆本土生产的国产元器件。始终以有效的JSON格式回复，不添加任何额外说明。"},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            max_tokens=1000
        )
        raw_content = response.choices[0].message.content
        recommendations = extract_json_content(raw_content, "初次调用")

        # Step 3: 过滤掉与输入型号相同的推荐
        recommendations = [rec for rec in recommendations if rec["model"].lower() != part_number.lower()]

        # Step 4: 如果推荐数量不足，从 Nexar 数据中补充
        if len(recommendations) < 3 and nexar_alternatives:
            for alt in nexar_alternatives:
                if len(recommendations) >= 3:
                    break
                if alt["mpn"].lower() != part_number.lower():
                    recommendations.append({
                        "model": alt["mpn"],
                        "brand": alt.get("name", "未知品牌").split(' ')[0] if alt.get("name") else "未知品牌",
                        "category": "未知类别",
                        "package": "未知封装",
                        "parameters": "参数未知",
                        "type": "未知",
                        "datasheet": alt["octopartUrl"]
                    })

        # Step 5: 后处理，识别国产方案
        for rec in recommendations:
            if rec["type"] == "未知" and is_domestic_brand(rec["model"]):
                rec["type"] = "国产"

        # Step 6: 如果仍然不足 3 个，或缺少国产方案，重新调用 DeepSeek 强调国产优先
        need_second_query = len(recommendations) < 3 or not any(rec["type"] == "国产" for rec in recommendations)
        
        if need_second_query:
            st.warning("⚠️ 推荐结果不足或未包含国产方案，将重新调用 DeepSeek 推荐。")
            
            prompt_retry = f"""
            任务：为以下元器件推荐替代产品，推荐的替代方案必须与输入型号 {part_number} 不同（绝对不能推荐 {part_number} 或其变体，如 {part_number} 的不同封装）。
            输入元器件型号：{part_number}

            之前的推荐结果未包含国产方案或数量不足，请重新推荐，重点关注国产替代方案。

            要求：
            1. 必须推荐至少一种中国大陆本土品牌的替代方案（如 GigaDevice/兆易创新、WCH/沁恒、复旦微电子、中颖电子、圣邦微电子、3PEAK、Chipsea 等）
            2. 优先推荐国产芯片，推荐的国产方案数量越多越好
            3. 如果找不到足够的国产方案，可以补充进口方案，但必须明确标注
            4. 总共推荐 {3 - len(recommendations)} 种替代方案
            5. 提供每种型号的品牌名称、封装信息和元器件类目（例如：MCU、DCDC、LDO、传感器等）
            6. 根据元器件类型提供不同的关键参数：
               - 若是MCU/单片机：提供CPU内核、主频、程序存储容量、RAM大小、IO数量
               - 若是DCDC：提供输入电压范围、输出电压、最大输出电流、效率
               - 若是LDO：提供输入电压范围、输出电压、最大输出电流、压差
               - 若是存储器：提供容量、接口类型、读写速度
               - 若是传感器：提供测量范围、精度、接口类型
               - 其他类型提供对应的关键参数
            7. 在每个推荐方案中明确标注是"国产"还是"进口"产品
            8. 提供产品官网链接（若无真实链接，可提供示例链接，如 https://www.example.com/datasheet）
            9. 推荐的型号不能与输入型号 {part_number} 相同
            10. 必须严格返回以下 JSON 格式的结果，不允许添加任何额外说明、Markdown 格式或代码块标记，直接返回裸 JSON：
            [
                {{"model": "型号1", "brand": "品牌1", "category": "类别1", "package": "封装1", "parameters": "参数1", "type": "国产/进口", "datasheet": "链接1"}},
                {{"model": "型号2", "brand": "品牌2", "category": "类别2", "package": "封装2", "parameters": "参数2", "type": "国产/进口", "datasheet": "链接2"}}
            ]
            11. 每个推荐项必须包含 "model"、"brand"、"category"、"package"、"parameters"、"type" 和 "datasheet" 七个字段
            12. 如果无法找到合适的替代方案，返回空的 JSON 数组：[]
            """
            
            second_query_success = False
            max_retries = 3
            additional_recommendations = []
            
            for attempt in range(max_retries):
                try:
                    response_retry = deepseek_client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": "你是一个精通中国电子元器件行业的专家，擅长为各种元器件寻找合适的替代方案，尤其专注于中国大陆本土生产的国产元器件。始终以有效的JSON格式回复，不添加任何额外说明。"},
                            {"role": "user", "content": prompt_retry}
                        ],
                        stream=False,
                        max_tokens=1000
                    )
                    raw_content_retry = response_retry.choices[0].message.content
                    
                    with st.spinner(f"正在解析第 {attempt + 1} 次二次查询结果..."):
                        additional_recommendations = extract_json_content(raw_content_retry, f"重新调用，第 {attempt + 1} 次")
                    
                    if additional_recommendations:
                        second_query_success = True
                        # 过滤掉与原型号相同的推荐
                        additional_recommendations = [rec for rec in additional_recommendations if rec["model"].lower() != part_number.lower()]
                        
                        # 快速检查是否找到了国产方案
                        found_domestic = False
                        for rec in additional_recommendations:
                            if rec["type"] == "未知" and is_domestic_brand(rec["model"]):
                                rec["type"] = "国产"
                            if rec["type"] == "国产":
                                found_domestic = True
                        
                        # 记录二次查询结果
                        if found_domestic:
                            st.success(f"✅ 二次查询成功！找到了 {len(additional_recommendations)} 个替代方案，其中包含国产方案。")
                        else:
                            st.info(f"ℹ️ 二次查询返回了 {len(additional_recommendations)} 个替代方案，但未找到国产方案。")
                        
                        # 添加到推荐列表
                        for rec in additional_recommendations:
                            if len(recommendations) >= 3:
                                break
                            recommendations.append(rec)
                        break
                    else:
                        st.warning(f"⚠️ 重新调用 DeepSeek API 第 {attempt + 1} 次未返回有效推荐。")
                        if attempt == max_retries - 1:
                            st.error("❌ 重新调用 DeepSeek API 未能返回有效推荐，将使用默认替代方案。")
                except Exception as e:
                    st.warning(f"⚠️ 重新调用 DeepSeek API 第 {attempt + 1} 次失败：{e}")
                    if attempt == max_retries - 1:
                        st.error("❌ 重新调用 DeepSeek API 失败，将使用默认替代方案。")
            
            # 如果二次查询失败且结果仍然不足，从 Nexar 数据中补充
            if not second_query_success or len(recommendations) < 3:
                for alt in nexar_alternatives:
                    if len(recommendations) >= 3:
                        break
                    # 检查是否已经包含此型号
                    if alt["mpn"].lower() != part_number.lower() and not any(rec["model"].lower() == alt["mpn"].lower() for rec in recommendations):
                        new_rec = {
                            "model": alt["mpn"],
                            "brand": alt.get("name", "未知品牌").split(' ')[0] if alt.get("name") else "未知品牌",
                            "category": "未知类别",
                            "package": "未知封装",
                            "parameters": "参数未知",
                            "type": "未知",
                            "datasheet": alt["octopartUrl"]
                        }
                        # 识别国产方案
                        if is_domestic_brand(new_rec["model"]):
                            new_rec["type"] = "国产"
                        recommendations.append(new_rec)
            
            # 在二次查询完成后再做一次最终统计
            if need_second_query:
                domestic_count = sum(1 for rec in recommendations if rec["type"] == "国产")
                import_count = sum(1 for rec in recommendations if rec["type"] == "进口" or rec["type"] == "未知")
                st.info(f"🔍 查找完成，共找到 {len(recommendations)} 个替代方案，其中国产方案 {domestic_count} 个，进口/未知方案 {import_count} 个。")

        # Step 7: 再次后处理，识别国产方案
        for rec in recommendations:
            if rec["type"] == "未知" and is_domestic_brand(rec["model"]):
                rec["type"] = "国产"

        return recommendations[:3]
    except Exception as e:
        st.error(f"DeepSeek API 调用失败：{e}")
        return []

def process_bom_file(uploaded_file):
    """处理上传的BOM文件并返回元器件列表"""
    # 再次检查依赖，确保已安装
    check_and_install_dependencies()
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_filepath = tmp_file.name
    
    try:
        # 根据文件扩展名读取文件
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext == '.csv':
            df = pd.read_csv(tmp_filepath)
        elif file_ext == '.xls':
            # 专门处理旧版Excel文件
            try:
                df = pd.read_excel(tmp_filepath, engine='xlrd')
            except Exception as e:
                st.error(f"无法使用xlrd读取.xls文件: {e}")
                st.warning("尝试使用openpyxl引擎...")
                df = pd.read_excel(tmp_filepath, engine='openpyxl')
        elif file_ext == '.xlsx':
            # 处理新版Excel文件
            df = pd.read_excel(tmp_filepath, engine='openpyxl')
        else:
            raise ValueError(f"不支持的文件格式: {file_ext}")
        
        # 尝试识别关键列：型号列、名称列、描述列
        # 可能的列名
        mpn_columns = []  # 型号列
        name_columns = []  # 名称列
        desc_columns = []  # 描述列
        
        mpn_keywords = ['mpn', 'part', 'part_number', 'part number', 'partnumber', '型号', '规格型号', '器件型号']
        name_keywords = ['name', 'component', 'component_name', '名称', '元件名称', '器件名称']
        desc_keywords = ['description', 'desc', '描述', '规格', '说明', '特性']
        
        # 遍历所有列，尝试匹配关键词
        for col in df.columns:
            col_lower = str(col).lower()
            # 检查是否为型号列
            if any(keyword in col_lower for keyword in mpn_keywords):
                mpn_columns.append(col)
            # 检查是否为名称列
            if any(keyword in col_lower for keyword in name_keywords):
                name_columns.append(col)
            # 检查是否为描述列
            if any(keyword in col_lower for keyword in desc_keywords):
                desc_columns.append(col)
        
        # 如果没有找到明确的列，尝试从所有列中查找最有可能的型号列
        if not mpn_columns:
            for col in df.columns:
                sample_values = df[col].dropna().astype(str).tolist()[:5]
                # 检查值的特征是否像型号（通常含有数字和字母的组合）
                if sample_values and all(bool(re.search(r'[A-Za-z].*\d|\d.*[A-Za-z]', val)) for val in sample_values):
                    mpn_columns.append(col)
        
        # 构建元器件列表，包含型号、名称和描述信息
        component_list = []
        
        # 确定最终使用的列
        mpn_col = mpn_columns[0] if mpn_columns else None
        name_col = name_columns[0] if name_columns else None
        desc_col = desc_columns[0] if desc_columns else None
        
        # 如果没有找到任何列，使用前几列
        if not mpn_col and len(df.columns) >= 1:
            mpn_col = df.columns[0]
        if not name_col and len(df.columns) >= 2:
            name_col = df.columns[1]
        if not desc_col and len(df.columns) >= 3:
            desc_col = df.columns[2]
        
        # 从DataFrame中提取元器件列表
        for _, row in df.iterrows():
            component = {}
            
            # 提取型号信息
            if mpn_col and pd.notna(row.get(mpn_col)):
                component['mpn'] = str(row.get(mpn_col)).strip()
            else:
                continue  # 如果没有型号，则跳过该行
                
            # 提取名称信息
            if name_col and pd.notna(row.get(name_col)):
                component['name'] = str(row.get(name_col)).strip()
            else:
                component['name'] = ''
                
            # 提取描述信息
            if desc_col and pd.notna(row.get(desc_col)):
                component['description'] = str(row.get(desc_col)).strip()
            else:
                component['description'] = ''
                
            # 仅添加有型号的元器件
            if component.get('mpn'):
                component_list.append(component)
        
        # 去重，通常BOM表中会有重复的元器件
        unique_components = []
        seen_mpns = set()
        for comp in component_list:
            mpn = comp['mpn']
            if mpn not in seen_mpns:
                seen_mpns.add(mpn)
                unique_components.append(comp)
        
        # 返回元器件列表和识别的列名
        columns_info = {
            'mpn_column': mpn_col,
            'name_column': name_col,
            'description_column': desc_col
        }
        
        return unique_components, columns_info
            
    except Exception as e:
        st.error(f"处理BOM文件时出错: {e}")
        if "Missing optional dependency 'xlrd'" in str(e):
            st.info("正在尝试安装xlrd依赖...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "xlrd>=2.0.1"])
                st.success("xlrd安装成功，请重新上传文件")
            except Exception as install_error:
                st.error(f"自动安装xlrd失败: {install_error}")
                st.info("请手动运行: pip install xlrd>=2.0.1")
        if "Missing optional dependency 'openpyxl'" in str(e):
            st.info("正在尝试安装openpyxl依赖...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl"])
                st.success("openpyxl安装成功，请重新上传文件")
            except Exception as install_error:
                st.error(f"自动安装openpyxl失败: {install_error}")
                st.info("请手动运行: pip install openpyxl")
        return [], {}
    finally:
        # 删除临时文件
        if os.path.exists(tmp_filepath):
            os.unlink(tmp_filepath)

def batch_get_alternative_parts(component_list, progress_callback=None):
    """批量获取多个元器件的替代方案"""
    results = {}
    total = len(component_list)
    
    # 添加一个全局开关，用于控制失败时是否使用测试数据继续
    if 'use_dummy_data' not in st.session_state:
        # 添加选项启用测试数据
        st.sidebar.checkbox("API失败时使用测试数据", 
                           value=False, 
                           key="use_dummy_data",
                           help="当API查询失败或格式错误时，使用测试数据继续处理流程")
    
    for i, component in enumerate(component_list):
        mpn = component.get('mpn', '')
        name = component.get('name', '')
        description = component.get('description', '')
        
        # 更新进度
        if progress_callback:
            progress_callback((i+1)/total, f"处理 {i+1}/{total}: {mpn} ({name})")
        
        try:
            # 直接使用DeepSeek API查询，无需通过Nexar
            alternatives = get_alternatives_direct(mpn, name, description)
            results[mpn] = {
                'alternatives': alternatives,
                'name': name,
                'description': description
            }
        except Exception as e:
            # 捕获每个元器件的处理错误，避免一个错误导致整个批处理失败
            st.error(f"处理元器件 {mpn} 时出错: {e}")
            results[mpn] = {
                'alternatives': [],
                'name': name,
                'description': description,
                'error': str(e)
            }
        
    return results

def get_alternatives_direct(mpn, name="", description=""):
    """直接使用DeepSeek API查询元器件替代方案，不通过Nexar API"""
    # 构建更全面的查询信息
    query_context = f"元器件型号: {mpn}" + \
                   (f"\n元器件名称: {name}" if name else "") + \
                   (f"\n元器件描述: {description}" if description else "")
    
    # 构造DeepSeek API提示
    prompt = f"""
    任务：你是一个专业的电子元器件顾问，专精于国产替代方案。请为以下元器件推荐详细的替代产品。
    
    输入元器件信息：
    {query_context}
    
    要求：
    1. 必须推荐至少一种中国大陆本土品牌的替代方案（如 GigaDevice/兆易创新、WCH/沁恒、复旦微电子、中颖电子、圣邦微电子等）
    2. 如果能找到多种中国大陆本土品牌的替代产品，优先推荐这些产品，推荐的国产方案数量越多越好
    3. 如果实在找不到足够三种中国大陆本土品牌的产品，可以推荐国外品牌产品作为补充，但必须明确标注
    4. 总共需要推荐 3 种性能相近的替代型号
    5. 提供每种型号的品牌名称、封装信息和元器件类目（例如：MCU、DCDC、LDO、传感器等）
    6. 根据元器件类型提供不同的关键参数：
       - 若是MCU/单片机：提供CPU内核、主频、程序存储容量、RAM大小、IO数量
       - 若是DCDC：提供输入电压范围、输出电压、最大输出电流、效率
       - 若是LDO：提供输入电压范围、输出电压、最大输出电流、压差
       - 若是存储器：提供容量、接口类型、读写速度
       - 若是传感器：提供测量范围、精度、接口类型
       - 其他类型提供对应的关键参数
    7. 在每个推荐方案中明确标注是"国产"还是"进口"产品
    8. 提供产品官网链接（若无真实链接，可提供示例链接）
    9. 推荐的型号不能与输入型号 {mpn} 相同
    10. 必须严格返回以下 JSON 格式的结果，不允许添加额外说明或Markdown格式：
    [
        {{"model": "详细型号1", "brand": "品牌名称1", "category": "类别1", "package": "封装1", "parameters": "详细参数1", "type": "国产/进口", "datasheet": "链接1"}},
        {{"model": "详细型号2", "brand": "品牌名称2", "category": "类别2", "package": "封装2", "parameters": "详细参数2", "type": "国产/进口", "datasheet": "链接2"}},
        {{"model": "详细型号3", "brand": "品牌名称3", "category": "类别3", "package": "封装3", "parameters": "详细参数3", "type": "国产/进口", "datasheet": "链接3"}}
    ]
    11. 每个推荐项必须包含 "model"、"brand"、"category"、"package"、"parameters"、"type" 和 "datasheet" 七个字段
    12. 如果无法找到合适的替代方案，返回空的 JSON 数组：[]
    """
    
    try:
        # 调用DeepSeek API
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个精通中国电子元器件行业的专家，擅长为各种元器件寻找合适的替代方案，尤其专注于中国大陆本土生产的国产元器件。始终以有效的JSON格式回复，不添加任何额外说明。"},
                {"role": "user", "content": prompt}
            ],
            stream=False,
            max_tokens=1200
        )
        
        raw_content = response.choices[0].message.content
        recommendations = extract_json_content(raw_content, "批量查询")
        
        # 过滤掉与输入型号相同的推荐
        recommendations = [rec for rec in recommendations if rec["model"].lower() != mpn.lower()]
        
        # 后处理，识别国产方案
        for rec in recommendations:
            if rec["type"] == "未知" and is_domestic_brand(rec["model"]):
                rec["type"] = "国产"
        
        # 如果没有找到国产方案，进行二次查询强调国产替代
        if not any(rec["type"] == "国产" for rec in recommendations):
            # 进行第二次查询，强调国产替代
            second_prompt = f"""
            任务：为元器件 {mpn} 推荐中国大陆本土品牌的替代方案。

            之前的推荐结果未包含国产方案，请重新推荐，仅限于中国大陆本土品牌的替代产品。
            如果实在无法找到合适的中国大陆本土品牌，可以补充少量进口产品，但必须优先推荐国产方案。

            元器件信息：
            {query_context}

            要求：
            1. 必须推荐至少一种中国大陆本土品牌的替代方案（如 GigaDevice/兆易创新、WCH/沁恒、复旦微电子、中颖电子、圣邦微电子、思旺等）
            2. 总共推荐 3 种替代方案，优先推荐国产品牌
            3. 提供元器件类目、品牌名称、封装信息和关键参数
            4. 明确标注是"国产"还是"进口"产品
            5. 提供产品官网链接
            6. 必须严格返回有效JSON数组格式结果
            """
            
            try:
                response = deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个精通中国电子元器件行业的专家，擅长寻找中国大陆本土生产的国产元器件替代方案。始终以有效的JSON格式回复，不添加任何额外说明。"},
                        {"role": "user", "content": second_prompt}
                    ],
                    stream=False,
                    max_tokens=1200
                )
                
                raw_content = response.choices[0].message.content
                second_recommendations = extract_json_content(raw_content, "国产替代二次查询")
                
                # 过滤掉与输入型号相同的推荐
                second_recommendations = [rec for rec in second_recommendations if rec["model"].lower() != mpn.lower()]
                
                # 后处理，识别国产方案
                for rec in second_recommendations:
                    if rec["type"] == "未知" and is_domestic_brand(rec["model"]):
                        rec["type"] = "国产"
                
                # 合并结果，优先保留国产方案
                domestic_recs = [rec for rec in second_recommendations if rec["type"] == "国产"]
                if domestic_recs:
                    # 如果找到了国产方案，先添加这些国产方案
                    combined = domestic_recs
                    
                    # 然后补充进口方案
                    import_recs = [rec for rec in recommendations if rec["type"] != "国产"][:3-len(combined)]
                    combined.extend(import_recs)
                    
                    # 如果还不够3个，再补充二次查询的进口方案
                    if len(combined) < 3:
                        second_import_recs = [rec for rec in second_recommendations if rec["type"] != "国产"]
                        combined.extend(second_import_recs[:3-len(combined)])
                    
                    recommendations = combined[:3]
            
            except Exception as e:
                st.warning(f"二次查询国产替代方案失败: {e}")
        
        return recommendations[:3]
        
    except Exception as e:
        st.error(f"DeepSeek API 查询失败: {e}")
        
        # 如果启用了测试数据，返回测试数据
        if st.session_state.get("use_dummy_data", False):
            st.info(f"使用测试数据继续处理 {mpn}")
            return [
                {
                    "model": f"{mpn}_ALT1",
                    "brand": "GigaDevice/兆易创新",
                    "category": "未知类别",
                    "package": "未知封装",
                    "parameters": "参数未知",
                    "type": "国产",
                    "datasheet": "https://www.example.com/datasheet"
                },
                {
                    "model": f"{mpn}_ALT2",
                    "brand": "品牌未知",
                    "category": "未知类别",
                    "package": "未知封装",
                    "parameters": "参数未知",
                    "type": "未知",
                    "datasheet": "https://www.example.com/datasheet"
                }
            ]
        return []

def chat_with_expert(user_input, history=None):
    """
    使用DeepSeek API实现与电子元器件专家的对话
    
    参数:
        user_input (str): 用户的输入/问题
        history (list): 对话历史记录，格式为[{"role": "user/assistant", "content": "消息内容"}, ...]
    
    返回:
        str 或 Generator: 根据stream参数，返回完整回复或流式回复
    """
    if history is None:
        history = []
    
    # 构建完整的消息历史
    messages = [
        {"role": "system", "content": """你是一位资深的电子元器件专家，熟悉各种电子元器件的参数、应用场景和设计建议。
        你可以回答关于电子元器件（如MCU、电阻、电容、二极管、晶体管等）的问题,
        包括但不限于其工作原理、常见参数、替代方案、应用场景和设计注意事项。
        请尽可能详细和专业地回答问题，必要时可以提供示例代码或电路图的文字描述。
        如果问题不清楚，请礼貌地要求用户提供更多信息。
        如果问题超出了电子元器件领域，请礼貌地说明你是一个电子元器件专家，只能回答相关问题。
        你应当特别关注用户查询的电子元器件型号，提供其详细规格、应用场景和设计建议。
        对于国产替代方案的问题，你应当提供专业、详尽的分析。"""}
    ]
    
    # 添加历史对话
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # 添加当前用户问题
    messages.append({"role": "user", "content": user_input})
    
    try:
        # 调用DeepSeek API获取回复 - 使用流式响应
        response = deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True,
            max_tokens=2000
        )
        return response
    
    except Exception as e:
        st.error(f"调用DeepSeek API失败: {e}")
        import traceback
        st.error(f"错误详情: {traceback.format_exc()}")
        # 返回一个只包含错误信息的生成器，以保持接口一致性
        def error_generator():
            yield f"很抱歉，我暂时无法回答你的问题。错误信息: {str(e)}"
        return error_generator()