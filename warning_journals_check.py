import streamlit as st
import pandas as pd
import datetime
import hashlib
import os
import json
from pathlib import Path

# 页面配置 - 必须放在最前面！
st.set_page_config(
    page_title="论文投稿备案系统",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# 隐藏整个菜单
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    /* 修复休眠提示样式，增加可读性 */
    .stAlert {z-index: 9999 !important;}
    </style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)

# 完整美化的标签页样式（调整字体大小）
tab_style_complete = """
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 16px;
    }

    .stTabs [data-baseweb="tab"] {
        height: 55px;
        white-space: pre-wrap;
        background-color: #f8f9fa;
        border-radius: 8px 8px 0px 0px;
        gap: 8px;
        padding: 14px 26px;
        font-weight: bold;
        font-size: 24px !important; /* 增大标签页字体大小 */
        border: 1px solid #dee2e6;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1f77b4;
        color: white;
        font-size: 24px !important; /* 增大选中标签页字体大小 */
        border: 1px solid #1f77b4;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e9ecef;
        color: #1f77b4;
    }

    .stTabs [aria-selected="true"]:hover {
        background-color: #1f77b4;
        color: white;
    }
</style>
"""

st.markdown(tab_style_complete, unsafe_allow_html=True)

# ==================== 核心配置优化 ====================
# 数据文件路径配置（确保跨平台兼容）
DATA_FILE = Path("submissions_data.json")
# 会话超时时间（延长至2小时，单位：秒）
SESSION_TIMEOUT = 7200  # 2小时 = 7200秒


# ==================== 数据持久化函数优化 ====================
def save_submissions():
    """优化：确保文件目录存在，增加写入成功验证"""
    try:
        # 确保数据文件所在目录存在
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        # 写入数据（增加错误捕获粒度）
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(st.session_state.submissions, f, ensure_ascii=False, indent=2)
        # 验证写入成功
        if DATA_FILE.exists() and os.path.getsize(DATA_FILE) > 0:
            return True
        else:
            st.error("❌ 数据保存失败：文件为空或未创建")
            return False
    except PermissionError:
        st.error("❌ 数据保存失败：无文件写入权限，请检查目录权限")
        return False
    except Exception as e:
        st.error(f"❌ 数据保存失败: {str(e)}")
        return False


def load_submissions():
    """优化：增加文件完整性校验，避免读取损坏文件"""
    try:
        if not DATA_FILE.exists():
            st.info("📁 未找到历史数据文件，将创建新文件")
            return []

        # 检查文件大小（避免空文件）
        if os.path.getsize(DATA_FILE) == 0:
            st.warning("⚠️ 数据文件为空，将重新初始化")
            return []

        # 读取并解析JSON
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # 校验数据格式（确保是列表）
        if isinstance(data, list):
            return data
        else:
            st.error("⚠️ 数据文件格式错误，将使用空数据")
            return []
    except json.JSONDecodeError:
        st.error("⚠️ 数据文件损坏，无法读取历史记录")
        # 备份损坏文件
        backup_file = DATA_FILE.with_suffix(f".bak_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")
        DATA_FILE.rename(backup_file)
        st.info(f"损坏文件已备份为：{backup_file.name}")
        return []
    except Exception as e:
        st.error(f"❌ 加载数据失败: {str(e)}")
        return []


# ==================== 会话超时管理 ====================
def check_session_timeout():
    """检查会话是否超时，延长会话有效期"""
    current_time = datetime.datetime.now().timestamp()
    # 初始化会话时间戳
    if 'session_start_time' not in st.session_state:
        st.session_state.session_start_time = current_time
    # 检查超时（当前时间 - 会话开始时间 > 超时时间）
    if current_time - st.session_state.session_start_time > SESSION_TIMEOUT:
        # 超时处理：保存当前数据并提示
        if 'submissions' in st.session_state:
            save_submissions()  # 强制保存数据
        st.warning(f"⚠️ 会话已超时（{SESSION_TIMEOUT // 3600}小时），请刷新页面继续使用")
        # 重置会话开始时间（允许继续操作）
        st.session_state.session_start_time = current_time
    else:
        # 未超时：更新会话时间戳（刷新有效期）
        st.session_state.session_start_time = current_time


# ==================== 安全配置函数 ====================
def get_security_config():
    """安全地获取系统配置"""
    try:
        return {
            'admin_password': st.secrets["app"]["admin_password"],
            'max_login_attempts': st.secrets["security"].get("max_login_attempts", 3),
            'debug_mode': st.secrets["app"].get("debug_mode", False)
        }
    except:
        st.warning("⚠️ 未找到secrets.toml文件，使用默认开发配置")
        return {
            'admin_password': "keyanban123456",
            'max_login_attempts': 5,
            'debug_mode': True
        }


# ==================== 数据初始化优化 ====================
def init_session_state():
    """优化：用户ID持久化（基于用户名+固定标识，避免会话重置后丢失）"""
    # 1. 会话超时检查
    check_session_timeout()

    # 2. 用户身份初始化（优化：科研人员用户名可自定义，便于识别）
    if 'user_role' not in st.session_state:
        st.session_state.user_role = "科研人员"
    if 'is_authenticated' not in st.session_state:
        st.session_state.is_authenticated = True  # 默认已登录
    if 'current_user' not in st.session_state:
        # 科研人员默认使用"科研人员+固定标识"，避免每次会话变更
        st.session_state.current_user = "科研人员"
        # 允许科研人员自定义用户名（可选，提升体验）
        with st.sidebar.expander("👤 个人设置", expanded=False):
            custom_name = st.text_input("自定义显示名称", value=st.session_state.current_user)
            if st.button("保存名称"):
                st.session_state.current_user = custom_name.strip() or "科研人员"
                st.rerun()

    # 3. 关键优化：用户ID基于用户名生成（固定不变，确保历史记录可匹配）
    if 'user_id' not in st.session_state:
        # 使用用户名+固定盐值生成MD5，确保同一用户ID不变
        salt = "whayh_hospital_research"  # 固定盐值，避免ID变更
        st.session_state.user_id = hashlib.md5(
            (st.session_state.current_user + salt).encode('utf-8')
        ).hexdigest()

    # 4. 数据加载（优化：优先加载本地文件，确保历史记录不丢失）
    if 'submissions' not in st.session_state:
        st.session_state.submissions = load_submissions()
        # 显示加载状态
        st.success(f"✅ 加载历史记录 {len(st.session_state.submissions)} 条")

    # 5. 预警期刊初始化
    if 'warning_journals' not in st.session_state:
        init_warning_journals()
    if 'show_admin_login' not in st.session_state:
        st.session_state.show_admin_login = False


# ==================== 预警期刊初始化（保持不变） ====================
def init_warning_journals():
    """初始化预警期刊数据"""
    try:
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin1', 'cp1252']
        for encoding in encodings:
            try:
                df = pd.read_csv('warning_journals_20251117.csv', encoding=encoding)
                df_cleaned = clean_dataframe(df)
                if not df_cleaned.empty:
                    st.session_state.warning_journals = df_cleaned
                    return
            except (UnicodeDecodeError, LookupError):
                continue
            except Exception as e:
                continue
        st.session_state.warning_journals = create_sample_journals()
        st.warning("⚠️ 无法读取CSV文件，使用示例数据")
    except FileNotFoundError:
        st.session_state.warning_journals = create_sample_journals()
        st.info("📝 使用示例预警期刊数据，请上传CSV文件")


def clean_dataframe(df):
    """清理数据框"""
    df_cleaned = df.dropna(axis=1, how='all')
    unnamed_cols = [col for col in df_cleaned.columns if 'Unnamed' in col]
    if unnamed_cols:
        df_cleaned = df_cleaned.drop(columns=unnamed_cols)
    return df_cleaned


def create_sample_journals():
    """创建示例预警期刊数据"""
    sample_data = {
        '期刊名称': [
            'Bioengineered', 'European Review for Medical and Pharmacological Sciences',
            'OncoTargets and Therapy', 'Medical Science Monitor'
        ],
        '预警年份': [2023, 2022, 2021, 2020],
        '预警来源': ['中科院预警', '中科院预警', '中科院预警', '中科院预警']
    }
    return pd.DataFrame(sample_data)


# ==================== 登录系统（保持不变） ====================
def login_system():
    """登录系统界面"""
    with st.sidebar:
        st.header("🔐 系统登录")
        if st.session_state.user_role == "科研办审核员":
            st.success("✅ 当前身份：科研办审核员")
            if st.button("🔁 切换至科研人员身份"):
                st.session_state.user_role = "科研人员"
                st.session_state.is_authenticated = True
                st.session_state.current_user = "科研人员"
                # 重新生成用户ID（基于新身份）
                salt = "whayh_hospital_research"
                st.session_state.user_id = hashlib.md5(
                    (st.session_state.current_user + salt).encode('utf-8')
                ).hexdigest()
                st.rerun()
        else:
            st.success(f"👤 当前身份：{st.session_state.current_user}")
            if st.button("🔐 管理员登录"):
                st.session_state.show_admin_login = True
            if st.session_state.show_admin_login:
                st.markdown("---")
                st.subheader("管理员登录")
                password = st.text_input(
                    "请输入管理员密码",
                    type="password",
                    placeholder="输入管理员密码"
                )
                if st.button("✅ 验证身份"):
                    handle_admin_login(password)
                if st.button("❌ 取消"):
                    st.session_state.show_admin_login = False
                    st.rerun()


def handle_admin_login(password):
    """处理管理员登录"""
    security_config = get_security_config()
    correct_password = security_config['admin_password']
    if password == correct_password:
        st.session_state.user_role = "科研办审核员"
        st.session_state.is_authenticated = True
        st.session_state.current_user = "科研办管理员"
        # 管理员ID固定（避免变更）
        st.session_state.user_id = hashlib.md5(
            ("科研办管理员" + "whayh_hospital_research").encode('utf-8')
        ).hexdigest()
        st.session_state.show_admin_login = False
        st.success("✅ 管理员身份验证成功！")
        st.rerun()
    else:
        st.error("❌ 密码错误，请重新输入")


# ==================== 管理功能（保持不变） ====================
def management_functions():
    """管理功能界面"""
    with st.sidebar:
        st.markdown("---")
        st.header("🔧 管理功能")
        if st.session_state.user_role == "科研办审核员":
            st.subheader("更新预警期刊库")
            uploaded_file = st.file_uploader("上传预警期刊列表(CSV)", type=['csv'])
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    df_cleaned = clean_dataframe(df)
                    st.session_state.warning_journals = df_cleaned
                    st.success(f"✅ 成功更新预警期刊库！共 {len(df_cleaned)} 条记录。")
                except Exception as e:
                    st.error(f"❌ 文件读取错误: {e}")
        else:
            st.subheader("更新预警期刊库")
            st.info("🔒 此功能仅限科研办审核员使用")
        st.markdown("---")
        st.subheader("📊 系统统计")
        st.write(f"预警期刊数量: **{len(st.session_state.warning_journals)}** 种")
        if st.session_state.user_role == "科研办审核员":
            total_count = len(st.session_state.submissions)
            st.write(f"总备案数量: **{total_count}** 条")
        else:
            my_count = len([s for s in st.session_state.submissions if s.get('提交用户ID') == st.session_state.user_id])
            st.write(f"我的备案数量: **{my_count}** 条")
        if st.session_state.user_role == "科研办审核员" and st.session_state.submissions:
            records_df = pd.DataFrame(st.session_state.submissions)
            pending_count = len(records_df[records_df['状态'] == '待审核'])
            approved_count = len(records_df[records_df['状态'] == '审核通过'])
            rejected_count = len(records_df[records_df['状态'] == '审核驳回'])
            st.write(f"待审核: **{pending_count}** 条")
            st.write(f"已通过: **{approved_count}** 条")
            st.write(f"已驳回: **{rejected_count}** 条")


# ==================== 主应用功能（优化数据保存逻辑） ====================
def main_application():
    """主应用界面"""
    st.title("📚 论文投稿备案与期刊预警系统")
    if st.session_state.user_role == "科研人员":
        show_researcher_interface()
    else:
        show_admin_interface()


def show_researcher_interface():
    """科研人员界面"""
    tab1, tab2, tab3 = st.tabs(["🔍 预警期刊查询", "📝 投稿备案", "📋 我的备案记录"])
    with tab1:
        show_journal_search_interface()
    with tab2:
        show_submission_interface()
    with tab3:
        show_my_submissions()


def show_journal_search_interface():
    """期刊查询界面（保持不变）"""